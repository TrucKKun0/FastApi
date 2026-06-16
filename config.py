from pydantic import SecretStr
from pydantic_settings import BaseSettings,SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file = ".env",
        env_file_encoding = "utf-8",
    )
    secret_key : SecretStr
    algorithm : str = "HS256"
    access_token_expires_minutes : int = 30
    max_upload_size_bytes : int = 5 * 1024 * 1024
    post_per_page : int= 10
    reset_token_expire_minute : int = 60
    mail_server : str = "localhost"
    mail_username : str = ""
    mail_port : int = 587
    mail_password : SecretStr = SecretStr("")
    mail_from : str = "noreply@example.com"
    mail_user_tls : bool = True 
    front_end_url : str = "http://localhost:8000"
    database_url : str

settings = Settings()