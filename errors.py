class AppError(Exception):  # 自訂錯誤類別，繼承 Exception 才能被 raise
    def __init__(self, status_code: int, code: str, message: str):  # 建立錯誤時要給三個資料
        super().__init__(message)  # 先讓父類別 Exception 記住訊息，印錯誤時看得到
        self.status_code = status_code  # HTTP 狀態碼，例如 404
        self.code = code  # 英文錯誤代碼，給程式判斷用，例如 TASK_NOT_FOUND
        self.message = message  # 中文錯誤訊息，給人看，例如「找不到這筆任務」
