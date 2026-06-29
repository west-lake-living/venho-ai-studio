import argparse
import json
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
CONFIG_PATH = BASE_DIR / "config" / "settings.json"
CONFIG = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="knowledge-studio",
        description="VENHO AI Studio — Knowledge Studio v0.1\nPhân tích ảnh → trích xuất Visual DNA → xuất Markdown",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 app/main.py --folder assets/raw/room --category Room
  python3 app/main.py --folder assets/raw/rooftop --category Rooftop --batch-size 3
  python3 app/main.py --folder assets/raw/room --category Room --output-name ROOM_DNA_v0.1
  python3 app/main.py --folder assets/raw/room --category Room --dry-run
        """,
    )

    parser.add_argument(
        "--folder",
        type=Path,
        required=True,
        help="Folder chứa ảnh input (e.g. assets/raw/room)",
    )
    parser.add_argument(
        "--category",
        type=str,
        required=True,
        choices=CONFIG["categories"],
        help=f"Category: {', '.join(CONFIG['categories'])}",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=CONFIG["batch_size"],
        dest="batch_size",
        help=f"Số ảnh mỗi batch (default: {CONFIG['batch_size']})",
    )
    parser.add_argument(
        "--output-name",
        type=str,
        default=None,
        dest="output_name",
        help="Tên file output (không có extension). Default: {CATEGORY}_DNA_v0.1",
    )
    parser.add_argument(
        "--version",
        type=str,
        default="v0.1",
        help="Version label cho output file (default: v0.1)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="Chỉ scan ảnh và show batch plan, không gọi API",
    )

    return parser


def parse_args():
    parser = build_parser()
    return parser.parse_args()
