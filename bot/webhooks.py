import hashlib
import hmac
import json
import bot.messaging_service as messaging

from quart import Response, request

from bot.constants import (
    APP_SECRET,
    VERIFY_TOKEN
)


async def post() -> Response:
    payload = await request.get_data()
    if not validate_payload(payload):
        return 'FORBIDDEN', 403

    verification_response = handle_verification_request(request.args)
    if verification_response is not None:
        return verification_response

    json_payload = json.loads(payload)
    if json_payload['object'] == 'page':
        print(json_payload)
        if 'entry' not in json_payload:
            return 'INVALID', 400
        for entry in json_payload['entry']:
            if 'messaging' not in entry:
                return 'INVALID', 400
            for message_entry in entry['messaging']:
                try:
                    message = messaging.IncomingMessage.from_json(message_entry)
                except Exception as e:
                    print('Error parsing message [%s]' % e)
                    return 'INVALID', 400
                messaging.handle_incoming_message(message)
        return 'EVENT_RECIEVED', 200
    else:
        print('Unexpected webhook type %s' % payload['page'])
        return 'UNKNOWN', 404
    

# Check the HMAC signature to ensure this webhook was signed with our app's secret key
def validate_payload(payload) -> bool:
    hash_header = request.headers['X-Hub-Signature-256']
    hash = hash_header.split('=')[1]
    expected_hash = hmac.new(APP_SECRET.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(str(hash), str(expected_hash))


# Handle verification webhooks necessary to register a webhook endpoint with Messenger
def handle_verification_request(request_args) -> Response:
    mode = request_args.get('hub.mode')
    token = request_args.get('hub.verify_token')
    challenge = request_args.get('hub.challenge')
    if mode is not None and token is not None:
        if mode == 'subscribe' and token == VERIFY_TOKEN:
            return challenge, 200
        else:
            return 'FORBIDDEN', 403
    return None
