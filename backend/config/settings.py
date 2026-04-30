from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # API
    api_version: str = "v1"

    # AI models
    gemini_api_key: str = ""
    elevenlabs_api_key: str = ""
    # ElevenLabs voice ID — find yours at elevenlabs.io/app/voice-lab
    # Default: "Rachel" (widely available on free plans)
    elevenlabs_voice_id: str = "21m00Tcm4TlvDq8ikWAM"

    # Langfuse LLM observability (optional — leave blank to disable)
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"

    # PostgreSQL
    database_url: str = "postgresql+asyncpg://aslbridge:changeme@postgres:5432/aslbridge"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # SeaweedFS
    seaweedfs_filer_url: str = "http://seaweedfs-filer:8888"

    class Config:
        env_file = ("../.env", ".env")
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()
