"""VENHO AI Studio — Studio Shell + Module 10 Dashboard.

Thin UI over the existing CLI pipeline (Mode A / Mode B). This file must not
contain business logic. The M10 dashboard only reads normalized presentation
snapshots from `dashboard.gateway`.

Run:
    streamlit run ui/studio_app.py
"""

from __future__ import annotations

import contextlib
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
        .block-container { padding-top: 2rem; }
        [data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 16px 18px;
        }
        [data-testid="stMetricLabel"] { color: #64748b; }
        .oc-eyebrow {
            color: #64748b;
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0;
            text-transform: uppercase;
        }
        .oc-header {
            border-bottom: 1px solid #e5e7eb;
            margin-bottom: 0.85rem;
            padding-bottom: 0.85rem;
        }
        .oc-focus {
            background: #f8fafc;
            border: 1px solid #dbe3ec;
            border-radius: 8px;
            padding: 18px;
        }
        .oc-status {
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 12px 14px;
            min-height: 78px;
            background: #fff;
        }
        .oc-pill {
            border-radius: 999px;
            display: inline-block;
            font-size: 0.78rem;
            font-weight: 700;
            padding: 4px 9px;
        }
        .oc-Healthy, .oc-Ready, .oc-APPROVED { background: #dcfce7; color: #166534; }
        .oc-Warning, .oc-Need-Review, .oc-CONDITIONAL { background: #fef3c7; color: #92400e; }
        .oc-Critical, .oc-Failed, .oc-REJECT { background: #fee2e2; color: #991b1b; }
        .oc-Critical-Failure, .oc-Needs-Attention { background: #fee2e2; color: #991b1b; }
        .oc-Missing { background: #f1f5f9; color: #475569; }
        .oc-Active { background: #dbeafe; color: #1d4ed8; }
        .oc-In-Progress { background: #dbeafe; color: #1d4ed8; }
        .oc-card-title { color: #0f172a; font-size: 1.02rem; font-weight: 750; margin-bottom: 4px; }
        .oc-muted { color: #64748b; font-size: 0.9rem; }
        .oc-task {
            align-items: center;
            border-bottom: 1px solid #f1f5f9;
            display: flex;
            gap: 10px;
            padding: 10px 0;
        }
        .oc-box {
            border: 1px solid #d1d5db;
            border-radius: 4px;
            height: 16px;
            width: 16px;
        }
        .oc-node {
            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            min-height: 148px;
            padding: 14px;
        }
        .oc-node-title {
            color: #0f172a;
            font-size: 0.95rem;
            font-weight: 750;
            margin-bottom: 8px;
        }
        .oc-node-meta {
            color: #64748b;
            font-size: 0.82rem;
            line-height: 1.45;
            margin-top: 8px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _status_class(status: str) -> str:
    return status.replace(" ", "-")


def _status_pill(status: str) -> str:
    return f'<span class="oc-pill oc-{_status_class(status)}">{status}</span>'


def _render_operating_header(snapshot) -> None:
    header = snapshot.operating_center.get("header", {})
    st.markdown(
        f"""
        <div class="oc-header">
            <div class="oc-eyebrow">{header.get('title', 'VENHO AI STUDIO')} ({header.get('subtitle', 'Operating Center')})</div>
            <h1 style="margin: 0.2rem 0 0.45rem;">Operating Center</h1>
            <div class="oc-muted">
                Project <strong>{header.get('project_scope', snapshot.project.display_name)}</strong>
                &nbsp;&nbsp; Status <strong>{header.get('project_status', 'ACTIVE')}</strong>
                &nbsp;&nbsp; Last Sync <strong>{header.get('last_sync', 'Recent')}</strong>
                &nbsp;&nbsp; Mode <strong>{header.get('mode', 'Read-only')}</strong>
                &nbsp;&nbsp; Build <strong>{header.get('build', 'v2.0')}</strong>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_summary_cards(cards: list[dict]) -> None:
    columns = st.columns(4)
    for column, card in zip(columns, cards):
        column.metric(card["label"], card["value"], card.get("status"))


def _render_current_focus(focus: dict) -> None:
    st.subheader("Current Focus")
    left, right = st.columns([4, 1])
    with left:
        detail = focus.get("progress_label") or "No active workflow selected"
        st.markdown(
            f"""
            <div class="oc-focus">
                <div class="oc-card-title">{focus.get('title', 'No active focus.')}</div>
                <div class="oc-muted">Progress: {detail} · Status: {_status_pill(str(focus.get('status', 'Ready')))}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        st.button(str(focus.get("action_label", "Continue")), use_container_width=True, disabled=True)


def _render_today(tasks: list[dict], progress: dict) -> None:
    completed = progress.get("completed", 0)
    total = progress.get("total", len(tasks))
    st.subheader(f"Today Task Center: {completed} / {total} Tasks Completed")
    groups = ["High", "Medium", "Low", "Completed"]
    for group in groups:
        rows = [task for task in tasks if task.get("priority") == group or task.get("status") == group]
        if not rows:
            continue
        st.caption(f"{group} Priority" if group != "Completed" else "Completed")
        for task in rows:
            text_col, button_col = st.columns([4, 1])
            with text_col:
                marker = "■" if group in {"High", "Medium", "Low"} else "✓"
                st.markdown(
                    f"""
                    <div class="oc-task">
                        <div class="oc-muted">{marker}</div>
                        <div>
                            <div class="oc-card-title">{task['task']}</div>
                            <div class="oc-muted">{task['source']} · {task.get('status', 'Pending')}</div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with button_col:
                st.button(task.get("action_label", "Open"), key=f"task_{task['task']}", use_container_width=True, disabled=True)


def _render_quick_actions(actions: list[dict]) -> None:
    st.subheader("Quick Actions")
    columns = st.columns(6)
    for index, action in enumerate(actions):
        columns[index % 6].button(action["label"], key=f"quick_{action['label']}", use_container_width=True, disabled=True)


def _render_health(health: list[dict]) -> None:
    st.subheader("System Health")
    for item in health:
        left, right = st.columns([2, 1])
        left.write(item["area"])
        right.markdown(_status_pill(item["status"]), unsafe_allow_html=True)


def _render_pipeline(pipeline: list[dict]) -> None:
    st.subheader("Pipeline Flow")
    first_row = st.columns(4)
    second_row = st.columns(4)
    for index, row in enumerate(pipeline):
        column = first_row[index] if index < 4 else second_row[index - 4]
        with column:
            st.markdown(
                f"""
                <div class="oc-node">
                    <div class="oc-node-title">{row['stage']}</div>
                    {_status_pill(str(row['status']))}
                    <div class="oc-node-meta">
                        Ready: {row['ready']}<br>
                        Need Review: {row['need_review']}<br>
                        Failed: {row['failed']}<br>
                        Action: <strong>{row['action']}</strong>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def _render_alerts(alerts: list[dict]) -> None:
    st.subheader("Alerts")
    if not alerts:
        st.success("All systems healthy.")
        return
    for alert in alerts:
        if alert["status"] == "Critical":
            st.error(alert["message"])
        else:
            st.warning(alert["message"])


def _render_recent_activity(activity: list[dict]) -> None:
    st.subheader("Recent Activity")
    if not activity:
        st.info("No recent activity yet.")
        return
    for item in activity:
        st.markdown(f"**{item['time']}** — {item['event']}")
        if item.get("detail"):
            st.caption(item["detail"])


def _render_workbench(snapshot) -> None:
    st.subheader("Quick Actions")
    actions = ["Build DNA", "Generate Prompt", "Validate Output", "Prepare Publishing", "Create Video", "Run Automation"]
    columns = st.columns(3)
    for index, action in enumerate(actions):
        columns[index % 3].button(action, use_container_width=True, disabled=True)

    left, right = st.columns(2)
    with left:
        st.subheader("Pending Reviews")
        rows = [row for row in snapshot.operating_center["pipeline"] if row["need_review"] or row["failed"]]
        st.dataframe(rows, use_container_width=True, hide_index=True)
    with right:
        st.subheader("Draft Outputs")
        st.dataframe(snapshot.content_items, use_container_width=True, hide_index=True)

    left, right = st.columns(2)
    with left:
        st.subheader("Ready To Publish")
        st.dataframe(snapshot.publishing_items, use_container_width=True, hide_index=True)
    with right:
        st.subheader("Failed Items")
        failed = [row for row in snapshot.validation_runs if str(row.get("verdict") or row.get("status") or "").lower() in {"fail", "failed", "reject", "rejected", "regenerate"}]
        st.dataframe(failed, use_container_width=True, hide_index=True)


def _render_dashboard() -> None:
    _install_operating_center_css()
    project = st.sidebar.text_input("Project", value="venho_hotel", key="m10_project")
    snapshot = build_dashboard_snapshot(BASE_DIR, project=project)
    oc = snapshot.operating_center

    _render_operating_header(snapshot)
    tab_names = ["Home", "Projects", "Workbench", "Agents", "Publish", "Insights", "System"]
    tabs = st.tabs(tab_names)

    with tabs[0]:
        _render_current_focus(oc["current_focus"])
        _render_summary_cards(oc["summary_cards"])
        _render_today(oc["today_tasks"], oc["today_progress"])
        _render_quick_actions(oc["quick_actions"])
        _render_pipeline(oc["pipeline"])
        left, right = st.columns([1, 1])
        with left:
            _render_alerts(oc["alerts"])
        with right:
            _render_health(oc["system_health"])
        _render_recent_activity(oc["recent_activity"])

    with tabs[1]:
        st.subheader("Projects")
        with st.container():
            st.markdown(f"### {snapshot.project.display_name}")
            st.caption(f"Prompt name: {snapshot.project.prompt_name}")
            st.write("Active project")
        project_tabs = st.tabs(["Overview", "Knowledge", "Content", "Validation", "Automation", "Publishing", "Analytics", "Files"])
        with project_tabs[0]:
            st.dataframe(oc["system_health"], use_container_width=True, hide_index=True)
        with project_tabs[1]:
            st.dataframe([asset.__dict__ for asset in snapshot.subjects], use_container_width=True, hide_index=True)
        with project_tabs[2]:
            st.dataframe(snapshot.content_items, use_container_width=True, hide_index=True)
        with project_tabs[3]:
            st.dataframe(snapshot.validation_runs, use_container_width=True, hide_index=True)
        with project_tabs[4]:
            st.dataframe(snapshot.automation_jobs, use_container_width=True, hide_index=True)
        with project_tabs[5]:
            st.dataframe(snapshot.publishing_items, use_container_width=True, hide_index=True)
        with project_tabs[6]:
            st.dataframe(snapshot.analytics_items, use_container_width=True, hide_index=True)
        with project_tabs[7]:
            st.dataframe(
                [{"section": section} for section in snapshot.project.config_sections],
                use_container_width=True,
                hide_index=True,
            )

    with tabs[2]:
        _render_workbench(snapshot)

    with tabs[3]:
        st.subheader("Agents")
        st.dataframe(oc["agents"], use_container_width=True, hide_index=True)
        st.subheader("Recent Automation")
        st.dataframe(snapshot.automation_jobs, use_container_width=True, hide_index=True)

    with tabs[4]:
        st.subheader("Publishing")
        publishing_tabs = st.tabs(["Ready", "Scheduled", "Published", "Failed"])
        statuses = {
            "Ready": {"ready", "pending", "waiting_approval", "draft", "available"},
            "Scheduled": {"scheduled"},
            "Published": {"published", "success", "completed"},
            "Failed": {"failed", "error"},
        }
        for tab, label in zip(publishing_tabs, statuses):
            with tab:
                allowed = statuses[label]
                rows = [item for item in snapshot.publishing_items if str(item.get("status", "")).lower() in allowed]
                st.dataframe(rows, use_container_width=True, hide_index=True)

    with tabs[5]:
        st.subheader("Insights")
        if snapshot.analytics_items:
            st.dataframe(snapshot.analytics_items, use_container_width=True, hide_index=True)
        else:
            st.info("No analytics snapshot available.")

    with tabs[6]:
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
st.title("VENHO AI Studio")
st.caption("Studio Shell + M10 Operating Center")

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
