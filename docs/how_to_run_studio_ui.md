# How to Run the Studio UI (Phase 8 MVP)

A thin local web UI over the existing CLI pipeline. It contains no business
logic — it only calls `knowledge_studio.vision.pipeline.run_mode_a` /
`run_mode_b`, the same functions `venho vision observe` uses. If the CLI and
the UI ever disagree, the UI is wrong (Master Plan v2.5 §4 Phase 8).

## Install

```bash
pip install -e ".[ui]"
```

This adds `streamlit` on top of the base install.

## Run

```bash
streamlit run ui/studio_app.py
```

Opens at `http://localhost:8501`. Runs entirely local — no deploy, no extra
hosting cost.

## What it does (v1 scope)

- Choose **Mode A** (observe any image) or **Mode B** (build DNA from
  multiple images of one subject)
- Pick project / subject / input folder
- Run and watch the pipeline log stream live
- View the resulting Markdown / JSON output inline

## Not in v1 (deferred)

- Failed-images gallery view
- DNA manifest viewer
- Re-render overlay button
- Export compact DNA from the UI (use `venho vault export` for now)

## Notes

- Mode B still enforces the §2.1 one-subject confirmation — you must tick
  the checkbox before running.
- Provider defaults to `settings.yaml` if left blank. Use `mock` to test
  without API calls or cost.
- A blank input folder is rejected before the pipeline runs — it will not
  silently fall back to the repo root.
