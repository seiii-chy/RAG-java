from flask_sqlalchemy import SQLAlchemy
from flask_redis import FlaskRedis

from app.db.doc_to_oss import DocToOSS
from app.pipelines.pipeline import ProcessingPipeline
from app.db.milvus_client import MilvusClient



db = SQLAlchemy()
redis_client = FlaskRedis()
oss_client = DocToOSS()
upload_pipeline = ProcessingPipeline()
milvus_client = MilvusClient(collection_name="java_doc_plus",dim=512)