from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_currency: str = "MXN"
    api_port: int = 7772
    bnr_xml_url: str = "https://www.bnr.ro/nbrfxrates.xml"
    data_csv_path: str = "../data/raw/date_converted.csv"
    openai_api_key: str = ""
    openai_model: str = ""
    gemini_api_key: str = ""
    gemini_model: str = ""
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"
    llm_provider_priority: str = "openai,gemini,ollama"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def backend_dir(self) -> Path:
        return Path(__file__).resolve().parents[1]

    @property
    def project_root(self) -> Path:
        return Path(__file__).resolve().parents[2]

    @property
    def resolved_data_csv_path(self) -> Path:
        configured = Path(self.data_csv_path)
        if configured.is_absolute():
            return configured
        return (self.backend_dir / configured).resolve()

    @property
    def processed_rates_path(self) -> Path:
        return self.project_root / "data" / "processed" / "rates.json"

    @property
    def reports_dir(self) -> Path:
        return self.project_root / "outputs" / "reports"

    @property
    def models_dir(self) -> Path:
        return self.project_root / "outputs" / "models"

    @property
    def provider_priority(self) -> List[str]:
        return [
            item.strip().lower()
            for item in self.llm_provider_priority.split(",")
            if item.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
