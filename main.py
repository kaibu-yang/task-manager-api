from fastapi import FastAPI, Request  # 多匯入 Request（請求），櫃台函式會收到它
from fastapi.responses import JSONResponse  # JSONResponse（JSON 回應）：自己組出要回傳的 JSON
from errors import AppError  # 匯入剛剛寫的自訂錯誤類別


from routers import tasks, auth
# 從 routers 資料夾匯入 tasks.py 和 auth.py

app = FastAPI()
# 建立 FastAPI 應用程式；資料表改由 Alembic 管理，所以不再需要 lifespan
@app.exception_handler(AppError)  # 登記：只要有 AppError 被拋出，就交給下面這個函式處理
async def app_error_handler(request: Request, exc: AppError):  # request = 這次的請求；exc = 被拋出的那個錯誤
    return JSONResponse(  # 回傳一個 JSON 回應
        status_code=exc.status_code,  # 狀態碼用錯誤身上帶的，例如 404
        content={"error": {"code": exc.code, "message": exc.message}},  # 照新格式組出內容
    )



app.include_router(tasks.router)
app.include_router(auth.router)
# include_router（包含路由器）= 告訴 app「去 tasks.py 和 auth.py 裡找端點」