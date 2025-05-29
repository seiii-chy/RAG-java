from datetime import datetime
from zoneinfo import ZoneInfo

from app.extensions import db

# 定义面试问题表，主要是问题的id
class InterviewQuestion(db.Model):
    __tablename__ = 'interview_questions'
    id = db.Column(db.Integer, primary_key=True)
    interview_id = db.Column(db.Integer, index=True)
    question_id = db.Column(db.Integer, index=True)
    stage = db.Column(db.String(50))  # 当前面试阶段
    is_followup = db.Column(db.Boolean)
    evaluation = db.Column(db.String(500))  # 该问题的评价
    created_at = db.Column(db.DateTime, default=lambda:datetime.now(ZoneInfo('Asia/Shanghai')))
    order = db.Column(db.Integer)  # 问题顺序
    context = db.Column(db.JSON)  # 存储原始对话上下文