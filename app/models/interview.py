from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Table
from app.extensions import db

# 定义面试表，标识面试的场次等基本信息
class Interview(db.Model):
    __tablename__ = 'interviews'
    id = Column(db.Integer, primary_key=True)
    user_id = Column(db.Integer, nullable=False)  # JWT中的用户ID
    position = Column(db.String(100))  # 新增面试岗位字段
    started_at = Column(db.DateTime, default=datetime.now(ZoneInfo('Asia/Shanghai')))
    ended_at = Column(db.DateTime)
    final_score = Column(db.Integer)
    feedback = Column(db.String(1000))
    llm_provider = Column(db.String(50))  # 使用的LLM提供商
    interview_name = Column(db.String(2500))