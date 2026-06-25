from contextlib import asynccontextmanager
# asynccontextmanager（非同步內容管理器）= 管理啟動和關閉時要做的事

from fastapi import FastAPI
# 從 fastapi 匯入 FastAPI（主應用程式）

from database import engine
# 從 database.py 匯入 engine（資料庫引擎）

import models
# 匯入 models.py（資料表定義）

from routers import tasks, auth
# 從 routers 資料夾匯入 tasks.py

# lifespan（生命週期）= 伺服器啟動時自動建立資料表
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin()as conn:
        # engine.begin()= 開始一個資料庫連線
        await conn.run_sync(models.Base.metadata.create_all)
        # run_sync= 在非同步環境裡執行同步的建表動作
    yield
    # yield= 啟動完成，開始接受請求

app = FastAPI(lifespan=lifespan)
# 建立 FastAPI 應用程式，並把 lifespan 掛上去

app.include_router(tasks.router)
app.include_router(auth.router)
# include_router（包含路由器）= 告訴 app「去 tasks.py 裡找端點」
