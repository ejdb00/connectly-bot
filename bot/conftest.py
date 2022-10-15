import quart.flask_patch

import bot.db_service as db
import bot.models as models

def pytest_sessionstart():
    setup_test_schema()


def pytest_sessionfinish():
    try:
        teardown_test_schema()
    except Exception as e:
        print(e)


def setup_test_schema():
    """
    Create a DB schema named "pytest" and update all models to use "pytest" instead of "public" (the default).
    """

    with db.atomic():
        res = db.execute_sql("SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'pytest';")
        schema_exists = res.fetchone()

        # Create pytest schema if not exists
        if not schema_exists:
            db.execute_sql('CREATE SCHEMA pytest;')
        db.execute_sql('SET search_path TO pytest;')

    # Patch all models to use the "pytest" schema
    for model in models.MODELS:
        model._meta.schema = 'pytest'

    with db.atomic():
        models.create_tables()


def teardown_test_schema():
    for model in models.MODELS:
        model._meta.schema = 'public'
    db.execute_sql('SET search_path TO public;')
    db.execute_sql('DROP SCHEMA pytest CASCADE;')