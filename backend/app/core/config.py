from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str
    postgres_port: int = 5432

    # Qdrant
    qdrant_host: str
    qdrant_port: int = 6333

    # Ollama
    ollama_host: str
    ollama_port: int = 11434
    ollama_llm_model: str
    ollama_embed_model: str

    # App
    app_secret_key: str
    app_debug: bool = False

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:"
            f"{self.postgres_password}@{self.postgres_host}:"
            f"{self.postgres_port}/{self.postgres_db}"
        )

    class Config:
        env_file = "../.env"
        env_file_encoding = "utf-8"

# Single instance used everywhere
settings = Settings()