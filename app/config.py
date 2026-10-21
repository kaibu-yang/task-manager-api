from pydantic_settings import BaseSettings, SettingsConfigDict  # 匯入設定基底類別與設定選項

class Settings(BaseSettings):  # 櫃台：繼承 BaseSettings，會自動去環境變數和 .env 找同名的值
    database_url: str  # 資料庫連線字串；沒有預設值 = 必填，缺了就拒絕啟動
    secret_key: str  # JWT 手環的簽名密鑰；同樣必填
    algorithm: str = "HS256"  # 加密演算法；有預設值 = 選填，沒寫就用 HS256

    model_config = SettingsConfigDict(env_file=".env")  # 告訴櫃台：也要去讀 .env 這個檔案

settings = Settings()  # 建立櫃台並立刻清點；缺東西會在這一行直接報錯
