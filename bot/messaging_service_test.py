import pytest

import bot.models as models
import bot.messaging_service as messaging

from unittest import mock

@pytest.fixture(scope='function', autouse=True)
def clear_database():
    try:
        yield
    finally:
        for model in models.MODELS:
            model.delete().execute()


def test_handle_outgoing_message():
    mock_response = mock.MagicMock
    mock_response.text = 'sample response'
    outgoing = messaging.OutgoingMessage(1, 'message', True)
    with mock.patch('bot.messaging_service.requests.post', return_value=mock_response) as mock_post:
        messaging.handle_outgoing_message(outgoing)
        mock_post.assert_called_once_with(
            messaging.MESSAGES_URL,
            params={'access_token': messaging.ACCESS_TOKEN},
            headers={'content-type': 'application/json'},
            json={
                'recipient': {'id': 1},
                'message': {'text': 'message'},
                'messaging_type': 'RESPONSE'
            }
        )
