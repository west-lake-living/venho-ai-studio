"""Test-session hygiene: no real secret ever reaches a test.

Why this file exists (2026-09-07). `providers/openai_provider.py`,
`providers/claude_provider.py` and `prompt_studio/optimizer.py` each call
`load_dotenv()` at *module import* time. Importing any of them -- which a
plain `pytest tests/` does during collection -- therefore pushed the real
contents of `.env` / `.env.local` into `os.environ` for the whole pytest
process. Two consequences, both observed:

* Six growth tests failed only in a full-suite run and passed in isolation,
  because a leaked `GOOGLE_DRIVE_TOKEN_JSON` made `google_drive_uploader_
  from_env` build a real uploader and blow up on `json.loads`. A test that
  passes alone and fails in company is the signature of exactly this.
* Any code path defaulting to `os.environ` could reach a *billed* provider
  from a test run. This repo's whole discipline is 0 API calls in tests.

The risk was written down in task_memory.md ("rủi ro thật ... CHƯA sửa") and
worked around test-by-test by injecting fakes. Working around it per test
only holds until someone writes the next test that forgets.

Neutralising `load_dotenv` here is belt-and-braces: the three modules now
load lazily (inside the functions that need a key), and this makes it
impossible for a *future* module-level call to reintroduce the leak. It runs
at conftest import, before any test module -- and so before those imports.
"""

from __future__ import annotations

import os

import dotenv

# Any module-level `from dotenv import load_dotenv` executed after this point
# binds the no-op below.
dotenv.load_dotenv = lambda *args, **kwargs: False  # type: ignore[assignment]
dotenv.main.load_dotenv = dotenv.load_dotenv  # type: ignore[attr-defined]

# ...and drop anything the developer's shell already exported, so a machine
# with real credentials in its environment behaves like clean CI.
_REAL_CREDENTIAL_KEYS = (
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_DRIVE_TOKEN_JSON",
    "GOOGLE_OAUTH_CLIENT_ID",
    "GOOGLE_OAUTH_CLIENT_SECRET",
    "TELEGRAM_BOT_TOKEN",
    "ZALO_ACCESS_TOKEN",
    "ZALO_REFRESH_TOKEN",
    "ZALO_APP_SECRET",
    "GMAIL_APP_PASSWORD",
    "MAKE_GROWTH_WEBHOOK_URL",
    "MAKE_WEBHOOK_URL",
    "TAVILY_API_KEY",
)

for _key in _REAL_CREDENTIAL_KEYS:
    os.environ.pop(_key, None)
