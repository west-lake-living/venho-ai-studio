import sys
import json
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.cli import parse_args
from core.logger import log
from core.media_loader import load_images
from core.batch_manager import make_batches
from core.dna_extractor import extract_dna
from core.knowledge_merger import merge_dna
from core.markdown_exporter import export

CONFIG_PATH = BASE_DIR / "config" / "settings.json"
CONFIG = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def main():
    args = parse_args()

    log("=" * 60)
    log("VENHO AI Studio — Knowledge Studio v0.1")
    log("=" * 60)
    log(f"Folder  : {args.folder}")
    log(f"Category: {args.category}")
    log(f"Batch   : {args.batch_size} ảnh/batch")
    if args.output_name:
        log(f"Output  : {args.output_name}")
    if args.dry_run:
        log("[DRY RUN] Chỉ scan — không gọi API")
    log("")

    # Resolve folder path (relative to BASE_DIR if not absolute)
    folder = args.folder if args.folder.is_absolute() else BASE_DIR / args.folder
    if not folder.exists():
        log(f"LỖI — Folder không tồn tại: {folder}")
        sys.exit(1)

    # Dry run: chỉ show plan
    if args.dry_run:
        images = load_images(folder)
        batches = make_batches(images, args.batch_size)
        log(f"\n[DRY RUN] Plan: {len(images)} ảnh → {len(batches)} batch")
        log("Không có API call nào được thực hiện.")
        return

    # Full run
    log("--- BƯỚC 1: Extraction (OpenAI) ---")
    batch_results = extract_dna(
        folder=folder,
        category=args.category,
        batch_size=args.batch_size,
        model=CONFIG["openai_model"],
    )

    log("")
    log("--- BƯỚC 2: Synthesis (Claude) ---")
    final_dna = merge_dna(
        batch_results=batch_results,
        category=args.category,
        model=CONFIG["claude_model"],
    )

    log("")
    log("--- BƯỚC 3: Export ---")
    images = load_images(folder)
    meta = {
        "category": args.category,
        "version": args.version,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "image_count": len(images),
        "batch_count": len(batch_results),
        "openai_model": CONFIG["openai_model"],
        "claude_model": CONFIG["claude_model"],
    }

    output_name = args.output_name or f"{args.category.upper()}_DNA_{args.version}"
    result = export(dna=final_dna, meta=meta, output_name=output_name)

    log("")
    log("=" * 60)
    log("HOÀN TẤT")
    log(f"Markdown : {result['md_path']}")
    log(f"JSON     : {result['json_path']}")
    log("=" * 60)


if __name__ == "__main__":
    main()
