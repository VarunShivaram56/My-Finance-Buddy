from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = f"sqlite:///{(BASE_DIR / 'my_finance_buddy.db').as_posix()}"
    agent_one_api_key: str = ""
    agent_two_api_key: str = ""
    agent_three_api_key: str = ""
    agent_one_model: str = "groq/compound"
    agent_two_model: str = "groq/compound"
    agent_three_model: str = "openai/gpt-oss-120b"
    embedding_model: str = "nomic-embed-text"
    chroma_dir: str = "./chroma_data"
    llm_confidence_threshold: float = 0.65
    llm_batch_size: int = 25
    max_insight_transactions: int = 40
    enable_ai_insights: bool = True
    enable_vector_memory: bool = False
    max_llm_categorization_merchants: int = 40
    max_ai_insight_statement_size: int = 80

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
