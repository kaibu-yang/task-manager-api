from sqlalchemy import select  # 查詢資料庫的工具
from sqlalchemy.ext.asyncio import AsyncSession  # 跟資料庫對話的工具（這裡只用來標示型別）

import models  # 資料表定義（User）

from passlib.context import CryptContext  # 密碼加密工具

from errors import AppError  # 自訂錯誤類別
from schemas import UserCreate  # 註冊用的資料格式


async def get_user_by_username(db: AsyncSession, username: str) -> models.User | None:  # 用帳號找使用者
    result = await db.execute(select(models.User).where(models.User.username == username))  # 找帳號一樣的那一筆
    return result.scalars().first()  # 找到就回傳使用者；找不到回傳 None


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")  # 使用 bcrypt 加密；舊的加密方式會自動升級

def hash_password(password: str) -> str:  # 把明文密碼變成雜湊值，看不出原本的密碼
    return pwd_context.hash(password)  # 同一個密碼每次結果都不一樣（bcrypt 會自動加鹽）

def verify_password(plain_password: str, hashed_password: str) -> bool:  # 檢查輸入的密碼對不對
    return pwd_context.verify(plain_password, hashed_password)  # 對就回 True，錯就回 False


async def register_user(db: AsyncSession, data: UserCreate) -> models.User:  # 註冊新使用者
    if await get_user_by_username(db, data.username) is not None:  # 規則一：帳號不能重複
        raise AppError(400, "USERNAME_TAKEN", "帳號已經存在")  # 被用過就拒絕
    user = models.User(username=data.username, hashed_password=hash_password(data.password))  # 規則二：只存加密後的密碼
    db.add(user)  # 放進待存清單
    await db.commit()  # 寫進資料庫
    await db.refresh(user)  # 重新讀回來，拿到資料庫產生的 id
    return user  # 回傳新使用者


