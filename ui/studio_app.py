"""VENHO AI Studio — Studio Shell + Module 10 Dashboard.

Thin UI over the existing CLI pipeline (Mode A / Mode B). This file must not
contain business logic. The M10 dashboard only reads normalized presentation
snapshots from `dashboard.gateway`.

Run:
    streamlit run ui/studio_app.py
"""

from __future__ import annotations

import contextlib
import html
import io
import sys
import threading
import time
from pathlib import Path

import streamlit as st

BASE_DIR = Path(__file__).parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from dashboard.gateway import build_dashboard_snapshot  # noqa: E402
from knowledge_studio.vision.pipeline import run_mode_a, run_mode_b  # noqa: E402


class _LineCapture(io.TextIOBase):
    """Captures print() output line by line so the UI can poll it while a
    background thread runs the pipeline (pipeline logs via print(), see
    shared/logging.py)."""

    def __init__(self) -> None:
        self.lines: list[str] = []
        self._buffer = ""

    def write(self, s: str) -> int:
        self._buffer += s
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            self.lines.append(line)
        return len(s)

    def flush(self) -> None:
        pass


def _list_subjects(project: str) -> list[str]:
    subjects_dir = BASE_DIR / "config" / "projects" / project / "subjects"
    if not subjects_dir.is_dir():
        return []
    names = sorted(
        p.stem for p in subjects_dir.glob("*.yaml") if not p.name.endswith(".overrides.yaml")
    )
    return names


def _list_media_subfolders(project: str) -> list[str]:
    media_dir = BASE_DIR / "data" / "projects" / project / "media"
    if not media_dir.is_dir():
        return []
    return sorted(d.name for d in media_dir.iterdir() if d.is_dir())


def _run_with_live_log(target, kwargs: dict) -> tuple[dict | None, str | None, list[str]]:
    """Run `target(**kwargs)` in a background thread while streaming its
    print() output into the UI. Returns (result, error, log_lines)."""
    capture = _LineCapture()
    result_holder: dict = {}

    def _worker() -> None:
        try:
            with contextlib.redirect_stdout(capture):
                result_holder["result"] = target(**kwargs)
        except Exception as e:  # noqa: BLE001 — surfaced to the UI, not swallowed
            result_holder["error"] = str(e)

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()

    log_box = st.empty()
    with st.spinner("Đang chạy pipeline..."):
        while thread.is_alive():
            log_box.code("\n".join(capture.lines[-300:]) or "Đang khởi động...", language="text")
            time.sleep(0.4)
    thread.join()
    log_box.code("\n".join(capture.lines[-500:]), language="text")

    return result_holder.get("result"), result_holder.get("error"), capture.lines


def _show_output_paths(paths: dict) -> None:
    for label, path in paths.items():
        path = Path(path)
        st.markdown(f"**{label}** — `{path}`")
        if path.suffix == ".md" and path.exists():
            with st.expander(f"Xem nội dung: {path.name}", expanded=(label == "md")):
                st.markdown(path.read_text(encoding="utf-8"))
        elif path.suffix == ".json" and path.exists():
            with st.expander(f"Xem nội dung: {path.name}"):
                st.code(path.read_text(encoding="utf-8"), language="json")


def _install_operating_center_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --oc-primary: #2F6F91;
            --oc-primary-soft: #EAF3F7;
            --oc-background: #F8F7F4;
            --oc-surface: #FFFFFF;
            --oc-border: #E8E5DF;
            --oc-text: #2B2B2B;
            --oc-secondary: #6B6B6B;
            --oc-muted: #9A958E;
            --oc-success: #5F8F6F;
            --oc-success-soft: #EEF6F0;
            --oc-warning: #D9A441;
            --oc-warning-soft: #FFF6E4;
            --oc-critical: #C96A5C;
            --oc-critical-soft: #FDECEA;
            --oc-radius-card: 16px;
            --oc-shadow-card: 0 2px 10px rgba(0,0,0,0.05);
            --oc-shadow-hover: 0 8px 24px rgba(0,0,0,0.08);
        }
        .stApp { background: var(--oc-background); color: var(--oc-text); }
        .block-container {
            max-width: 1280px;
            padding: 24px 32px 72px;
        }
        [data-testid="stSidebar"] {
            background: var(--oc-surface);
            border-right: 1px solid var(--oc-border);
            min-width: 240px;
            width: 240px;
        }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
        [data-testid="stSidebar"] label {
            color: var(--oc-text);
            font-size: 14px;
        }
        .oc-top-header {
            align-items: center;
            background: var(--oc-surface);
            border: 1px solid var(--oc-border);
            border-radius: var(--oc-radius-card);
            box-shadow: var(--oc-shadow-card);
            display: grid;
            gap: 20px;
            grid-template-columns: 1fr auto auto;
            min-height: 80px;
            margin-bottom: 24px;
            padding: 18px 24px;
        }
        .oc-brand-title { color: var(--oc-text); font-size: 18px; font-weight: 700; line-height: 1.2; }
        .oc-brand-subtitle { color: var(--oc-secondary); font-size: 12px; font-weight: 500; margin-top: 4px; }
        .oc-header-meta {
            align-items: center;
            color: var(--oc-secondary);
            display: flex;
            flex-wrap: wrap;
            font-size: 13px;
            gap: 10px;
            justify-content: center;
        }
        .oc-header-actions { color: var(--oc-primary); display: flex; font-size: 20px; gap: 14px; }
        .oc-card {
            background: var(--oc-surface);
            border: 1px solid var(--oc-border);
            border-radius: var(--oc-radius-card);
            box-shadow: var(--oc-shadow-card);
            padding: 24px;
        }
        .oc-card:hover { box-shadow: var(--oc-shadow-hover); }
        .oc-section-title {
            color: var(--oc-text);
            font-size: 22px;
            font-weight: 700;
            letter-spacing: 0;
            margin: 0 0 16px;
        }
        .oc-label {
            color: var(--oc-muted);
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 0;
            text-transform: uppercase;
        }
        .oc-muted { color: var(--oc-secondary); font-size: 14px; }
        .oc-small { color: var(--oc-muted); font-size: 12px; }
        .oc-badge {
            border-radius: 999px;
            display: inline-flex;
            font-size: 12px;
            font-weight: 700;
            padding: 6px 10px;
            white-space: nowrap;
        }
        .oc-tone-success { background: var(--oc-success-soft); color: var(--oc-success); }
        .oc-tone-warning { background: var(--oc-warning-soft); color: #8A621A; }
        .oc-tone-critical { background: var(--oc-critical-soft); color: var(--oc-critical); }
        .oc-tone-info { background: var(--oc-primary-soft); color: var(--oc-primary); }
        .oc-tone-muted { background: #F2F0EC; color: var(--oc-secondary); }
        .oc-btn {
            align-items: center;
            background: var(--oc-primary);
            border-radius: 999px;
            color: #fff;
            display: inline-flex;
            font-size: 14px;
            font-weight: 700;
            justify-content: center;
            min-height: 40px;
            padding: 0 18px;
            text-decoration: none;
            white-space: nowrap;
        }
        .oc-btn-secondary { background: var(--oc-primary-soft); color: var(--oc-primary); }
        .oc-focus-card {
            align-items: center;
            display: grid;
            gap: 24px;
            grid-template-columns: 1fr auto;
            min-height: 170px;
            padding: 28px;
        }
        .oc-focus-title {
            color: var(--oc-text);
            font-size: 32px;
            font-weight: 700;
            line-height: 1.15;
            margin: 8px 0 10px;
        }
        .oc-progress {
            background: #EEEAE3;
            border-radius: 999px;
            height: 8px;
            margin-top: 20px;
            overflow: hidden;
            width: min(520px, 100%);
        }
        .oc-progress-fill {
            background: var(--oc-primary);
            border-radius: inherit;
            height: 100%;
            width: 38%;
        }
        .oc-focus-side {
            align-items: flex-end;
            display: flex;
            flex-direction: column;
            gap: 18px;
        }
        .oc-status-grid {
            display: grid;
            gap: 16px;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            margin: 24px 0;
        }
        .oc-status-card {
            min-height: 120px;
            padding: 20px;
        }
        .oc-status-icon {
            align-items: center;
            background: var(--oc-primary-soft);
            border-radius: 12px;
            color: var(--oc-primary);
            display: inline-flex;
            font-size: 18px;
            height: 36px;
            justify-content: center;
            margin-bottom: 14px;
            width: 36px;
        }
        .oc-status-metric {
            color: var(--oc-text);
            font-size: 28px;
            font-weight: 700;
            line-height: 1.05;
            margin: 6px 0 10px;
        }
        .oc-link { color: var(--oc-primary); font-size: 13px; font-weight: 700; }
        .oc-two-col {
            display: grid;
            gap: 24px;
            grid-template-columns: 2fr 1fr;
            margin-bottom: 24px;
        }
        .oc-task-row {
            align-items: center;
            border-top: 1px solid var(--oc-border);
            display: grid;
            gap: 14px;
            grid-template-columns: 32px 1fr auto;
            min-height: 64px;
            padding: 12px 0;
        }
        .oc-task-icon {
            align-items: center;
            border-radius: 10px;
            display: flex;
            font-size: 15px;
            height: 32px;
            justify-content: center;
            width: 32px;
        }
        .oc-task-title { color: var(--oc-text); font-size: 14px; font-weight: 700; }
        .oc-action-grid {
            display: grid;
            gap: 12px;
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }
        .oc-action-chip {
            align-items: center;
            background: var(--oc-primary-soft);
            border: 1px solid #D7E8EF;
            border-radius: 999px;
            color: var(--oc-primary);
            display: flex;
            font-size: 13px;
            font-weight: 700;
            justify-content: center;
            min-height: 52px;
            padding: 0 14px;
            text-align: center;
        }
        .oc-pipeline {
            display: flex;
            gap: 16px;
            overflow-x: auto;
            padding-bottom: 4px;
        }
        .oc-stage {
            flex: 0 0 140px;
            min-height: 150px;
            padding: 16px;
            position: relative;
        }
        .oc-stage:not(:last-child)::after {
            color: var(--oc-muted);
            content: ">";
            font-size: 18px;
            font-weight: 700;
            position: absolute;
            right: -13px;
            top: 58px;
        }
        .oc-stage-title { color: var(--oc-text); font-size: 16px; font-weight: 700; margin-bottom: 12px; }
        .oc-stage-meta { color: var(--oc-secondary); font-size: 12px; line-height: 1.5; margin-top: 12px; }
        .oc-alert {
            border-left: 4px solid var(--oc-warning);
            border-radius: 14px;
            margin-top: 12px;
            padding: 16px;
        }
        .oc-alert-critical { background: var(--oc-critical-soft); border-left-color: var(--oc-critical); }
        .oc-alert-warning { background: var(--oc-warning-soft); border-left-color: var(--oc-warning); }
        .oc-alert-title { color: var(--oc-text); font-size: 14px; font-weight: 700; margin-bottom: 4px; }
        .oc-health-row {
            align-items: center;
            border-top: 1px solid var(--oc-border);
            display: grid;
            gap: 12px;
            grid-template-columns: 26px 1fr auto;
            min-height: 48px;
        }
        .oc-timeline-row {
            border-top: 1px solid var(--oc-border);
            display: grid;
            gap: 16px;
            grid-template-columns: 64px 1fr;
            padding: 14px 0;
        }
        .oc-page-head {
            margin: 0 0 24px;
        }
        .oc-page-title {
            color: var(--oc-text);
            font-size: 32px;
            font-weight: 700;
            letter-spacing: 0;
            line-height: 1.15;
            margin: 0 0 8px;
        }
        .oc-card-grid {
            display: grid;
            gap: 16px;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            margin-bottom: 24px;
        }
        .oc-mini-card {
            min-height: 150px;
            padding: 20px;
        }
        .oc-mini-title {
            color: var(--oc-text);
            font-size: 16px;
            font-weight: 700;
            line-height: 1.25;
            margin: 8px 0;
        }
        .oc-mini-meta {
            color: var(--oc-secondary);
            font-size: 13px;
            line-height: 1.45;
            min-height: 38px;
        }
        .oc-mini-footer {
            align-items: center;
            display: flex;
            gap: 10px;
            justify-content: space-between;
            margin-top: 16px;
        }
        .oc-section-gap { margin-top: 24px; }
        .oc-empty {
            color: var(--oc-secondary);
            font-size: 14px;
            line-height: 1.55;
        }
        .oc-bottom-nav { display: none; }
        @media (max-width: 767px) {
            .block-container { padding: 16px 16px 92px; }
            [data-testid="stSidebar"] { display: none; }
            .oc-top-header {
                grid-template-columns: 1fr auto;
                min-height: 64px;
                padding: 14px 16px;
            }
            .oc-header-meta { display: none; }
            .oc-focus-card { grid-template-columns: 1fr; min-height: auto; padding: 22px; }
            .oc-focus-title { font-size: 26px; }
            .oc-focus-side { align-items: stretch; }
            .oc-status-grid {
                display: flex;
                overflow-x: auto;
                scroll-snap-type: x mandatory;
            }
            .oc-status-card { flex: 0 0 220px; scroll-snap-align: start; }
            .oc-two-col { grid-template-columns: 1fr; }
            .oc-action-grid { display: flex; overflow-x: auto; }
            .oc-action-chip { flex: 0 0 auto; min-height: 44px; }
            .oc-pipeline { flex-direction: column; overflow: visible; }
            .oc-stage { flex: 1 1 auto; min-height: auto; }
            .oc-stage:not(:last-child)::after {
                content: "v";
                left: 50%;
                right: auto;
                top: auto;
                bottom: -18px;
                transform: translateX(-50%);
            }
            .oc-task-row { grid-template-columns: 32px 1fr; }
            .oc-task-row .oc-btn { grid-column: 1 / -1; }
            .oc-timeline-row { grid-template-columns: 1fr; gap: 4px; }
            .oc-page-title { font-size: 26px; }
            .oc-card-grid { grid-template-columns: 1fr; }
            .oc-bottom-nav {
                align-items: center;
                background: var(--oc-surface);
                border-top: 1px solid var(--oc-border);
                bottom: 0;
                display: grid;
                grid-template-columns: repeat(5, 1fr);
                height: 72px;
                left: 0;
                position: fixed;
                right: 0;
                z-index: 9999;
            }
            .oc-bottom-item {
                color: var(--oc-secondary);
                font-size: 11px;
                font-weight: 700;
                text-align: center;
            }
            .oc-bottom-item:first-child { color: var(--oc-primary); }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def _status_tone(status: str) -> str:
    normalized = status.lower().replace("_", " ")
    if any(word in normalized for word in ["critical", "failed", "failure", "reject", "needs attention"]):
        return "critical"
    if any(word in normalized for word in ["warning", "review", "missing", "conditional"]):
        return "warning"
    if any(word in normalized for word in ["healthy", "ready", "approved", "completed", "active"]):
        return "success"
    if any(word in normalized for word in ["running", "progress"]):
        return "info"
    return "muted"


def _status_pill(status: str) -> str:
    return f'<span class="oc-badge oc-tone-{_status_tone(status)}">{_esc(status)}</span>'


def _action_for_label(label: str) -> str:
    actions = {
        "Today's Tasks": "Open",
        "System Security": "Review",
        "Automation Engine": "Continue",
        "Publishing Queue": "Open queue",
    }
    return actions.get(label, "Open")


def _status_icon(label: str) -> str:
    icons = {
        "Today's Tasks": "T",
        "System Security": "S",
        "Automation Engine": "A",
        "Publishing Queue": "P",
    }
    return icons.get(label, "O")


def _render_operating_header(snapshot) -> None:
    header = snapshot.operating_center.get("header", {})
    st.markdown(
        f"""
        <div class="oc-top-header">
            <div>
                <div class="oc-brand-title">{_esc(header.get('title', 'VENHO AI Studio'))}</div>
                <div class="oc-brand-subtitle">{_esc(header.get('subtitle', 'Operating Center'))}</div>
            </div>
            <div class="oc-header-meta">
                <strong>{_esc(header.get('project_scope', snapshot.project.display_name))}</strong>
                <span>{_status_pill(str(header.get('project_status', 'ACTIVE')))}</span>
                <span>Last Sync {_esc(header.get('last_sync', 'Recent'))}</span>
                <span>{_esc(header.get('mode', 'Read-only'))}</span>
            </div>
            <div class="oc-header-actions" aria-hidden="true">
                <span>!</span><span>U</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_summary_cards(cards: list[dict]) -> None:
    items = []
    for card in cards:
        label = str(card["label"])
        status = str(card.get("status", "Ready"))
        items.append(
            f"""
            <div class="oc-card oc-status-card">
                <div class="oc-status-icon">{_esc(_status_icon(label))}</div>
                <div class="oc-label">{_esc(label)}</div>
                <div class="oc-status-metric">{_esc(card["value"])}</div>
                <div class="oc-link">{_esc(_action_for_label(label))} &gt;</div>
                <div style="margin-top: 10px;">{_status_pill(status)}</div>
            </div>
            """
        )
    st.markdown(f'<div class="oc-status-grid">{"".join(items)}</div>', unsafe_allow_html=True)


def _render_current_focus(focus: dict) -> None:
    detail = focus.get("progress_label") or "No active workflow selected"
    st.markdown(
        f"""
        <div class="oc-card oc-focus-card">
            <div>
                <div class="oc-label">Current Focus</div>
                <div class="oc-focus-title">{_esc(focus.get('title', 'No active focus.'))}</div>
                <div class="oc-muted">Progress: {_esc(detail)}</div>
                <div class="oc-progress"><div class="oc-progress-fill"></div></div>
            </div>
            <div class="oc-focus-side">
                {_status_pill(str(focus.get('status', 'Ready')))}
                <span class="oc-btn">{_esc(focus.get('action_label', 'Continue'))}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_today(tasks: list[dict], progress: dict) -> None:
    completed = progress.get("completed", 0)
    total = progress.get("total", len(tasks))
    groups_html = []
    groups = ["High", "Medium", "Low", "Completed"]
    for group in groups:
        rows = [task for task in tasks if task.get("priority") == group or task.get("status") == group]
        if not rows:
            continue
        group_title = f"{group} Priority" if group != "Completed" else "Completed"
        groups_html.append(f'<div class="oc-label" style="margin-top: 18px;">{_esc(group_title)}</div>')
        for task in rows:
            tone = "success" if group == "Completed" else ("critical" if group == "High" else "warning")
            marker = "OK" if group == "Completed" else "!"
            groups_html.append(
                f"""
                <div class="oc-task-row">
                    <div class="oc-task-icon oc-tone-{tone}">{_esc(marker)}</div>
                    <div>
                        <div class="oc-task-title">{_esc(task['task'])}</div>
                        <div class="oc-small">{_esc(task['source'])} · {_esc(task.get('status', 'Pending'))}</div>
                    </div>
                    <span class="oc-btn oc-btn-secondary">{_esc(task.get('action_label', 'Open'))}</span>
                </div>
                """
            )
    st.markdown(
        f"""
        <div class="oc-card">
            <h2 class="oc-section-title">Today Task Center</h2>
            <div class="oc-muted">Today progress: <strong>{_esc(completed)} / {_esc(total)}</strong> tasks completed</div>
            {''.join(groups_html)}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_quick_actions(actions: list[dict]) -> None:
    buttons = "".join(f'<div class="oc-action-chip">{_esc(action["label"])}</div>' for action in actions)
    st.markdown(
        f"""
        <div class="oc-card">
            <h2 class="oc-section-title">Quick Actions</h2>
            <div class="oc-action-grid">{buttons}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_health(health: list[dict]) -> None:
    rows = []
    for item in health:
        status = str(item["status"])
        rows.append(
            f"""
            <div class="oc-health-row">
                <div class="oc-small">{_esc(item['area'][:1])}</div>
                <div class="oc-task-title">{_esc(item['area'])}</div>
                {_status_pill(status)}
            </div>
            """
        )
    st.markdown(
        f'<div class="oc-card"><h2 class="oc-section-title">System Health</h2>{"".join(rows)}</div>',
        unsafe_allow_html=True,
    )


def _render_pipeline(pipeline: list[dict]) -> None:
    stages = []
    for row in pipeline:
        stages.append(
            f"""
            <div class="oc-card oc-stage">
                <div class="oc-stage-title">{_esc(row['stage'])}</div>
                {_status_pill(str(row['status']))}
                <div class="oc-stage-meta">
                    Ready: {_esc(row['ready'])}<br>
                    Need Review: {_esc(row['need_review'])}<br>
                    Failed: {_esc(row['failed'])}<br>
                    <strong>{_esc(row['action'])}</strong>
                </div>
            </div>
            """
        )
    st.markdown(
        f"""
        <div class="oc-card" style="margin-bottom: 24px;">
            <h2 class="oc-section-title">Pipeline Flow</h2>
            <div class="oc-pipeline">{''.join(stages)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_alerts(alerts: list[dict]) -> None:
    if not alerts:
        st.markdown(
            """
            <div class="oc-card">
                <h2 class="oc-section-title">Alerts</h2>
                <div class="oc-alert oc-alert-warning">
                    <div class="oc-alert-title">All systems healthy</div>
                    <div class="oc-muted">No urgent action is needed right now.</div>
                    <div class="oc-link" style="margin-top: 8px;">Keep monitoring &gt;</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return
    rows = []
    for alert in alerts:
        status = str(alert["status"])
        severity = "critical" if status == "Critical" else "warning"
        action = "Review now" if severity == "critical" else "Open workflow"
        rows.append(
            f"""
            <div class="oc-alert oc-alert-{severity}">
                <div class="oc-alert-title">{_esc(status)}</div>
                <div class="oc-muted">{_esc(alert['message'])}</div>
                <div class="oc-link" style="margin-top: 8px;">{_esc(action)} &gt;</div>
            </div>
            """
        )
    st.markdown(
        f'<div class="oc-card"><h2 class="oc-section-title">Alerts</h2>{"".join(rows)}</div>',
        unsafe_allow_html=True,
    )


def _render_recent_activity(activity: list[dict]) -> None:
    if not activity:
        st.markdown(
            """
            <div class="oc-card">
                <h2 class="oc-section-title">Recent Activity</h2>
                <div class="oc-muted">No recent activity yet.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return
    rows = []
    for item in activity:
        rows.append(
            f"""
            <div class="oc-timeline-row">
                <div class="oc-small">{_esc(item['time'])}</div>
                <div>
                    <div class="oc-task-title">{_esc(item['event'])}</div>
                    <div class="oc-small">{_esc(item.get('detail', ''))}</div>
                </div>
            </div>
            """
        )
    st.markdown(
        f'<div class="oc-card"><h2 class="oc-section-title">Recent Activity</h2>{"".join(rows)}</div>',
        unsafe_allow_html=True,
    )


def _render_page_header(title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="oc-page-head">
            <h1 class="oc-page-title">{_esc(title)}</h1>
            <div class="oc-muted">{_esc(subtitle)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_empty_card(title: str, message: str, action: str = "Open Home") -> None:
    st.markdown(
        f"""
        <div class="oc-card" style="margin-bottom: 24px;">
            <div class="oc-label">{_esc(title)}</div>
            <div class="oc-empty" style="margin-top: 10px;">{_esc(message)}</div>
            <div class="oc-link" style="margin-top: 14px;">{_esc(action)} &gt;</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_card_grid(title: str, cards: list[dict[str, object]], empty_message: str) -> None:
    if not cards:
        _render_empty_card(title, empty_message)
        return
    rendered = []
    for card in cards:
        status = str(card.get("status", "Ready"))
        rendered.append(
            f"""
            <div class="oc-card oc-mini-card">
                <div class="oc-label">{_esc(card.get('label', title))}</div>
                <div class="oc-mini-title">{_esc(card.get('title', 'Untitled'))}</div>
                <div class="oc-mini-meta">{_esc(card.get('meta', ''))}</div>
                <div class="oc-mini-footer">
                    {_status_pill(status)}
                    <span class="oc-link">{_esc(card.get('action', 'Open'))} &gt;</span>
                </div>
            </div>
            """
        )
    st.markdown(
        f"""
        <div class="oc-section-gap">
            <h2 class="oc-section-title">{_esc(title)}</h2>
            <div class="oc-card-grid">{''.join(rendered)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _validation_failed(row: dict) -> bool:
    return str(row.get("verdict") or row.get("status") or "").lower() in {
        "fail",
        "failed",
        "reject",
        "rejected",
        "regenerate",
    }


def _cards_from_records(records: list[dict], *, label: str, title_key: str, status_key: str = "status") -> list[dict[str, object]]:
    cards = []
    for index, row in enumerate(records):
        title = row.get(title_key) or row.get("id") or row.get("run_id") or row.get("path") or f"Item {index + 1}"
        status = row.get(status_key) or row.get("verdict") or "Available"
        path = row.get("path") or row.get("report_md") or row.get("report_json") or ""
        meta_parts = []
        if row.get("project"):
            meta_parts.append(f"Project: {row['project']}")
        if row.get("platforms"):
            meta_parts.append(f"Platforms: {', '.join(str(item) for item in row['platforms'])}")
        if row.get("workflow_id"):
            meta_parts.append(f"Workflow: {row['workflow_id']}")
        if path:
            meta_parts.append(str(path))
        cards.append(
            {
                "label": label,
                "title": title,
                "meta": " · ".join(meta_parts) or "Ready for review",
                "status": status,
                "action": "Open",
            }
        )
    return cards


def _render_workbench(snapshot) -> None:
    _render_page_header("Workbench", "Continue and complete production work without reading module internals.")
    _render_current_focus(snapshot.operating_center["current_focus"])
    _render_quick_actions(snapshot.operating_center["quick_actions"])

    pending = [
        {
            "label": "Pipeline Review",
            "title": row["stage"],
            "meta": f"Need review: {row['need_review']} · Failed: {row['failed']}",
            "status": row["status"],
            "action": row["action"],
        }
        for row in snapshot.operating_center["pipeline"]
        if row["need_review"] or row["failed"]
    ]
    _render_card_grid("Pending Reviews", pending, "No workflow stages need review right now.")
    _render_card_grid(
        "Draft Outputs",
        _cards_from_records(snapshot.content_items, label="Content Draft", title_key="id"),
        "No content drafts available yet.",
    )
    _render_card_grid(
        "Ready To Publish",
        _cards_from_records(snapshot.publishing_items, label="Publishing Item", title_key="id"),
        "No approved publishing package is ready yet.",
    )
    failed = [row for row in snapshot.validation_runs if _validation_failed(row)]
    _render_card_grid(
        "Failed Items",
        _cards_from_records(failed, label="Validation", title_key="validation_type", status_key="verdict"),
        "No failed validation items.",
    )


def _render_dashboard() -> None:
    _install_operating_center_css()
    st.sidebar.markdown("### VENHO AI Studio")
    st.sidebar.caption("Operating Center")
    section = st.sidebar.radio(
        "Navigation",
        ["Home", "Projects", "Workbench", "Agents", "Publishing", "Insights", "System"],
        key="m10_section",
    )
    project = st.sidebar.text_input("Project", value="venho_hotel", key="m10_project")
    snapshot = build_dashboard_snapshot(BASE_DIR, project=project)
    oc = snapshot.operating_center

    _render_operating_header(snapshot)
    if section == "Home":
        _render_current_focus(oc["current_focus"])
        _render_summary_cards(oc["summary_cards"])
        left, right = st.columns([2, 1])
        with left:
            _render_today(oc["today_tasks"], oc["today_progress"])
        with right:
            _render_quick_actions(oc["quick_actions"])
        _render_pipeline(oc["pipeline"])
        left, right = st.columns([2, 1])
        with left:
            _render_alerts(oc["alerts"])
        with right:
            _render_health(oc["system_health"])
        _render_recent_activity(oc["recent_activity"])
        st.markdown(
            """
            <div class="oc-bottom-nav">
                <div class="oc-bottom-item">Home</div>
                <div class="oc-bottom-item">Projects</div>
                <div class="oc-bottom-item">Workbench</div>
                <div class="oc-bottom-item">Publish</div>
                <div class="oc-bottom-item">System</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    elif section == "Projects":
        _render_page_header("Projects", "Project cards show operating state, attention areas, and the next place to work.")
        health_attention = [item for item in oc["system_health"] if _status_tone(str(item["status"])) != "success"]
        project_status = "Warning" if health_attention else "Active"
        project_cards = [
            {
                "label": "Active Project",
                "title": snapshot.project.display_name,
                "meta": (
                    f"Prompt name: {snapshot.project.prompt_name} · "
                    f"{len(snapshot.subjects)} DNA subjects · "
                    f"{len(health_attention)} attention area(s)"
                ),
                "status": project_status,
                "action": "Open Workbench" if health_attention else "Open",
            }
        ]
        _render_card_grid("Project Cards", project_cards, "No project configured.")
        knowledge_cards = [
            {
                "label": "Knowledge",
                "title": asset.subject,
                "meta": (
                    f"Config: {'yes' if asset.has_config else 'no'} · "
                    f"DNA JSON: {'yes' if asset.has_dna_json else 'no'} · "
                    f"Compact: {'yes' if asset.has_compact else 'no'}"
                ),
                "status": "Ready" if asset.has_dna_json else "Need Review",
                "action": "Browse" if asset.has_dna_json else "Build DNA",
            }
            for asset in snapshot.subjects
        ]
        _render_card_grid("Knowledge Assets", knowledge_cards, "No knowledge assets available yet.")
        _render_health(oc["system_health"])

    elif section == "Workbench":
        _render_workbench(snapshot)

    elif section == "Agents":
        _render_page_header("Agents", "Persona cards show who can plan work and what should happen next.")
        agent_cards = [
            {
                "label": "Agent",
                "title": row.get("agent") or row.get("display_name") or "Agent",
                "meta": f"{row.get('display_name', '')} · Modules: {', '.join(str(item) for item in row.get('allowed_modules', []))}",
                "status": row.get("status", "Ready"),
                "action": "Open",
            }
            for row in snapshot.agent_personas
        ]
        _render_card_grid("Agent Cards", agent_cards, "No agent persona configured.")
        _render_card_grid(
            "Recent Automation",
            _cards_from_records(snapshot.automation_jobs, label="Automation", title_key="run_id"),
            "No automation run has been recorded yet.",
        )

    elif section == "Publishing":
        _render_page_header("Publishing", "Review approved packages, waiting approvals, scheduled work, receipts, and failures.")
        statuses = {
            "Ready": {"ready", "pending", "waiting_approval", "draft", "available"},
            "Waiting Approval": {"waiting_approval", "pending", "draft"},
            "Scheduled": {"scheduled"},
            "Published": {"published", "success", "completed"},
            "Failed": {"failed", "error"},
        }
        for label, allowed in statuses.items():
            rows = [item for item in snapshot.publishing_items if str(item.get("status", "")).lower() in allowed]
            _render_card_grid(
                label,
                _cards_from_records(rows, label="Publishing", title_key="id"),
                f"No {label.lower()} publishing items.",
            )

    elif section == "Insights":
        _render_page_header("Insights", "Analytics stays advisory-only: review snapshots and recommendations before approval.")
        if snapshot.analytics_items:
            _render_card_grid(
                "Overview",
                _cards_from_records(snapshot.analytics_items, label="Analytics", title_key="id"),
                "No analytics snapshot available.",
            )
            recommendations = [
                {
                    "label": "Recommendation",
                    "title": "Review advisory before applying changes",
                    "meta": "M08 advisories remain pending approval and must route through M04/M09.",
                    "status": "Need Review",
                    "action": "Review",
                }
            ]
            _render_card_grid("Recommendations", recommendations, "No recommendations available.")
        else:
            _render_empty_card(
                "No Analytics Snapshot",
                "No analytics snapshot available. Publish receipts from M07 will feed M08 when ready.",
                "Review Pipeline",
            )

    else:
        system_tabs = st.tabs(["Developer", "Artifacts", "JSON Viewer", "Module Status", "Logs", "Settings"])
        with system_tabs[0]:
            st.json(snapshot.system)
        with system_tabs[1]:
            st.dataframe(
                {
                    "area": ["Prompts", "Content", "Validation", "Automation", "Video", "Publishing", "Analytics"],
                    "items": [
                        len(snapshot.prompts),
                        len(snapshot.content_items),
                        len(snapshot.validation_runs),
                        len(snapshot.automation_jobs),
                        len(snapshot.video_items),
                        len(snapshot.publishing_items),
                        len(snapshot.analytics_items),
                    ],
                },
                use_container_width=True,
                hide_index=True,
            )
        with system_tabs[2]:
            st.subheader("JSON Viewer")
            st.json(
                {
                    "system": snapshot.system,
                    "operating_center": snapshot.operating_center,
                    "advisories": [advisory.__dict__ for advisory in snapshot.advisories],
                }
            )
        with system_tabs[3]:
            st.dataframe(oc["system_health"], use_container_width=True, hide_index=True)
        with system_tabs[4]:
            _render_recent_activity(oc["recent_activity"])
        with system_tabs[5]:
            st.write(
                {
                    "project": snapshot.project.project,
                    "ui_display": snapshot.project.display_name,
                    "prompt_display": snapshot.project.prompt_name,
                    "config_sections": snapshot.project.config_sections,
                }
            )


st.set_page_config(page_title="VENHO AI Studio", page_icon="🧬", layout="wide")

mode = st.sidebar.radio(
    "Chọn màn hình",
    [
        "M10 Operating Center",
        "Mode A — Observe (bất kỳ ảnh nào)",
        "Mode B — Build DNA (nhiều ảnh cùng 1 subject)",
    ],
)

if mode.startswith("M10 Operating"):
    _render_dashboard()

elif mode.startswith("Mode A"):
    st.title("VENHO AI Studio")
    st.caption("Studio Shell")
    st.header("Mode A — Observe")
    st.caption("Mỗi ảnh → 1 file quan sát .md + .json. Không tạo DNA.")

    input_dir = st.text_input("Folder ảnh input", value="data/projects/_inbox/media")
    output_dir = st.text_input("Folder output (để trống = mặc định trong settings.yaml)", value="")
    provider = st.selectbox("Provider (để trống = dùng config mặc định)", ["", "openai", "claude", "mock"])

    if st.button("▶ Chạy Mode A", type="primary"):
        if not input_dir.strip():
            st.error("Cần nhập folder ảnh input.")
        else:
            input_path = Path(input_dir)
            if not input_path.is_absolute():
                input_path = BASE_DIR / input_path
            if not input_path.is_dir():
                st.error(f"Không tìm thấy folder: {input_path}")
            else:
                kwargs = {
                    "input_dir": input_path,
                    "output_dir": (Path(output_dir) if output_dir.strip() else None),
                    "provider": (provider or None),
                }
                result, error, _ = _run_with_live_log(run_mode_a, kwargs)
                if error:
                    st.error(f"Lỗi: {error}")
                elif result:
                    st.success(f"Xong! {len(result)} ảnh đã xử lý.")
                    for i, paths in enumerate(result):
                        with st.expander(f"Ảnh {i + 1}: {Path(paths['md']).stem}"):
                            _show_output_paths(paths)

else:
    st.title("VENHO AI Studio")
    st.caption("Studio Shell")
    st.header("Mode B — Build DNA")
    st.caption("Nhiều ảnh cùng 1 subject → DNA .md + .json. §2.1: 1 folder = 1 tier/subject.")

    project = st.text_input("Project", value="venho_hotel")
    known_subjects = _list_subjects(project)
    subject = st.selectbox(
        "Subject",
        options=known_subjects or ["(chưa có schema — điền tay bên dưới)"],
        index=0,
    )
    subject_manual = st.text_input("Hoặc nhập subject khác", value="")
    resolved_subject = subject_manual.strip() or subject

    media_subfolders = _list_media_subfolders(project)
    default_input = (
        f"data/projects/{project}/media/{resolved_subject}"
        if resolved_subject in media_subfolders
        else ""
    )
    input_dir = st.text_input("Folder ảnh input", value=default_input)
    dna_version = st.text_input("DNA version", value="1.0")
    provider = st.selectbox("Provider (để trống = dùng config mặc định)", ["", "openai", "claude", "mock"])

    st.warning(
        "⚠ Xác nhận (v2.4 §2.1): TẤT CẢ ảnh trong folder trên phải thuộc ĐÚNG 1 "
        "tier/subject (vd: toàn bộ ảnh lake-view room, không lẫn loại phòng khác)."
    )
    confirmed_one_subject = st.checkbox("Folder này chỉ chứa 1 tier/subject duy nhất", value=False)

    if st.button("▶ Chạy Mode B", type="primary"):
        if not resolved_subject or resolved_subject.startswith("("):
            st.error("Cần chọn hoặc nhập subject.")
        elif not confirmed_one_subject:
            st.error("Phải xác nhận folder chỉ chứa 1 tier/subject trước khi chạy (v2.4 §2.1).")
        elif not input_dir.strip():
            st.error("Cần nhập folder ảnh input.")
        else:
            input_path = Path(input_dir)
            if not input_path.is_absolute():
                input_path = BASE_DIR / input_path
            if not input_path.is_dir() or not any(input_path.iterdir()):
                st.error(f"Folder rỗng hoặc không tồn tại: {input_path}")
            else:
                kwargs = {
                    "project": project,
                    "subject": resolved_subject,
                    "input_dir": input_path,
                    "dna_version": dna_version,
                    "provider": (provider or None),
                }
                result, error, _ = _run_with_live_log(run_mode_b, kwargs)
                if error:
                    st.error(f"Lỗi: {error}")
                elif result:
                    st.success("Xong!")
                    _show_output_paths(result)
