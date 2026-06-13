from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import engine, get_db
import models


# lifespan：伺服器「啟動時」自動建立資料表（非同步版的 create_all）
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    yield


app = FastAPI(lifespan=lifespan)
# 「建立任務」時，使用者要傳進來的資料（沒有 id，因為 id 由伺服器自己給）

class TaskCreate(BaseModel):
    title: str                         # 標題（必填）
    description: Optional[str] = None   # 描述（選填，預設 None＝沒有）
    done: bool = False                 # 是否完成（預設 False＝還沒做）

# 「回傳任務」時的完整樣子：繼承上面的 TaskCreate，再多一個 id 欄位
class TaskRead(TaskCreate):
    id: int                            # 任務編號（由伺服器產生）
    model_config = {"from_attributes": True}





@app.get("/")
async def hello():
    return {"message": "Hello, FastAPI!"}


# Create（建立）：新增一筆任務
@app.post("/tasks", response_model=TaskRead)
async def create_task(payload: TaskCreate, db: AsyncSession = Depends(get_db)):
    task = models.Task(**payload.model_dump())
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


# Read（查全部）：列出所有任務
@app.get("/tasks", response_model=list[TaskRead])
async def list_tasks(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Task))
    return result.scalars().all()


# Read（查單筆）：依 id 查詢
@app.get("/tasks/{task_id}", response_model=TaskRead)
async def get_task(task_id: int, db: AsyncSession = Depends(get_db)):
    task = await db.get(models.Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="找不到這筆任務")
    return task


# Update（更新）：改某一筆任務
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


# Delete（刪除）：刪掉某一筆任務
@app.delete("/tasks/{task_id}")
async def delete_task(task_id: int, db: AsyncSession = Depends(get_db)):
    task = await db.get(models.Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="找不到這筆任務")
    await db.delete(task)
    await db.commit()
    return {"message": f"任務 {task_id} 已刪除"}
