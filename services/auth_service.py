from sqlalchemy import select  # 查詢資料庫的工具
from sqlalchemy.ext.asyncio import AsyncSession  # 跟資料庫對話的工具（這裡只用來標示型別）

import models  # 資料表定義（User）

async def get_user_by_username(db: AsyncSession, username: str) -> models.User | None:  # 用帳號找使用者
    result = await db.execute(select(models.User).where(models.User.username == username))  # 找帳號一樣的那一筆
    return result.scalars().first()  # 找到就回傳使用者；找不到回傳 None
