from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    APP_NAME: str = "AstaLink Backend"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Supabase
    # URL/anon/JWT are required (used at every request). Service-role is
    # optional — only loaded by the admin client, which is lazy.
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_JWT_SECRET: str
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    # Google Gemini — optional so the app boots without keys; the lazy chat /
    # embedding clients raise only when actually invoked.
    GOOGLE_API_KEY: str = ""
    GEMINI_CHAT_MODEL: str = "gemini-1.5-flash"
    GEMINI_EMBEDDING_MODEL: str = "text-embedding-004"

    # Pinecone — same lazy-boot philosophy.
    PINECONE_API_KEY: str = ""
    PINECONE_INDEX_NAME: str = "astalink-regulations"

    # CORS
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:3000"]


settings = Settings()
