# How to Run the Studio UI

A thin local web UI over the existing CLI pipeline and Module 10 Dashboard.
It contains no business logic:

- Mode A / Mode B call `knowledge_studio.vision.pipeline.run_mode_a` /
  `run_mode_b`, the same functions `venho vision observe` uses.
- M10 Dashboard reads presentation snapshots from `dashboard.gateway`, which
  only normalizes existing M01-M09 config/artifacts for display.

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

- Open **M10 Dashboard** as the unified read-only presentation layer for
  Projects, Knowledge, Prompt/Content, Validator, Automation/Agent, Video,
  Publishing/Analytics, and System Monitor.
- Choose **Mode A** (observe any image) or **Mode B** (build DNA from
  multiple images of one subject)
- Pick project / subject / input folder
- Run and watch the pipeline log stream live
- View the resulting Markdown / JSON output inline

## M10 Guardrails

- No live provider API calls from dashboard tests.
- No standalone dashboard database; project config and module artifacts remain
  the source of truth.
- No duplicated scoring, prompt building, publishing, or analytics logic.
- Missing module artifacts degrade into advisory messages instead of crashing
  the UI.

## Deferred

- Failed-images gallery view
- Re-render overlay button
- Export compact DNA from the UI (use `venho vault export` for now)
- Direct M04/M07 write actions from the dashboard UI; approvals remain routed
  through module contracts.

## Notes

- Mode B still enforces the §2.1 one-subject confirmation — you must tick
  the checkbox before running.
- Provider defaults to `settings.yaml` if left blank. Use `mock` to test
  without API calls or cost.
- A blank input folder is rejected before the pipeline runs — it will not
  silently fall back to the repo root.
