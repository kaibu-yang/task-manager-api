from fastapi import APIRouter, HTTPException, Depends
# fastapi（API 框架）匯入三個工具：
# APIRouter（路由器）= 把端點分組管理的工具，等下會解釋
# HTTPException（HTTP 例外）= 回傳錯誤給使用者，例如 404 找不到
# Depends（依賴）= 讓端點自動取得資料庫連線

from sqlalchemy.ext.asyncio import AsyncSession
# AsyncSession（非同步會話）= 跟資料庫對話的工具（非同步版）

from sqlalchemy import select
# select（選取）= 用來查詢資料庫的工具

from database import get_db
# 從 database.py 匯入 get_db（取得資料庫連線的函式）

import models
# 匯入 models.py（資料表定義）

from schemas import TaskCreate, TaskRead
# 從 schemas.py 匯入我們剛建立的兩個資料格式

router = APIRouter()
# router（路由器）= 用 APIRouter() 建立一個路由器物件
# 之後所有端點都掛在這個 router 上，而不是掛在 app 上

# Create（建立）：新增一筆任務
@router.post("/tasks", response_model=TaskRead)
async def create_task(payload: TaskCreate, db: AsyncSession = Depends(get_db)):
    task = models.Task(**payload.model_dump())
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task

# Read（查全部）：列出所有任務
@router.get("/tasks", response_model=list[TaskRead])
async def list_tasks(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Task))
    return result.scalars().all()

# Read（查單筆）：依 id 查詢
@router.get("/tasks/{task_id}", response_model=TaskRead)
async def get_task(task_id: int, db: AsyncSession = Depends(get_db)):
    task = await db.get(models.Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="找不到這筆任務")
    return task

# Update（更新）：改某一筆任務
@router.put("/tasks/{task_id}", response_model=TaskRead)
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
@router.delete("/tasks/{task_id}")
async def delete_task(task_id: int, db: AsyncSession = Depends(get_db)):
    task = await db.get(models.Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="找不到這筆任務")
    await db.delete(task)
    await db.commit()
    return {"message": f"任務 {task_id} 已刪除"}