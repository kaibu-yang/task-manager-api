from datetime import datetime, timedelta, timezone
# datetime（日期時間）= Python 內建的時間工具
# timedelta（時間差）= 用來計算「幾分鐘後過期」的工具
# timezone（時區），用來標明 UTC

from jose import jwt
# jose（JWT 工具套件）= 處理 JWT 手環的套件
# jwt（JSON Web Token）= 產生和驗證手環的工具

from config import settings
# settings（設定櫃台）= 啟動時已清點好的設定，缺必填值會直接拒絕啟動

from fastapi import APIRouter, Depends, status

from errors import AppError  # 匯入自訂錯誤類別，取代 HTTPException

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

from services import auth_service
# 匯入 auth 的廚房（使用者相關的業務規則）


router = APIRouter()
# router（路由器）= 建立一個路由器物件，端點都掛在這上面

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login", auto_error=False)  
# auto_error=False：沒帶手環不自己報錯，交給 get_current_user 處理
# oauth2_scheme（OAuth2 方案）= 驗票員工具
# tokenUrl="/login"（令牌網址）= 告訴它去哪裡取得手環（登入端點）

async def get_current_user(token: str | None = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    # token（手環）= 從請求裡自動取出的 JWT 字串
    # Depends(oauth2_scheme)= 自動從請求的 Header 取出手環
    if token is None:  # 沒帶手環（驗票員不再自己報錯，改由這裡處理）
        raise AppError(401, "NOT_AUTHENTICATED", "請先登入")  # 跟「手環無效」分開，前端才知道是要登入，還是要重新登入

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # jwt.decode（解碼）= 把 JWT 手環解開，取出裡面的資料
        username = payload.get("sub")
        # payload.get("sub")= 取出手環裡存的使用者帳號
        if username is None:
            raise AppError(401, "INVALID_TOKEN", "無效的手環")  # 手環無效：解不開、沒有帳號、或帳號已不存在)
    except Exception:
        raise AppError(401, "INVALID_TOKEN", "無效的手環")  # 手環無效：解不開、沒有帳號、或帳號已不存在
    user = await auth_service.get_user_by_username(db, username)  # 叫廚房用帳號找使用者；找不到是 None
    if user is None:  # token 有效，但這個帳號已經不在 users 表（例如被刪除）
        raise AppError(401, "INVALID_TOKEN", "無效的手環")  # 手環無效：解不開、沒有帳號、或帳號已不存在、一樣回 401
    return user  # 回傳整個使用者物件，之後路由可以用 user.id


SECRET_KEY = settings.secret_key
# 找櫃台拿 JWT 簽名密鑰（必填，保證有值）

ALGORITHM = settings.algorithm
# 找櫃台拿加密演算法（沒設定就用預設的 HS256）


def create_access_token(data: dict) -> str:
    # data（資料）= 要放進手環裡的資訊，例如使用者帳號
    to_encode = data.copy()
    # copy()（複製）= 複製一份資料，避免修改到原本的
    expire = datetime.now(timezone.utc) + timedelta(minutes=30)
    # 取得「標明是 UTC」的現在時間，再加 30 分鐘
    # datetime.now(timezone.utc)（現在的 UTC 時間）= 取得標明時區的目前時間
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
        raise AppError(400, "USERNAME_TAKEN", "帳號已經存在")  # 帳號被用過了

    # 把密碼加密後，建立新使用者
    hashed_pw = auth_service.hash_password(payload.password)
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
    if not user or not auth_service.verify_password(form_data.password, user.hashed_password):
        # not user = 帳號不存在
        # not verify_password(...) = 密碼不正確
        raise AppError(401, "INVALID_CREDENTIALS", "帳號或密碼錯誤")  # credentials（憑證）= 帳號密碼；不說是哪個錯，避免洩漏帳號是否存在
    token = create_access_token({"sub": user.username})
    # create_access_token（產生手環）= 產生 JWT 手環
    # "sub"（subject，主體）= JWT 規定的欄位，存放使用者帳號
    return Token(access_token=token, token_type="bearer")
    # Token（手環格式）= 回傳手環字串和類型
