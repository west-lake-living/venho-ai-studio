# Automation Studio

Module 04 orchestrates existing VENHO AI Studio modules through adapters and YAML workflows.

```bash
venho auto list
venho auto actions
venho auto run venho_prompt_generation --dry-run
venho auto run venho_prompt_generation
```

Automation owns only run state, locks, and reports under `data/automation_runs/`. Module outputs and archive policy remain inside Module 01, 02, and 03.

