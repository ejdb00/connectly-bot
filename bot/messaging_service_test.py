from datetime import datetime
import pytest

import bot.messaging_service as messaging

from bot.models import Conversation, Person, Review
from typing import List
from unittest import mock

@pytest.fixture(scope='function', autouse=True)
def clear_database():
    try:
        yield
    finally:
        Review.delete().execute()
        Conversation.delete().execute()
        Person.delete().execute()


def test_handle_outgoing_message():
    mock_response = mock.MagicMock
    mock_response.text = 'sample response'
    outgoing = messaging.OutgoingMessage(1, 'message', True)
    with mock.patch('bot.messaging_service.requests.post', return_value=mock_response) as mock_post:
        messaging.handle_outgoing_message(outgoing)
        mock_post.assert_called_once_with(
            url=messaging.MESSAGES_URL,
            params={'access_token': messaging.ACCESS_TOKEN},
            headers={'content-type': 'application/json'},
            json={
                'recipient': {'id': 1},
                'message': {'text': 'message'},
                'messaging_type': 'RESPONSE'
            }
        )


def test_handle_incoming_message__e2e_review_provided():
    assert len(Person.select()) == 0
    assert len(Conversation.select()) == 0
    assert len(Review.select()) == 0

    profile_response = mock.MagicMock
    profile_response.json = lambda: {
        'first_name': 'Fake',
        'last_name': 'Person'
    }

    with (mock.patch('bot.messaging_service.handle_outgoing_message') as mock_outgoing, 
        mock.patch('bot.messaging_service.requests.get', return_value=profile_response) as mock_get):

        # First message
        messaging.handle_incoming_message(incoming('Hi!')) 

        mock_outgoing.assert_called_once_with(messaging.OutgoingMessage(1, '...'))
        mock_get.assert_called_once_with(
            url='https://graph.facebook.com/1',
            params={
                'fields': 'first_name,last_name',
                'access_token': messaging.ACCESS_TOKEN
            }
        )
        mock_outgoing.reset_mock()
        mock_get.reset_mock()

        [persisted_person] = list(Person.select())
        assert persisted_person.first_name == 'Fake'
        assert persisted_person.last_name == 'Person'
        
        [persisted_conversation] = list(Conversation.select())
        assert persisted_conversation.person == persisted_person
        assert persisted_conversation.started_at is not None
        assert persisted_conversation.review_requested_at is None
        assert persisted_conversation.review_recieved_at is None
        assert persisted_conversation.declined_review_at is None
        
        assert len(Review.select()) == 0

        # Second message (review trigger)
        messaging.handle_incoming_message(incoming('Thank you!')) 

        mock_outgoing.assert_called_once_with(messaging.OutgoingMessage(1, messaging.SOLICIT_REVIEW_REPLY_TEMPLATE))
        mock_get.assert_not_called()
        mock_outgoing.reset_mock()
        mock_get.reset_mock()
        
        [persisted_conversation] = list(Conversation.select())
        assert persisted_conversation.person == persisted_person
        assert persisted_conversation.started_at is not None
        assert persisted_conversation.review_requested_at is not None
        assert persisted_conversation.review_recieved_at is None
        assert persisted_conversation.declined_review_at is None

        assert len(Review.select()) == 0

        # Third message (review itself)
        messaging.handle_incoming_message(incoming('Incredible, just incredible')) 

        mock_outgoing.assert_called_once_with(messaging.OutgoingMessage(1, 'Thanks for the feedback!'))
        mock_get.assert_not_called()
        
        [persisted_conversation] = list(Conversation.select())
        assert persisted_conversation.person == persisted_person
        assert persisted_conversation.started_at is not None
        assert persisted_conversation.review_requested_at is not None
        assert persisted_conversation.review_recieved_at is not None
        assert persisted_conversation.declined_review_at is None
        
        [persisted_review] = list(Review.select())
        assert persisted_review.conversation == persisted_conversation
        assert persisted_review.raw_message == 'Incredible, just incredible'
        assert float(persisted_review.estimated_review_stars) == 4.832


def test_handle_incoming_message__e2e_review_declined():
    assert len(Person.select()) == 0
    assert len(Conversation.select()) == 0
    assert len(Review.select()) == 0

    profile_response = mock.MagicMock
    profile_response.json = lambda: {
        'first_name': 'Fake',
        'last_name': 'Person'
    }

    with (mock.patch('bot.messaging_service.handle_outgoing_message') as mock_outgoing, 
        mock.patch('bot.messaging_service.requests.get', return_value=profile_response) as mock_get):

        # First message
        messaging.handle_incoming_message(incoming('Hi!')) 

        mock_outgoing.assert_called_once_with(messaging.OutgoingMessage(1, '...'))
        mock_get.assert_called_once_with(
            url='https://graph.facebook.com/1',
            params={
                'fields': 'first_name,last_name',
                'access_token': messaging.ACCESS_TOKEN
            }
        )
        mock_outgoing.reset_mock()
        mock_get.reset_mock()

        [persisted_person] = list(Person.select())
        assert persisted_person.first_name == 'Fake'
        assert persisted_person.last_name == 'Person'
        
        [persisted_conversation] = list(Conversation.select())
        assert persisted_conversation.person == persisted_person
        assert persisted_conversation.started_at is not None
        assert persisted_conversation.review_requested_at is None
        assert persisted_conversation.review_recieved_at is None
        assert persisted_conversation.declined_review_at is None
        
        assert len(Review.select()) == 0

        # Second message (review trigger)
        messaging.handle_incoming_message(incoming('Thank you!')) 

        mock_outgoing.assert_called_once_with(messaging.OutgoingMessage(1, messaging.SOLICIT_REVIEW_REPLY_TEMPLATE))
        mock_get.assert_not_called()
        mock_outgoing.reset_mock()
        mock_get.reset_mock()
        
        [persisted_conversation] = list(Conversation.select())
        assert persisted_conversation.person == persisted_person
        assert persisted_conversation.started_at is not None
        assert persisted_conversation.review_requested_at is not None
        assert persisted_conversation.review_recieved_at is None
        assert persisted_conversation.declined_review_at is None

        assert len(Review.select()) == 0

        # Third message (review decline)
        messaging.handle_incoming_message(incoming('No')) 

        mock_outgoing.assert_called_once_with(messaging.OutgoingMessage(1, 'Aw :('))
        mock_get.assert_not_called()
        
        [persisted_conversation] = list(Conversation.select())
        assert persisted_conversation.person == persisted_person
        assert persisted_conversation.started_at is not None
        assert persisted_conversation.review_requested_at is not None
        assert persisted_conversation.review_recieved_at is None
        assert persisted_conversation.declined_review_at is not None
        
        assert len(Review.select()) == 0


def incoming(message: str) -> messaging.IncomingMessage:
    return messaging.IncomingMessage(
        sender_id=1,
        recipient_id=0,
        timestamp=datetime(2022, 10, 20, 11, 22, 33),
        message_id='<messageid>',
        text=message
    ) 