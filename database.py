from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from config import settings  # 從 config.py 拿出已經清點好的櫃台

DATABASE_URL = settings.database_url  # 找櫃台拿資料庫連線字串（保證有值，缺了早就啟動失敗）



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