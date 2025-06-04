import os

from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate

from app.api.endpoints import chat, search, document, auth, interview, knowledge_base, conversation
from app.config import Settings
from app.extensions import db, redis_client, oss_client, upload_pipeline, milvus_client

app = Flask(__name__)



@app.route('/')
def home():
    return 'Hello, World!'


def create_app():
    set_env()
    app.config.from_object(Settings)

    app.extensions['oss'] = oss_client
    app.extensions['pipeline'] = upload_pipeline
    # init db
    db.init_app(app)
    Migrate(app, db)
    # init redis
    redis_client.init_app(app)
    app.register_blueprint(chat.bp)
    app.register_blueprint(search.bp)
    app.register_blueprint(document.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(interview.interview_bp)
    app.register_blueprint(knowledge_base.bp)
    app.register_blueprint(conversation.bp)
    milvus_client.connect(app)
    CORS(app, supports_credentials=True)
    return app

def set_env():
    os.environ['LANGSMITH_ENDPOINT'] = Settings.LANGSMITH_ENDPOINT
    os.environ['LANGSMITH_API_KEY'] = Settings.LANGSMITH_API_KEY
    os.environ['LANGSMITH_TRACING'] = Settings.LANGSMITH_TRACING
    os.environ['LANGSMITH_PROJECT'] = Settings.LANGSMITH_PROJECT

if __name__ == '__main__':
    app = create_app()
    app.run(port=5000,debug=False)