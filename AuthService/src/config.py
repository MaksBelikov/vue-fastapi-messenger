from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DB_HOST: str
    DB_PORT: int 
    DB_USER: str
    DB_PASS: str
    DB_NAME: str
    PRIVATE_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    PUBLIC_KEY: str
    DB_ENGINE_ECHO: bool
    RABBIT_HOST: str
    RABBIT_USER: str
    RABBIT_PASS: str

    @property
    def DATABASE_URL_asyncpg(self):
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    
    model_config = SettingsConfigDict(env_file=".env")

settings = Settings() # type: ignore