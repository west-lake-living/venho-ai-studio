from __future__ import annotations

import os
from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict, Field


_REQUIRED = "REQUIRED_FROM_P0"


class Settings(BaseModel):
    """Environment-backed runtime settings; secret fields are hidden from repr."""

    model_config = ConfigDict(frozen=True)

    env: str = "development"
    db_path: str = _REQUIRED
    media_root: str = _REQUIRED
    public_base_url: str = _REQUIRED
    capability_keys: str = Field(default=_REQUIRED, repr=False)
    service_tokens: str = Field(default=_REQUIRED, repr=False)
    make_webhook_urls: dict[str, str] = Field(default_factory=dict, repr=False)
    meta_read_tokens: dict[str, str] = Field(default_factory=dict, repr=False)
    telegram: dict[str, str] = Field(default_factory=dict, repr=False)

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> Settings:
        source = os.environ if environ is None else environ
        settings = cls(
            env=source.get("GE_ENV", "development"),
            db_path=source.get("GE_DB_PATH", _REQUIRED),
            media_root=source.get("GE_MEDIA_ROOT", _REQUIRED),
            public_base_url=source.get("GE_PUBLIC_BASE_URL", _REQUIRED),
            capability_keys=source.get("GE_CAPABILITY_KEYS", _REQUIRED),
            service_tokens=source.get("GE_SERVICE_TOKENS", _REQUIRED),
            make_webhook_urls=_read_prefix(source, "GE_MAKE_WEBHOOK_URL_"),
            meta_read_tokens=_read_prefix(source, "GE_META_READ_TOKEN_"),
            telegram=_read_prefix(source, "GE_TELEGRAM_"),
        )
        if settings.env.lower() == "production":
            settings._validate_production()
        return settings

    def _validate_production(self) -> None:
        required = {
            "GE_DB_PATH": self.db_path,
            "GE_MEDIA_ROOT": self.media_root,
            "GE_PUBLIC_BASE_URL": self.public_base_url,
            "GE_CAPABILITY_KEYS": self.capability_keys,
            "GE_SERVICE_TOKENS": self.service_tokens,
            "GE_TELEGRAM_BOT_TOKEN": self.telegram.get("BOT_TOKEN", ""),
            "GE_TELEGRAM_CHAT_ID": self.telegram.get("CHAT_ID", ""),
        }
        if not self.make_webhook_urls:
            required["GE_MAKE_WEBHOOK_URL_<KEY>"] = ""
        if not self.meta_read_tokens:
            required["GE_META_READ_TOKEN_<KEY>"] = ""
        for name, value in required.items():
            if not value.strip() or _REQUIRED in value:
                raise ValueError(f"{name} is empty or still contains {_REQUIRED}")
        for prefix, values in (
            ("GE_MAKE_WEBHOOK_URL_", self.make_webhook_urls),
            ("GE_META_READ_TOKEN_", self.meta_read_tokens),
            ("GE_TELEGRAM_", self.telegram),
        ):
            for key, value in values.items():
                if not value.strip() or _REQUIRED in value:
                    raise ValueError(f"{prefix}{key} is empty or still contains {_REQUIRED}")


def _read_prefix(environ: Mapping[str, str], prefix: str) -> dict[str, str]:
    return {
        name.removeprefix(prefix): value
        for name, value in environ.items()
        if name.startswith(prefix)
    }
