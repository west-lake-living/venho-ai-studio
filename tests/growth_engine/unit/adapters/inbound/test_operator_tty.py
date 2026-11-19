from __future__ import annotations

import pytest

from growth_engine.adapters.inbound.cli.operator_tty import (
    OperatorTtyUnavailable,
    confirm_from_tty,
    read_tty_line,
)


class _FakeTty:
    def __init__(self, answer: str) -> None:
        self.answer = answer
        self.prompt_text = ""

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def write(self, value: str) -> int:
        self.prompt_text += value
        return len(value)

    def flush(self) -> None:
        return None

    def readline(self) -> str:
        return self.answer


def test_confirmation_opens_controlling_tty_and_never_reads_stdin() -> None:
    opened: list[tuple[str, str, str]] = []
    terminal = _FakeTty("REPROCESS\n")

    def opener(path: str, mode: str, *, encoding: str):
        opened.append((path, mode, encoding))
        return terminal

    assert confirm_from_tty("REPROCESS", "Type REPROCESS:", opener=opener)
    assert opened == [("/dev/tty", "r", "utf-8"), ("/dev/tty", "w", "utf-8")]
    assert "Type REPROCESS:" in terminal.prompt_text


def test_confirmation_refuses_if_controlling_tty_is_unavailable() -> None:
    def opener(*_args, **_kwargs):
        raise OSError("no controlling terminal")

    with pytest.raises(OperatorTtyUnavailable) as error:
        read_tty_line("confirm", opener=opener)
    assert error.value.code == "ERR_GC2_OPERATOR_TTY_REQUIRED"
