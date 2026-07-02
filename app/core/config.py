from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Telecom Knowledge Assistant"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    api_prefix: str = "/api/v1"
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-v4-flash"
    chroma_persist_dir: str = "./data/chroma"
    raw_data_dir: str = "./data/raw"
    processed_data_dir: str = "./data/processed"
    session_store_path: str = "./data/session_memory.db"
    knowledge_collection_name: str = "telecom_knowledge_base"
    chunk_size: int = 800
    chunk_overlap: int = 120
    retrieval_top_k: int = 4
    hybrid_candidate_k: int = 8
    rrf_k: int = 60
    keyword_min_score: float = 1.0
    vector_max_distance: float = 1.6
    min_answerable_matches: int = 1
    query_rewrite_enabled: bool = True
    llm_query_rewrite_enabled: bool = True
    query_rewrite_context_turns: int = 4

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
