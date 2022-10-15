import bot.webhooks as webhooks
import bot.db_service as db
import bot.models as models

from quart import Quart, jsonify

app = Quart(__name__)

db.register_request_handlers(app)
models.create_tables()


@app.route('/')
async def root():
    return 'ROOT'


@app.route('/hello')
async def hello():
    return jsonify({'greeting':'Hello World!'})


app.add_url_rule('/messenger-webhooks', 'messenger-webhooks', webhooks.post, methods=['GET', 'POST'])