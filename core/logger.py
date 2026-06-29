from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent
LOG_DIR = BASE_DIR / "output" / "logs"


def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    month = datetime.now().strftime("%Y-%m")
    log_file = LOG_DIR / f"knowledge-studio-{month}.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(line + "\n")
