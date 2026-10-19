from fastapi import FastAPI  # 不再需要 Request 了
from errors import register_exception_handlers  # 匯入「登記櫃台」的函式



from routers import tasks, auth
# 從 routers 資料夾匯入 tasks.py 和 auth.py

app = FastAPI()
# 建立 FastAPI 應用程式；資料表改由 Alembic 管理，所以不再需要 lifespan
register_exception_handlers(app)  # 把錯誤櫃台接上（跟 include_router 一樣，main.py 只負責組裝）





app.include_router(tasks.router)
app.include_router(auth.router)
# include_router（包含路由器）= 告訴 app「去 tasks.py 和 auth.py 裡找端點」