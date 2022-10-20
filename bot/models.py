import bot.db_service as db
import uuid

from typing import List

from peewee import (
    BigIntegerField,
    DateTimeField,
    ForeignKeyField,
    Model,
    DecimalField,
    TextField,
    UUIDField,
)


class Person(Model):

    class Meta:
        database = db.get_db_instance()
        table_name = 'persons'

    id = BigIntegerField(primary_key=True)
    first_name = TextField(null=True)
    last_name = TextField(null=True)
    created_at = DateTimeField()


class Conversation(Model):

    class Meta:
        database = db.get_db_instance()
        table_name = 'conversations'

    id = UUIDField(primary_key=True, default=uuid.uuid4)
    person = ForeignKeyField(Person, index=True, unique=False)
    selected_product_id = BigIntegerField(null=True)
    started_at = DateTimeField()
    review_requested_at = DateTimeField(null=True)
    product_selected_at = DateTimeField(null=True)
    review_recieved_at = DateTimeField(null=True)
    declined_review_at = DateTimeField(null=True)
    

class Review(Model):

    class Meta:
        database = db.get_db_instance()
        table_name = 'reviews'

    id = UUIDField(primary_key=True, default=uuid.uuid4)
    conversation = ForeignKeyField(Conversation, index=True, unique=False)
    person = ForeignKeyField(Person, index=True, unique=False)
    product_id = BigIntegerField()
    created_at = DateTimeField()
    estimated_review_stars = DecimalField(max_digits=4, decimal_places=3)
    raw_message = TextField()
    
    
MODELS: List[Model] = [Person, Conversation, Review]
    

def create_tables():
    for model in MODELS:
        if not model.table_exists():
            model.create_table(safe=True)