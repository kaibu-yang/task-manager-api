from sqlalchemy import select  # 查詢資料庫的工具
from sqlalchemy.ext.asyncio import AsyncSession  # 跟資料庫對話的工具（這裡只用來標示型別）

import models  # 資料表定義（Task、User）
from errors import AppError  # 自訂錯誤類別

async def get_own_task(db: AsyncSession, task_id: int, user: models.User) -> models.Task:  # 取出屬於這位使用者的任務
    result = await db.execute(select(models.Task).where(models.Task.id == task_id, models.Task.user_id == user.id))  # 編號對、主人也對
    task = result.scalars().first()  # 找不到、或是別人的任務，都會是 None
    if task is None:  # 規則：找不到就是 404，由廚房統一判斷
        raise AppError(404, "TASK_NOT_FOUND", "找不到這筆任務")  # 以後不用在三個端點各寫一次
    return task  # 能走到這裡，保證是自己的任務
