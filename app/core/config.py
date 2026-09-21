from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "PetShop Stock API"
    # SQLite por defecto para demo local sin Docker.
    # Para prod/Postgres: DATABASE_URL=postgresql+psycopg2://petshop:petshop@db:5432/petshop
    database_url: str = "sqlite:///./petshop.db"
    secret_key: str = "cambiar-en-produccion-petshop-demo-2026"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 8

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
