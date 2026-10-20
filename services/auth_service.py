from sqlalchemy import select  # 查詢資料庫的工具
from sqlalchemy.ext.asyncio import AsyncSession  # 跟資料庫對話的工具（這裡只用來標示型別）

import models  # 資料表定義（User）

from passlib.context import CryptContext  # 密碼加密工具

from errors import AppError  # 自訂錯誤類別
from schemas import UserCreate  # 註冊用的資料格式

from datetime import datetime, timedelta, timezone  # 時間工具：現在時間、時間差、時區
from jose import JWTError, jwt  # jwt = 產生／解開手環的工具；JWTError = 手環有問題時的專用錯誤

from config import settings  # 設定櫃台（密鑰、演算法）



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


async def authenticate_user(db: AsyncSession, username: str, password: str) -> models.User:  # 檢查帳號密碼，正確就回傳使用者
    user = await get_user_by_username(db, username)  # 先用帳號找人
    if user is None or not verify_password(password, user.hashed_password):  # 帳號不存在，或密碼不對
        raise AppError(401, "INVALID_CREDENTIALS", "帳號或密碼錯誤")  # 規則：不說是哪一個錯，避免洩漏帳號是否存在
    return user  # 帳密都正確，回傳使用者


ACCESS_TOKEN_EXPIRE_MINUTES = 30  # 手環有效時間（分鐘）

def create_access_token(username: str) -> str:  # 幫這位使用者簽發 JWT 手環
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)  # 過期時間 = 現在（UTC）+ 30 分鐘
    to_encode = {"sub": username, "exp": expire}  # sub = 使用者帳號、exp = 過期時間（JWT 規定的欄位名）
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)  # 用密鑰簽名，產生手環字串


def decode_access_token(token: str) -> str | None:  # 解開手環、取出帳號；手環無效就回傳 None
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])  # 用密鑰檢查簽名，也會檢查是否過期
    except JWTError:  # 只抓「手環本身有問題」：簽名錯、過期、格式壞掉
        return None  # 手環無效
    return payload.get("sub")  # 取出帳號；手環裡沒有 sub 也會得到 None


