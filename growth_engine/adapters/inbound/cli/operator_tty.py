from __future__ import annotations


class OperatorTtyUnavailable(RuntimeError):
    code = "ERR_GC2_OPERATOR_TTY_REQUIRED"


def read_tty_line(prompt: str, *, opener=None) -> str:
    """Read an operator response from the controlling terminal, never process stdin."""
    if opener is None:
        opener = open
    try:
        # Text update mode requires seeking, which terminal devices do not support.
        with (
            opener("/dev/tty", "r", encoding="utf-8") as terminal_input,
            opener("/dev/tty", "w", encoding="utf-8") as terminal_output,
        ):
            terminal_output.write(prompt)
            if not prompt.endswith((" ", "\n")):
                terminal_output.write(" ")
            terminal_output.flush()
            answer = terminal_input.readline()
    except OSError:
        raise OperatorTtyUnavailable("an interactive controlling terminal is required") from None
    if answer == "":
        raise OperatorTtyUnavailable("the controlling terminal closed before confirmation")
    return answer.rstrip("\r\n")


def confirm_from_tty(expected: str, prompt: str, *, opener=None) -> bool:
    return read_tty_line(prompt, opener=opener) == expected
