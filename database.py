from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from dotenv import load_dotenv
import os

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")


# 改用 create_async_engine（非同步引擎）
engine = create_async_engine(DATABASE_URL)

# 改用 async_sessionmaker；expire_on_commit=False 讓 commit 後物件還能繼續用
SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

# Base（基底）：之後定義資料表的 ORM 模型都要繼承它
Base = declarative_base()

# get_db：端點需要資料庫時，用它取得一個 session，用完自動關閉
async def get_db():
    async with SessionLocal() as db:
        yield db