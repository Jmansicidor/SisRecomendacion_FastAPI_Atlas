# core/config.py
import os
from typing import Annotated, Any, Literal
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyUrl, BeforeValidator, computed_field, Field
from urllib.parse import quote_plus, urlencode


def parse_cors(v: Any) -> list[str] | str:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",") if i.strip()]
    elif isinstance(v, (list, str)):
        return v
    raise ValueError(v)


def parse_hosts(v: str | list[str]) -> list[str]:
    if isinstance(v, str):
        return [h.strip() for h in v.split(",") if h.strip()]
    return v


def _none_if_blank(v: str | None) -> str | None:
    if isinstance(v, str):
        v = v.strip()
        return v if v else None
    return v


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_ignore_empty=True,
    )

    # App
    DOMAIN: str = "localhost"
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"
    JWT_SECRET_KEY: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_EXPIRES_MIN: int = 30
    JWT_REFRESH_EXPIRES_DAYS: int = 7

    @computed_field
    @property
    def server_host(self) -> str:
        return f"http://{self.DOMAIN}" if self.ENVIRONMENT == "local" else f"https://{self.DOMAIN}"

    BACKEND_CORS_ORIGINS: Annotated[list[AnyUrl] | str, BeforeValidator(
        parse_cors)] = Field(default_factory=list)

    # -------- Mongo (¡estos campos DEBEN existir!) --------
    MONGO_SCHEME: Literal["mongodb", "mongodb+srv"] = "mongodb"
    MONGO_USERNAME: str | None = None
    MONGO_PASSWORD: str | None = None
    MONGO_HOSTS: Annotated[list[str] | str, BeforeValidator(
        parse_hosts)] = "mongo"  # default para Docker Compose
    MONGO_PORT: int | None = 27017                 # para +srv debe ser None
    MONGO_DATABASE: str = "testuser"
    MONGO_AUTH_SOURCE: str | None = None
    MONGO_PARAMS: dict[str, str] | str = Field(default_factory=dict)

    # Permite anular todo con una URI ya armada (opcional)
    MONGO_URI_OVERRIDE: str | None = None
    # Aceptar alias si lo usabas antes (opcional)
    MONGO_URI: str | None = None

    @computed_field  # type: ignore[misc]
    @property
    def MONGODB_URI(self) -> str:
        # Respeta overrides si están seteados
        if self.MONGO_URI_OVERRIDE:
            return self.MONGO_URI_OVERRIDE
        if self.MONGO_URI:
            return self.MONGO_URI

        hosts = self.MONGO_HOSTS if isinstance(
            self.MONGO_HOSTS, list) else [self.MONGO_HOSTS]

        # auth: solo si hay user y password (evita el bug de "A password is required")
        user = _none_if_blank(self.MONGO_USERNAME)
        pwd = _none_if_blank(self.MONGO_PASSWORD)
        auth = ""
        if user and pwd:
            auth = f"{quote_plus(user)}:{quote_plus(pwd)}@"

        # host:port (para mongodb+srv NO va puerto)
        host_entries = []
        for h in hosts:
            if self.MONGO_SCHEME == "mongodb" and self.MONGO_PORT:
                host_entries.append(f"{h}:{self.MONGO_PORT}")
            else:
                host_entries.append(h)
        host_part = ",".join(host_entries)

        # query string
        if isinstance(self.MONGO_PARAMS, str) and self.MONGO_PARAMS.strip():
            query = f"?{self.MONGO_PARAMS.lstrip('?')}"
        else:
            params: dict[str, str] = {}
            if isinstance(self.MONGO_PARAMS, dict):
                params.update({str(k): str(v)
                              for k, v in self.MONGO_PARAMS.items()})
            # authSource solo si hay credenciales
            if user and pwd and _none_if_blank(self.MONGO_AUTH_SOURCE):
                params["authSource"] = self.MONGO_AUTH_SOURCE.strip()
            query = f"?{urlencode(params)}" if params else ""

        return f"{self.MONGO_SCHEME}://{auth}{host_part}/{self.MONGO_DATABASE}{query}"


# Singleton para usar en todo lado
_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


ALPHA = float(os.getenv("RANK_ALPHA", "0.7"))  # peso del coseno vs. jaccard
W_HAB = float(os.getenv("RANK_W_HAB", "0.45"))
W_EXP = float(os.getenv("RANK_W_EXP", "0.2"))
W_EDU = float(os.getenv("RANK_W_EDU", "0.35"))
# no lo estoy usando, se suma en los embeddings
W_IDI = float(os.getenv("RANK_W_IDI", "0"))
# % de similitud para contar en jaccard
THR_JACCARD = int(os.getenv("RANK_THR_JACCARD", "87"))
# si no está en config, usamos 87 por defecto
