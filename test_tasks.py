import pytest
# pytest（測試工具）= 自動跑測試的套件

from httpx import AsyncClient, ASGITransport
# AsyncClient（非同步客戶端）= 非同步版的「假裝是使用者」工具
# ASGITransport（ASGI 傳輸層）= 讓 AsyncClient 能直接跟 FastAPI 溝通的橋梁

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
# create_async_engine（建立非同步引擎）= 非同步版的資料庫連線管理員
# async_sessionmaker（非同步 session 製造機）= 非同步版的對話工具

from database import get_db
# 從 database.py 匯入 get_db（取得資料庫連線的函式）

from main import app
# 從 main.py 匯入 app（FastAPI 應用程式）

import models
# 匯入 models.py（資料表定義）

# 測試用的資料庫連線網址（用 testdb，不用真實的 taskdb）
TEST_DATABASE_URL = "postgresql+psycopg://taskuser:taskpass@localhost:5432/testdb"
# postgresql+psycopg = 用 PostgreSQL 資料庫，透過 psycopg 驅動程式連線
# taskuser = 帳號
# taskpass = 密碼
# localhost = 本機電腦
# 5432 = PostgreSQL 的預設埠號（port，通訊用的門號）
# testdb = 測試專用的資料庫

# 建立測試用的引擎（連去 testdb，不是 taskdb）
engine = create_async_engine(TEST_DATABASE_URL)
# create_engine（建立引擎）= 建立資料庫連線管理員
# 這個引擎專門連去測試資料庫

# 建立測試用的 session 製造機
TestingSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)
# sessionmaker（session 製造機）= 建立跟資料庫對話的工具
# bind=engine（綁定引擎）= 告訴它要連去哪個資料庫
# autocommit=False（不自動存檔）= 我們自己決定什麼時候存檔
# autoflush=False（不自動刷新）= 我們自己決定什麼時候刷新




# 建立一個「替換用」的資料庫函式
async def override_get_db():
    async with TestingSessionLocal() as db:
        yield db

# 告訴 app：測試時，把 get_db 換成 override_get_db
app.dependency_overrides[get_db] = override_get_db
# dependency_overrides（依賴覆蓋）
# = 把原本的函式換成另一個函式
# get_db = 原本的真實資料庫連線函式
# override_get_db = 替換成測試資料庫連線函式

@pytest.fixture(autouse=True)
# autouse=True（自動使用）= 每個測試開始前自動執行這個函式
async def setup_database():
    # 測試開始前：建立資料表
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    yield
    # yield（產出）= 分隔「測試前」和「測試後」
    # 測試結束後：把資料表全部刪掉，保持乾淨
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.drop_all)

# 測試「建立任務」
async def test_create_task():
    # async def（非同步函式）= 非同步版的函式定義
    async with AsyncClient(
        # AsyncClient（非同步客戶端）= 非同步版的假使用者工具
        transport=ASGITransport(app=app),
        # transport（傳輸層）= 告訴 AsyncClient 要跟哪個 app 溝通
        # ASGITransport（ASGI 傳輸層）= 連接 AsyncClient 和 FastAPI 的橋梁
        base_url="http://test"
        # base_url（基礎網址）= 測試用的假網址
    ) as client:
        # as client = 把這個假使用者取名叫 client
        response = await client.post("/tasks", json={
            # await（等待）= 等非同步操作完成
            # client.post（發送 POST 請求）= 模擬建立任務
            "title": "測試任務",
            "description": "這是測試",
            "done": False
        })
        assert response.status_code == 200
        # assert（斷言）= 確認這件事是對的
        # status_code == 200 = 確認回應是成功的
        assert response.json()["title"] == "測試任務"
        # response.json()（回應的 JSON 內容）= 拿到 API 回傳的資料
        # ["title"] == "測試任務" = 確認標題正確

# 測試「查詢全部任務」
async def test_list_tasks():
    # async def（非同步函式）= 非同步版的函式定義
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        # 先建立一筆任務
        await client.post("/tasks", json={"title": "任務一", "done": False})
        # await（等待）= 等非同步操作完成
        # client.post（發送 POST 請求）= 模擬建立任務
        response = await client.get("/tasks")
        # client.get（發送 GET 請求）= 模擬查詢全部任務
        assert response.status_code == 200 
        # assert（斷言）= 確認這件事是對的
        assert len(response.json()) >=1
        # len（length，長度）= 計算清單裡有幾筆資料
        # >= 1（大於等於 1）= 確認至少有一筆任務

# 測試「查詢單筆任務」
async def test_get_tasks():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        # 先建立一筆任務，拿到它的 id
        create = await client.post("/tasks", json={"title": "單筆任務", "done": False})
        # create（建立的回應）= 儲存建立任務後回傳的資料
        task_id = create.json()["id"]
        # task_id（任務編號）= 從回傳資料裡拿到這筆任務的 id
        response = await client.get(f"/tasks/{task_id}")
        # f"/tasks/{task_id}"（f-string 格式化字串）
        # = 把 task_id 的數字放進網址，例如 /tasks/1
        assert response.status_code == 200
        # assert（斷言）= 確認這件事是對的
        assert response.json()["title"] == "單筆任務"
        # 確認回傳的標題跟我們建立的一樣

# 測試「查詢不存在的任務，應該回 404」
async def test_get_task_not_found():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.get("/tasks/99999")
        # 查一個不存在的 id（99999）
        assert response.status_code == 404
        # 404（找不到）= 確認回應是「找不到這筆任務」

# 測試「更新任務」
async def test_update_task():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        # 先建立一筆任務
        create = await client.post("/tasks", json={"title": "舊標籤", "done": False})
        task_id = create.json()["id"]
        # task_id（任務編號）= 從回傳資料裡拿到這筆任務的 id
        response = await client.put(f"/tasks/{task_id}", json={
            # client.put（發送 PUT 請求）= 模擬更新任務
            "title": "新標題",
            "done": True
        })
        assert response.status_code == 200
        # assert（斷言）= 確認這件事是對的
        assert response.json()["title"] == "新標題"
        # 確認標題有改成新的
        assert response.json()["done"] == True
        # 確認完成狀態有改成 True

# 測試「刪除任務」
async def test_delete_task():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        # 先建立一筆任務
        create = await client.post("/tasks", json={"title": "要刪除的任務", "done": False})
        task_id = create.json()["id"]
        # task_id（任務編號）= 從回傳資料裡拿到這筆任務的 id
        response = await client.delete(f"/tasks/{task_id}")
        # client.delete（發送 DELETE 請求）= 模擬刪除任務
        assert response.status_code == 200
        # 確認刪除成功
        # 再查一次，確認真的不見了
        check = await client.get(f"/tasks/{task_id}")
        # check（確認）= 儲存再查一次的回應
        assert check.status_code == 404
        # 應該回 404，因為已經刪掉了