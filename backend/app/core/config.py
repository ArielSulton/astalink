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

    # Supabase Postgres connection string for LangGraph PostgresSaver.
    # Format: postgresql://postgres.<ref>:<password>@<host>:<port>/postgres
    SUPABASE_DB_URL: str = ""

    # News API (optional — N2a runs without it)
    NEWS_API_KEY: str = ""

    # WhatsApp Business API (Meta Cloud API)
    WHATSAPP_VERIFY_TOKEN: str = ""        # used during webhook subscription
    WHATSAPP_APP_SECRET: str = ""          # for signature verification
    WHATSAPP_ACCESS_TOKEN: str = ""        # for outbound messages
    WHATSAPP_PHONE_NUMBER_ID: str = ""     # for outbound messages
    APP_BASE_URL: str = "http://localhost:3000"  # for deep links

    # CORS
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:3000"]


settings = Settings()
