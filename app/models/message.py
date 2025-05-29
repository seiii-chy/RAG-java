from app.extensions import db
from datetime import datetime
from zoneinfo import ZoneInfo

class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversations.id', ondelete='CASCADE'), nullable=False, index=True)
    role = db.Column(db.String(20), nullable=False) # 'user' or 'assistant'
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=lambda:datetime.now(ZoneInfo('Asia/Shanghai')))

    def to_dict(self):
            return {
                'id': self.id,
                'conversation_id': self.conversation_id,
                'role': self.role,
                'content': self.content,
                'timestamp': self.timestamp.isoformat()
            }