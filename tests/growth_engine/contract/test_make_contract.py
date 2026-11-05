from __future__ import annotations

import json
from pathlib import Path

import jsonschema


def test_growth_command_v2_contract_rejects_unknown_fields() -> None:
    schema = json.loads(Path("contracts/growth_engine/command_envelope.v2.schema.json").read_text())
    fixture = {
        "_synthetic": True,
        "note": "cần thay bằng fixture thật từ P0-T03/P0-T04",
        "envelope": {
            "schema_version": "growth.command.v2",
            "environment": "test",
            "command_id": "command-synthetic",
            "delivery_id": "delivery-synthetic",
            "revision_id": "revision-synthetic",
            "channel_id": "channel-synthetic",
            "channel_key": "fb_hanoi",
            "platform": "facebook",
            "remote_page_id": "remote-page-synthetic",
            "idempotency_key": "publish:delivery-synthetic:revision-synthetic:1",
            "payload_hash": "a" * 64,
            "dispatch_epoch": "epoch-synthetic",
            "execute_before_ms": 1_800_000_000_000,
            "media_url": "https://example.test/media/synthetic.jpg?sig=synthetic",
            "command_token": "v1.c3ludGhldGlj.c2ln",
        },
    }

    jsonschema.validate(fixture["envelope"], schema)
    errors = list(
        jsonschema.Draft202012Validator(schema).iter_errors(
            {**fixture["envelope"], "token": "synthetic-extra-field"}
        )
    )
    assert any(error.validator == "additionalProperties" for error in errors)
