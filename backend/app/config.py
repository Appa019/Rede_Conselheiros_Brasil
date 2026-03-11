from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "conselheiros2024"
    pinecone_api_key: str = ""
    pinecone_index_name: str = "conselheiros-embeddings"
    cors_origins: list[str] = ["http://localhost:3000"]
    cvm_base_url: str = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/FRE/DADOS"
    data_dir: str = "data"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
