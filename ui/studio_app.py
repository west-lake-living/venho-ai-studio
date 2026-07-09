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


def _render_dashboard() -> None:
    project = st.sidebar.text_input("Project", value="venho_hotel", key="m10_project")
    snapshot = build_dashboard_snapshot(BASE_DIR, project=project)

    st.header("M10 Dashboard — Unified Presentation Layer")
    st.caption("Read-only UI layer over M01-M09 artifacts. No live API calls, no duplicated business logic.")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Project", snapshot.project.display_name)
    c2.metric("DNA Subjects", snapshot.system["counts"]["subjects"])
    c3.metric("Automation Jobs", snapshot.system["counts"]["automation_jobs"])
    c4.metric("Validation Runs", snapshot.system["counts"]["validation_runs"])

    if snapshot.advisories:
        for advisory in snapshot.advisories:
            st.warning(f"{advisory.module} · {advisory.status}: {advisory.message}")

    tab_names = [
        "Home",
        "Projects",
        "Knowledge",
        "Prompt & Content",
        "Validator",
        "Automation & Agent",
        "Video",
        "Publishing & Analytics",
        "System",
    ]
    tabs = st.tabs(tab_names)

    with tabs[0]:
        st.subheader("System Overview")
        st.json(snapshot.system)
        st.subheader("Recent Automation Queue")
        st.dataframe(snapshot.automation_jobs, use_container_width=True)

    with tabs[1]:
        st.subheader("Project Manager")
        st.write(
            {
                "project": snapshot.project.project,
                "ui_display": snapshot.project.display_name,
                "prompt_display": snapshot.project.prompt_name,
                "config_sections": snapshot.project.config_sections,
            }
        )
        st.caption('UI display keeps "Ven Hồ Hotel"; prompt display keeps "Ven Ho Hotel".')

    with tabs[2]:
        st.subheader("Knowledge Studio Browser")
        st.dataframe([asset.__dict__ for asset in snapshot.subjects], use_container_width=True)

    with tabs[3]:
        st.subheader("Prompt Library")
        st.dataframe(snapshot.prompts, use_container_width=True)
        st.subheader("Content Drafts")
        st.dataframe(snapshot.content_items, use_container_width=True)

    with tabs[4]:
        st.subheader("Validation Reports")
        st.dataframe(snapshot.validation_runs, use_container_width=True)

    with tabs[5]:
        st.subheader("Agent Personas")
        st.dataframe(snapshot.agent_personas, use_container_width=True)
        st.subheader("Automation Jobs")
        st.dataframe(snapshot.automation_jobs, use_container_width=True)
        st.info("Manual Gate approval remains routed through M09/M04 contracts; the dashboard does not build ModuleRequest packages.")

    with tabs[6]:
        st.subheader("Video Storyboard Packages")
        st.dataframe(snapshot.video_items, use_container_width=True)
        st.info("M06 packages are pre-render only. This view does not render, upload, or publish video.")

    with tabs[7]:
        st.subheader("Publishing Gateway")
        st.dataframe(snapshot.publishing_items, use_container_width=True)
        st.subheader("Analytics & Feedback")
        st.dataframe(snapshot.analytics_items, use_container_width=True)
        st.info("M08 advisories remain pending approval and are not applied automatically.")

    with tabs[8]:
        st.subheader("System Monitor")
        st.json(snapshot.system)


st.set_page_config(page_title="VENHO AI Studio", page_icon="🧬", layout="wide")
st.title("🧬 VENHO AI Studio")
st.caption("Studio Shell + M10 Dashboard — local-first, presentation-only")

mode = st.sidebar.radio(
    "Chọn màn hình",
    [
        "M10 Dashboard — Unified Control Center",
        "Mode A — Observe (bất kỳ ảnh nào)",
        "Mode B — Build DNA (nhiều ảnh cùng 1 subject)",
    ],
)

if mode.startswith("M10 Dashboard"):
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
