from app.extensions import db
from datetime import datetime
from zoneinfo import ZoneInfo
from app.models.message import Message


class Conversation(db.Model):
    __tablename__ = 'conversations'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now(ZoneInfo('Asia/Shanghai')))
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now(ZoneInfo('Asia/Shanghai')), onupdate=datetime.now(ZoneInfo('Asia/Shanghai')))
    messages = db.relationship('Message', backref='conversation', lazy='dynamic', order_by='Message.timestamp')

    def add_message(self, role, content):
        """添加消息并自动更新对话时间"""
        msg = Message(role=role, content=content, conversation=self)
        db.session.add(msg)
        db.session.commit()
        self.updated_at = datetime.now(ZoneInfo('Asia/Shanghai'))
        return msg


    def to_dict(self):
        """将对话转换为字典格式"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'messages': [msg.to_dict() for msg in self.messages.all()]
        }
