from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60  # longer than v2's 15 min -- no refresh flow to renew it

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


settings = Settings()
