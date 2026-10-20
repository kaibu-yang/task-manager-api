from fastapi import APIRouter, Depends

from errors import AppError  # 匯入自訂錯誤類別，取代 HTTPException

from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
# OAuth2PasswordRequestForm（OAuth2 密碼請求表單）= 接收表單格式的帳號密碼

from sqlalchemy.ext.asyncio import AsyncSession
# AsyncSession（非同步會話）= 跟資料庫對話的工具

from database import get_db
# 從 database.py 匯入 get_db（取得資料庫連線的函式）


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

    username = auth_service.decode_access_token(token)  # 叫廚房解開手環，取出帳號
    if username is None:  # 解不開、過期、或手環裡沒有帳號
        raise AppError(401, "INVALID_TOKEN", "無效的手環")  # 一律回無效的手環
    user = await auth_service.get_user_by_username(db, username)  # 叫廚房用帳號找使用者；找不到是 None

    if user is None:  # token 有效，但這個帳號已經不在 users 表（例如被刪除）
        raise AppError(401, "INVALID_TOKEN", "無效的手環")  # 手環無效：解不開、沒有帳號、或帳號已不存在、一樣回 401
    return user  # 回傳整個使用者物件，之後路由可以用 user.id


# 註冊新使用者
@router.post("/register", response_model=Token)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    new_user = await auth_service.register_user(db, payload)  # 叫廚房註冊：檢查重複、加密密碼、存檔
    token = auth_service.create_access_token(new_user.username)  # 叫廚房簽發 JWT 手環
    return Token(access_token=token, token_type="bearer")  # 把手環交給客人

 
#登入
@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    user = await auth_service.authenticate_user(db, form_data.username, form_data.password)  # 叫廚房檢查帳密；錯了廚房會直接回 401
    token = auth_service.create_access_token(user.username)   # 叫廚房簽發 JWT 手環
    return Token(access_token=token, token_type="bearer")  # 把手環交給客人

