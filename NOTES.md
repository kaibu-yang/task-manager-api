# Task Manager API — 程式碼複習筆記

一個用 **FastAPI + PostgreSQL（全非同步 async）** 的任務管理 API。
本筆記把三個檔案逐行拆解，標出「會變 🟢 / 固定樣板 🔵 / 必須綁在一起 🔗」。

---

## 📁 專案架構（三個檔案各司其職）

| 檔案 | 角色 | 白話 |
|------|------|------|
| `database.py` | 連線設定 | 「怎麼連到資料庫」 |
| `models.py` | 資料表定義（ORM） | 「資料庫的表格長怎樣」 |
| `main.py` | API 端點 | 「對外提供哪些功能」 |

**資料流向：** 使用者 → `main.py` 端點 → 用 `get_db` 拿連線（`database.py`）→ 操作 `models.py` 定義的表格 → PostgreSQL

---

## 1️⃣ database.py — 連線設定

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

DATABASE_URL = "postgresql+psycopg://taskuser:taskpass@localhost:5432/taskdb"

engine = create_async_engine(DATABASE_URL)
SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)
Base = declarative_base()

async def get_db():
    async with SessionLocal() as db:
        yield db
```

| 程式碼 | 作用 |
|--------|------|
| `DATABASE_URL` | 連線字串。格式：`postgresql+psycopg://帳號:密碼@主機:埠/資料庫名` 🟢 |
| `create_async_engine(...)` | 建立「非同步引擎」＝資料庫的總連線管理員 🔵 |
| `async_sessionmaker(...)` | 「session 製造機」（非同步版） 🔵 |
| `expire_on_commit=False` | commit 後物件還能繼續讀（非同步必加，否則出錯） 🔵 |
| `Base = declarative_base()` | ORM 模型的「基底」，models.py 要繼承它 🔗 |
| `async def get_db()` | 給端點用的依賴：開一個 session 借出去，用完自動關 🔵 |
| `async with ... as db: yield db` | 「借了一定會還」：`async with` 自動關閉，`yield` 把 db 交給端點 🔵 |

> **session（會話）** = 「跟資料庫的一次對話」。新增/查詢/刪除都在某個 session 裡進行。

---

## 2️⃣ models.py — 資料表定義（ORM）

```python
from sqlalchemy import Column, Integer, String, Boolean
from database import Base

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    done = Column(Boolean, default=False)
```

| 程式碼 | 作用 |
|--------|------|
| `class Task(Base)` | 繼承 `Base`，SQLAlchemy 才知道這是一張資料表 🔗 |
| `__tablename__ = "tasks"` | 這張表在資料庫裡的名字 🟢 |
| `Column(Integer, primary_key=True)` | 整數、**主鍵**＝唯一身分證；主鍵會由資料庫**自動遞增** 🔵 |
| `index=True` | 建索引，查詢更快 🔵 |
| `nullable=False` | 不可空白（必填）🟢 |
| `nullable=True` | 可空白（選填）🟢 |
| `default=False` | 沒給就用預設值 🟢 |

> **ORM** = 用 Python 類別/物件操作資料庫，不用手寫 SQL。

---

## 3️⃣ main.py — API 端點

### (A) 上半部：匯入 + 啟動建表 + app + 資料格式

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import engine, get_db
import models

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    yield

app = FastAPI(lifespan=lifespan)

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    done: bool = False

class TaskRead(TaskCreate):
    id: int
    model_config = {"from_attributes": True}
```

| 程式碼 | 作用 |
|--------|------|
| `lifespan` | 伺服器「啟動時」做的事；`yield` 前＝啟動、`yield` 後＝關閉 🔵 |
| `engine.begin() + run_sync(...create_all)` | 非同步引擎建表的固定寫法（非同步不能直接 create_all）🔵 |
| `FastAPI(lifespan=lifespan)` | 把 lifespan 掛上去 🔵 |
| `class TaskCreate` | **輸入**格式（沒有 id，使用者要傳的）🟢 |
| `class TaskRead(TaskCreate)` | **輸出**格式（繼承再加 id）🟢 |
| `model_config = {"from_attributes": True}` | 讓 Pydantic 能從 ORM 物件讀資料（回傳時必須）🔵 |

> **兩種 model 的差別（最重要！）**
> - Pydantic（`TaskCreate`/`TaskRead`）= 檢查 **API 進出**的資料格式
> - ORM（`models.Task`）= 對應 **資料庫表格**

### (B) 五個 CRUD 端點

```python
@app.get("/")
async def hello():
    return {"message": "Hello, FastAPI!"}

# Create
@app.post("/tasks", response_model=TaskRead)
async def create_task(payload: TaskCreate, db: AsyncSession = Depends(get_db)):
    task = models.Task(**payload.model_dump())
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task

# Read 全部
@app.get("/tasks", response_model=list[TaskRead])
async def list_tasks(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Task))
    return result.scalars().all()

# Read 單筆
@app.get("/tasks/{task_id}", response_model=TaskRead)
async def get_task(task_id: int, db: AsyncSession = Depends(get_db)):
    task = await db.get(models.Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="找不到這筆任務")
    return task

# Update
@app.put("/tasks/{task_id}", response_model=TaskRead)
async def update_task(task_id: int, payload: TaskCreate, db: AsyncSession = Depends(get_db)):
    task = await db.get(models.Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="找不到這筆任務")
    task.title = payload.title
    task.description = payload.description
    task.done = payload.done
    await db.commit()
    await db.refresh(task)
    return task

# Delete
@app.delete("/tasks/{task_id}")
async def delete_task(task_id: int, db: AsyncSession = Depends(get_db)):
    task = await db.get(models.Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="找不到這筆任務")
    await db.delete(task)
    await db.commit()
    return {"message": f"任務 {task_id} 已刪除"}
```

**每個端點的共同樣板 🔵**
- 裝飾器 `@app.方法("/網址", response_model=...)`
- 參數 `db: AsyncSession = Depends(get_db)` ← 每個都要
- 找不到就 `if task is None: raise HTTPException(404, ...)`

**資料庫操作對照（async 都要 await）**
| 動作 | 寫法 |
|------|------|
| 新建一筆 | `models.Task(**payload.model_dump())` → `db.add(task)` |
| 存檔 | `await db.commit()` |
| 讀回最新（拿 id） | `await db.refresh(task)` |
| 查全部 | `await db.execute(select(models.Task))` → `.scalars().all()` |
| 查單筆（用主鍵） | `await db.get(models.Task, task_id)` |
| 刪除 | `await db.delete(task)` → `await db.commit()` |

---

## 🔗 必須「綁在一起」改的（最易錯）

```
@app.get("/tasks/{task_id}", response_model=TaskRead)
                  └─①─┘                    └──③──┘
async def get_task(task_id: int, db: AsyncSession = Depends(get_db)):
                   └─①─┘                            └────②────┘
    task = await db.get(models.Task, task_id)
                        └───④───┘   └─①─┘
```
1. 網址 `{task_id}` = 參數 `task_id` = 用到的 `task_id`（三處名字要一樣）
2. `Depends(get_db)` ↔ database.py 的 `get_db`
3. `response_model=TaskRead` ↔ 實際 `return` 的東西
4. `models.Task` ↔ models.py 的資料表類別

---

## ⭐ CRUD ↔ HTTP 方法（必背）

| 操作 | 方法 | 網址 |
|------|------|------|
| 建立 Create | POST | /tasks |
| 查全部 Read | GET | /tasks |
| 查單筆 Read | GET | /tasks/{id} |
| 更新 Update | PUT | /tasks/{id} |
| 刪除 Delete | DELETE | /tasks/{id} |

---

## ⭐ 同步 vs 非同步（async）重點

- **規則：要嘛全同步、要嘛全非同步，不能混**（`async def` 配同步 db 呼叫會卡住整個伺服器）。
- 全非同步要件：`create_async_engine` + `async_sessionmaker` + `AsyncSession` + 端點 `async def` + 碰資料庫前加 `await`。
- 一句話：**碰資料庫的動作（commit/refresh/delete/execute/get）前面都要 `await`**。

---

## ⚠️ Python 易錯點（踩過的雷）

| 雷 | 正確 |
|----|------|
| 大小寫敏感 | `Task`(類別大寫) ≠ `task`(變數小寫)；`Base` ≠ `base` |
| 判斷 None | `if task is None:`（不是 `not in None`、不是 `not is`） |
| class/def 結尾 | 一定要有冒號 `:` |
| 函式內縮排 | 每行往內縮 4 空格 |
| 取屬性 | 用句點 `models.Base`（不是逗號） |
| import 多個 | 名字間要逗號 `,` |
| 比較 | filter/判斷用兩個等號 `==` |

---

## 🐘 PostgreSQL 設定指令（一次性）

```bash
sudo -u postgres psql -c "CREATE USER taskuser WITH PASSWORD 'taskpass';"
sudo -u postgres psql -c "CREATE DATABASE taskdb OWNER taskuser;"
```

## ▶️ 啟動指令

```bash
source venv/bin/activate          # 進虛擬環境
uvicorn main:app --reload         # 啟動，開 http://127.0.0.1:8000/docs 測試
```
