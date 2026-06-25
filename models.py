from sqlalchemy import Column, Integer, String, Boolean
from database import Base

# Task 的 ORM 模型：對應資料庫裡一張叫 "tasks" 的表格
class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    done = Column(Boolean, default=False)

    # User（使用者）資料表
class User(Base):
    # 繼承 Base（基底）= 告訴 SQLAlchemy 這是一張資料表
    __tablename__ = "users"
    # __tablename__（資料表名稱）= 這張表在資料庫裡叫做 users

    id = Column(Integer, primary_key=True, index=True)
    # id（編號）= 每個使用者的唯一身分證，資料庫自動產生
    username = Column(String, unique=True, nullable=False)
    # username（使用者名稱）= 帳號，不能重複（unique），必填（nullable=False）
    # unique=True（唯一）= 不能有兩個人用同樣的帳號
    hashed_password = Column(String, nullable=False)
    # hashed_password（加密後的密碼）= 存加密過的密碼，不存明文
    
