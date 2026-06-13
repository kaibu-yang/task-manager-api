from sqlalchemy import Column, Integer, String, Boolean
from database import Base

# Task 的 ORM 模型：對應資料庫裡一張叫 "tasks" 的表格
class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    done = Column(Boolean, default=False)