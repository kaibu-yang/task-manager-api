from fastapi import FastAPI
# 從 fastapi 匯入 FastAPI（主應用程式）

from routers import tasks, auth
# 從 routers 資料夾匯入 tasks.py 和 auth.py

app = FastAPI()
# 建立 FastAPI 應用程式；資料表改由 Alembic 管理，所以不再需要 lifespan

app.include_router(tasks.router)
app.include_router(auth.router)
# include_router（包含路由器）= 告訴 app「去 tasks.py 和 auth.py 裡找端點」