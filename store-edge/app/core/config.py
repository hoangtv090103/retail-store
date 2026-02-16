from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DB_URL: str
    DB_SYNC_URL: str
    
    class Config:
        env_file = ".env"

settings = Settings()