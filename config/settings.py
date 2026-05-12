from functools import lru_cache
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """All runtime configuration for NoteAlchemy."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    #models

    groq_api_key: str = Field(default="", description="Groq Cloud API key")

    

    whisper_model: str = Field(
        default="whisper-large-v3",
        description="Whisper model used for transcription",
    )
    structure_model: str = Field(
        default="llama-3.3-70b-versatile",
        description="LLM used to generate the notes outline (quality model)",
    )
    content_model: str = Field(
        default="llama-3.1-8b-instant",
        description="LLM used to write section content (speed model)",
    )
    #hyper parameters 
    structure_temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    content_temperature: float = Field(default=0.4, ge=0.0, le=2.0)
    structure_max_tokens: int = Field(default=1500, ge=100)
    content_max_tokens: int = Field(default=2000, ge=100)

    #file and network limits
    max_file_size_mb: int = Field(default=25, ge=1, description="Max audio upload size")
    max_retries: int = Field(default=3, ge=1, le=10)
    retry_delay_seconds: float = Field(default=2.0, ge=0.0)

    log_level: str = Field(default="INFO")

    #download youtube audio
    ytdlp_audio_format: str = Field(default="m4a")
    ytdlp_audio_quality: str = Field(default="5")  # 0 best, 9 worst

    @field_validator("log_level")
    @classmethod
    def _validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in allowed:
            raise ValueError(f"log_level must be one of {allowed}")
        return upper

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton Settings instance."""
    return Settings()






