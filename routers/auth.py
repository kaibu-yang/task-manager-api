from datetime import datetime, timedelta
# datetime（日期時間）= Python 內建的時間工具
# timedelta（時間差）= 用來計算「幾分鐘後過期」的工具

from jose import jwt
# jose（JWT 工具套件）= 處理 JWT 手環的套件
# jwt（JSON Web Token）= 產生和驗證手環的工具

from passlib.context import CryptContext
# passlib（密碼工具套件）= 處理密碼加密的套件
# CryptContext（加密環境）= 設定要用哪種加密方式的工具

import os
# os（作業系統）= Python 內建，讓我們能讀電腦的環境變數

from dotenv import load_dotenv
# dotenv（環境變數工具）= 讀取 .env 檔案的工具

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
# OAuth2PasswordRequestForm（OAuth2 密碼請求表單）= 接收表單格式的帳號密碼

from sqlalchemy.ext.asyncio import AsyncSession
# AsyncSession（非同步會話）= 跟資料庫對話的工具

from database import get_db
# 從 database.py 匯入 get_db（取得資料庫連線的函式）

import models
# 匯入 models.py（資料表定義）

from schemas import UserCreate, Token
# 從 schemas.py 匯入使用者相關的資料格式

router = APIRouter()
# router（路由器）= 建立一個路由器物件，端點都掛在這上面

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")
# oauth2_scheme（OAuth2 方案）= 驗票員工具
# tokenUrl="/login"（令牌網址）= 告訴它去哪裡取得手環（登入端點）

async def get_current_user(token: str = Depends(oauth2_scheme)):
    # token（手環）= 從請求裡自動取出的 JWT 字串
    # Depends(oauth2_scheme)= 自動從請求的 Header 取出手環
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # jwt.decode（解碼）= 把 JWT 手環解開，取出裡面的資料
        username = payload.get("sub")
        # payload.get("sub")= 取出手環裡存的使用者帳號
        if username is None:
            raise HTTPException(status_code=401, detail = "無效的手環")
    except Exception:
        raise HTTPException(status_code=401, detail="無效的手環")
    return username
# 回傳使用者帳號，讓端點知道是誰在操作


load_dotenv()
# 執行「打開 .env、把裡面的值載入進來」

SECRET_KEY = os.getenv("SECRET_KEY")
# 從 .env 讀取密鑰

ALGORITHM = os.getenv("ALGORITHM")
# 從 .env 讀取加密演算法

# 建立密碼加密工具
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# pwd_context（密碼環境）= 我們的密碼加密工具
# schemes=["bcrypt"]（加密方式）= 使用 bcrypt 這種加密演算法
# deprecated="auto"（自動處理舊的加密方式）= 自動升級舊密碼

# 把明文密碼加密
def hash_password(password: str) -> str:
    return pwd_context.hash(password)
# hash_password（雜湊密碼）= 把原始密碼變成一串看不懂的亂碼
# 就像把食材放進絞肉機，出來的東西完全看不出原本是什麼

# 確認密碼是否正確
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
# verify_password（驗證密碼）= 確認使用者輸入的密碼跟資料庫裡的加密密碼是否相符
# plain_password（明文密碼）= 使用者輸入的原始密碼
# hashed_password（加密密碼）= 資料庫裡存的加密版本

def create_access_token(data: dict) -> str:
    # data（資料）= 要放進手環裡的資訊，例如使用者帳號
    to_encode = data.copy()
    # copy()（複製）= 複製一份資料，避免修改到原本的
    expire = datetime.utcnow() + timedelta(minutes=30)
    # datetime.utcnow()（現在的時間）= 取得目前的時間
    # timedelta(minutes=30)（30分鐘後）= 手環 30 分鐘後過期
    to_encode.update({"exp": expire})
    # update（更新）= 把過期時間加進去
    # "exp"（expiration，過期時間）= JWT 規定的過期時間欄位名稱
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    # jwt.encode（編碼）= 把資料加密成 JWT 手環字串
    return token
    # 回傳產生好的 JWT 手環字串

# 註冊新使用者
@router.post("/register", response_model=Token)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    # payload（資料）= 使用者傳進來的帳號和密碼
    # 先檢查帳號是不是已經有人用了
    from sqlalchemy import select
    result = await db.execute(select(models.User).filter(models.User.username == payload.username))
    # select（選取）= 查詢資料庫
    # filter（篩選）= 找帳號跟使用者傳進來一樣的
    existing_user = result.scalars().first()
    # scalars().first()= 取出第一筆結果
    if existing_user:
        raise HTTPException(status_code=400, detail="帳號已經存在")
    # status_code=400（錯誤請求）= 使用者傳來的資料有問題

    # 把密碼加密後，建立新使用者
    hashed_pw = hash_password(payload.password)
    # hash_password（雜湊密碼）= 把明文密碼變成加密版本
    # payload.password（使用者傳來的密碼）= 原始密碼

    new_user = models.User(
        username=payload.username,
        # username（使用者名稱）= 帳號
        hashed_password=hashed_pw
        # hashed_password（加密後的密碼）= 存加密版本，不存明文
    )
    db.add(new_user)
    # db.add（加入）= 把新使用者加入資料庫連線
    await db.commit()
    # await db.commit()（等待存檔）= 真正寫進資料庫
    await db.refresh(new_user)
    # await db.refresh（等待重新讀取）= 讀回最新狀態

    # 產生 JWT 手環並回傳
    token = create_access_token({"sub": new_user.username})
    # "sub"（subject，主體）= JWT 規定的欄位，存放使用者帳號
    return Token(access_token=token, token_type="bearer")
    # Token（手環格式）= 回傳手環字串和類型
 
#登入
@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    # payload（資料）= 使用者傳進來的帳號和密碼
    from sqlalchemy import select
    result = await db.execute(select(models.User).filter(models.User.username == form_data.username))
    # select（選取）= 查詢資料庫
    # filter（篩選）= 找帳號跟使用者傳進來一樣的
    user = result.scalars().first()
    # scalars().first()= 取出第一筆結果
    if not user or not verify_password(form_data.password, user.hashed_password):
        # not user = 帳號不存在
        # not verify_password(...) = 密碼不正確
        raise HTTPException(status_code=401, detail="帳號或密碼錯誤")
        # status_code=401（未授權）= 身份驗證失敗
    token = create_access_token({"sub": user.username})
    # create_access_token（產生手環）= 產生 JWT 手環
    # "sub"（subject，主體）= JWT 規定的欄位，存放使用者帳號
    return Token(access_token=token, token_type="bearer")
    # Token（手環格式）= 回傳手環字串和類型
