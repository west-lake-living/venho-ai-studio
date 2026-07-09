from __future__ import annotations

import os
from typing import Optional

from publishing_gateway.exceptions import ERR_TOKEN_INVALID, PublishingGatewayError


class TokenVault:
    def get(self, env_name: str, required: bool = True) -> Optional[str]:
        value = os.environ.get(env_name)
        if required and not value:
            raise PublishingGatewayError(f"missing token env: {env_name}", ERR_TOKEN_INVALID)
        return value

    def refresh(self, platform: str) -> None:
        raise PublishingGatewayError(f"token refresh is not implemented for {platform}", ERR_TOKEN_INVALID)
