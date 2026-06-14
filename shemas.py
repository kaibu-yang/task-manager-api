from pydantic import BaseModel
# 從 pydantic（資料驗證工具）匯入 BaseModel（基礎模型）

from typing import Optional
# Optional（選擇性）= 代表這個欄位可以填，也可以不填

# 建立任務時，使用者要傳進來的資料
# （沒有 id，因為 id 由資料庫自動產生）
class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    done: bool = False

# 回傳任務時的完整格式
# 繼承 TaskCreate，再多一個 id 欄位
class TaskRead(TaskCreate)
    id: int
    model_config = {"from_attributes": True}
# 讓 Pydantic 能從資料庫物件讀資料，沒有這行回傳時會出錯
