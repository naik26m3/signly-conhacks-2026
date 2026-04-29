from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    gemini_api_key: str = ""
    elevenlabs_api_key: str = ""
    database_url: str = ""
    seaweedfs_filer_url: str = "http://seaweedfs-filer:8888"
    api_version: str = "v1"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
