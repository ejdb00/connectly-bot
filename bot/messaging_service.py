import requests

from dataclasses import dataclass
from datetime import datetime
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline

from bot.constants import ACCESS_TOKEN
from bot.models import Conversation, Person, Review


MESSAGES_URL = 'https://graph.facebook.com/v15.0/me/messages'
PROFILE_URL_TEMPLATE = 'https://graph.facebook.com/{}'
DECLINE_MESSAGE = 'NO'
SOLICIT_REVIEW_REPLY_TEMPLATE = 'Please take a moment to let us know how we did, or reply NO if you\'d rather not.'
SOLICIT_REVIEW_PROACTIVE_TEMPLATE = 'Hey {}!  Please take a moment to let us know what you thought of your experience with us, or reply NO if you\'d rather not.'
PRODUCT_CHOOSE_TEMPLATE = 'Which product would you like to provide a review for? Please respond with the number of your chosen product: {}'


tokenizer = AutoTokenizer.from_pretrained("nlptown/bert-base-multilingual-uncased-sentiment")
model = AutoModelForSequenceClassification.from_pretrained("nlptown/bert-base-multilingual-uncased-sentiment")
sentiment_classifier = pipeline('sentiment-analysis', model=model, tokenizer=tokenizer)


@dataclass(frozen=True)
class IncomingMessage:
    sender_id: int
    recipient_id: int
    timestamp: datetime
    message_id: str
    text: str
    
    @classmethod
    def from_json(cls, obj):
        return IncomingMessage(
            sender_id=int(obj['sender']['id']),
            recipient_id=int(obj['recipient']['id']),
            timestamp=datetime.fromtimestamp(int(obj['timestamp'])/1000.0),
            message_id=obj['message']['mid'],
            text=obj['message']['text']
        )


@dataclass(frozen=True)
class OutgoingMessage:
    recipient_id: int
    text: str
    is_response: bool = True
    
    def to_api_payload(self):
        return {
            'recipient': {'id': self.recipient_id},
            'message': {'text': self.text},
            'messaging_type': 'RESPONSE' if self.is_response else 'UPDATE'
        }


@dataclass(frozen=True)
class ProfileInfo:
    person_id: int
    first_name: str
    last_name: str

    @classmethod
    def from_json(cls, obj, person_id: int):
        return ProfileInfo(
            person_id=person_id, 
            first_name=obj['first_name'], 
            last_name=obj['last_name']
        )
        

@dataclass(frozen=True)
class Product:
    id: int
    product_name: str
    manufacturer: str
    vehicle: str

    @classmethod
    def from_json(cls, obj):
        return Product(
            id=obj['id'], 
            product_name=obj['productName'], 
            manufacturer=obj['manufacturer'],
            vehicle=obj['vehicle']
        )
        

def get_products():
    response = requests.get(url='https://62daf70dd1d97b9e0c49ca5d.mockapi.io/v1/products')
    products = {}
    for obj in response.json():
        product = Product.from_json(obj)
        products[product.id] = product
    return products


def format_product_selection_message() -> str:
    products = get_products()
    product_strings = []
    for id in products:
        product = products[id]
        product_strings.append('(%s: %s %s)' % (product.id, product.manufacturer, product.vehicle))
    product_string = ', '.join(product_strings)
    message = PRODUCT_CHOOSE_TEMPLATE.format(product_string)
    return message
    

def handle_incoming_message(message: IncomingMessage):
    print('Recieved incoming message')
    try:
        create_or_update_conversation(message)
    except Exception as e:
        print(e)


def handle_outgoing_message(message: OutgoingMessage):
    payload = message.to_api_payload()
    headers = {'content-type': 'application/json'}
    params = {'access_token': ACCESS_TOKEN}
    response = requests.post(url=MESSAGES_URL, params=params, headers=headers, json=payload, timeout=3)
    print(response.text)
    

def get_profile_info(person_id: int) -> ProfileInfo:
    params = {
        'fields': 'first_name,last_name', 
        'access_token': ACCESS_TOKEN
    }
    url = PROFILE_URL_TEMPLATE.format(person_id)
    response = requests.get(url=url, params=params, timeout=3)
    info = ProfileInfo.from_json(response.json(), person_id)
    print(info)
    return info


def get_or_create_person(person_id: int) -> Person:
    person = Person.get_or_none(Person.id == person_id)
    if person is not None:
        return person
    info = get_profile_info(person_id)
    return Person.create(
        id=person_id, 
        first_name=info.first_name, 
        last_name=info.last_name,
        created_at=datetime.now()
    )
    

def create_or_update_conversation(message: IncomingMessage):
    person = get_or_create_person(message.sender_id)
    convo = Conversation.get_or_none(Conversation.person == person)
    if convo is None:
        convo = Conversation.create(person=person, started_at=datetime.now())
    if convo.review_requested_at is None:
        if 'thank' in message.text.lower():
            solicit_review_in_conversation(convo)
        else:
            reply = OutgoingMessage(recipient_id=message.sender_id, text='...')
            handle_outgoing_message(reply)
    elif convo.product_selected_at is None:
        handle_product_selection(message.text, convo)
    elif convo.review_recieved_at is None and convo.declined_review_at is None:
        if message.text.strip().lower() == 'no':
            convo.declined_review_at = datetime.now()
            convo.save()
            reply = OutgoingMessage(recipient_id=message.sender_id, text='Aw :(')
            handle_outgoing_message(reply)
        else:
            process_review(message.text, convo)
    else:
        reply = OutgoingMessage(recipient_id=message.sender_id, text='Now get lost')
        handle_outgoing_message(reply)
        

def handle_product_selection(msg: str, convo: Conversation):
    try:
        id = int(msg)
        convo.product_selected_at = datetime.now()
        convo.selected_product_id = id
        convo.save()
        reply = OutgoingMessage(recipient_id=convo.person.id, text='Thanks for selecting')
        handle_outgoing_message(reply)

    except ValueError:
        reply = OutgoingMessage(recipient_id=convo.person.id, text='Please respond with the number of the product you would like to review')
        handle_outgoing_message(reply)
    

def solicit_review_in_conversation(convo: Conversation):
    outgoing = OutgoingMessage(recipient_id=convo.person.id, text=SOLICIT_REVIEW_REPLY_TEMPLATE)
    handle_outgoing_message(outgoing)
    convo.review_requested_at = datetime.now()
    convo.save()


def solicit_review_proactively(person_id: int):
    person = get_or_create_person(person_id)
    convo = Conversation.get_or_none(Conversation.person == person)
    if convo is None:
        convo = Conversation.create(person=person, started_at=datetime.now())
    solicitation_message = SOLICIT_REVIEW_PROACTIVE_TEMPLATE.format(person.first_name)
    outgoing = OutgoingMessage(recipient_id=convo.person.id, text=solicitation_message, is_response=False)
    handle_outgoing_message(outgoing)
    convo.review_requested_at = datetime.now()
    convo.review_recieved_at = None
    convo.declined_review_at = None
    convo.save()


def process_review(raw_review_message: str, convo: Conversation):
    estimated_review_stars = extract_sentiment(raw_review_message)
    Review.create(
        conversation=convo, 
        person=convo.person, 
        product_id=convo.selected_product_id,
        created_at=datetime.now(), 
        estimated_review_stars=estimated_review_stars,
        raw_message=raw_review_message
    )
    
    convo.review_recieved_at = datetime.now()
    convo.save()
    reply = OutgoingMessage(recipient_id=convo.person.id, text='Thanks for the feedback!')
    handle_outgoing_message(reply)

    
def extract_sentiment(text: str) -> float:
    review_classification = sentiment_classifier(text, top_k=5)
    weighted_average_stars = 0.0
    for label_score in review_classification:
        stars = int(label_score['label'][0])
        score = label_score['score']
        weighted_average_stars += stars * score
    return weighted_average_stars
    
