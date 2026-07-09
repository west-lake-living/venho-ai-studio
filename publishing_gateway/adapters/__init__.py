"""Platform adapter namespace for Publishing Gateway."""

from publishing_gateway.adapters.facebook import FacebookAdapter
from publishing_gateway.adapters.google_business import GoogleBusinessAdapter
from publishing_gateway.adapters.instagram import InstagramAdapter
from publishing_gateway.adapters.mock_adapter import MockAdapter
from publishing_gateway.adapters.threads import ThreadsAdapter

__all__ = ["FacebookAdapter", "GoogleBusinessAdapter", "InstagramAdapter", "MockAdapter", "ThreadsAdapter"]
