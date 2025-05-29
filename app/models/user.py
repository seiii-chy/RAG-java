from app.extensions import db
from datetime import datetime
from zoneinfo import ZoneInfo


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(512), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda:datetime.now(ZoneInfo('Asia/Shanghai')))
    user_type = db.Column(db.String(128), default='normal')
