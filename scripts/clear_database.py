#!/usr/local/bin/python

from bot.models import Conversation, Person, Review

Review.delete().execute()
Conversation.delete().execute()
Person.delete().execute()