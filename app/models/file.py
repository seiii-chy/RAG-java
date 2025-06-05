from app.extensions import db

class File(db.Model):
    __tablename__ = 'files'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(255), nullable=False)
    collection_name = db.Column(db.String(255), nullable=False, default='java_doc_plus')

    # category: 计算机基本知识、 中间件及工具使用、 面试技巧、 Java经典书籍、 Java开发、 个人笔记