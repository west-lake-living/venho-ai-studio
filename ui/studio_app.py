"""VENHO AI Studio — Studio Shell + Module 10 Dashboard.

Thin UI over the existing CLI pipeline (Mode A / Mode B). This file must not
contain business logic. The M10 dashboard only reads normalized presentation
snapshots from `dashboard.gateway`.

Run:
    streamlit run ui/studio_app.py
"""

from __future__ import annotations

import contextlib
import datetime
import html
import io
import json
import re
import subprocess
import sys
import threading
import time
import unicodedata
from pathlib import Path

import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# --- Creative Studio paths ---
VENHO_HOTEL_DIR = BASE_DIR.parent.parent / "Ven Ho Hotel"
SOCIAL_MANAGER_DIR = VENHO_HOTEL_DIR / "ops" / "VenHoSocialManager"
VIDEO_SCRIPTS_DIR = VENHO_HOTEL_DIR / "local-generated" / "social-video" / "scripts"

# --- Linh An Face Lock v3.1 ---
_LINH_AN_FACE_LOCK = (
    "Linh An, Vietnamese female influencer, 24 years old,\n"
    "soft elongated oval face, slightly fuller cheeks, balanced facial proportions,\n"
    "slim natural nose bridge, long almond eyes, horizontal eye emphasis,\n"
    "slightly narrow eye opening, thin upper eyelid, warm brown irises,\n"
    "very subtle outer corner lift, natural eye asymmetry,\n"
    "low-position eyebrows, minimal arch, close eye-brow distance,\n"
    "natural full lips with slightly thinner upper lip and slightly fuller lower lip,\n"
    "very subtle upward lip corners, slightly shorter philtrum,\n"
    "soft feminine jawline, delicate chin,\n"
    "fair warm ivory skin, healthy natural glow, realistic skin texture, natural pores,\n"
    "long dark chocolate brown layered wavy hair, natural center part,\n"
    "small pearl drop earrings,\n"
    "gentle feminine beauty, elegant Vietnamese appearance,\n"
    "luxury lifestyle creator, consistent facial identity,\n"
    "photorealistic, natural beauty,\n"
    "no plastic skin, no doll face, no exaggerated makeup.\n"
    "168cm height, slim elegant body, defined waistline,\n"
    "long legs, natural feminine curves, healthy feminine silhouette,\n"
    "graceful posture, confident but relaxed body language.\n"
    "10-20 degree soft hero left angle, natural eye contact,\n"
    "Living Expression — subtle anticipation smile, genuine engagement."
)

_OUTFITS: dict[str, str] = {
    "A — Cafe Girl": "cream knit top, beige A-line skirt, small luxury handbag",
    "B — West Lake Sunset": "flowing white dress, minimal gold jewelry",
    "C — Street Style": "white button-up shirt, high-waist trousers, denim jacket",
    "D — Business Travel": "light beige blazer, white blouse, elegant trousers",
    "E — Sport & Active": "light pastel-green fitted sports top, slim-fit black cycling leggings, white sneakers",
}

_ENV_BLOCKS: dict[str, str] = {
    "Nguyễn Đình Thi (Street Level)": (
        "Authentic Nguyễn Đình Thi Street beside West Lake Hanoi, current 2026 lakeside environment,\n"
        "ivory-white metal railing with rounded top handrail, multiple horizontal bars,\n"
        "angled triangular support frames, simple modern functional railing, no stone pillars, no green railing,\n"
        "narrow local lakeside sidewalk with gray paving, mature trees growing close to the railing,\n"
        "natural leafy branches extending over the path, strong tree shadows on the pavement,\n"
        "light motorbike and bicycle traffic on the two-lane road,\n"
        "wide calm West Lake water immediately beside the railing,\n"
        "distant low and mid-rise Hanoi skyline across the lake,\n"
        "large open sky with soft clouds, authentic local West Lake residential atmosphere,\n"
        "not touristy, not resort-like."
    ),
    "Rooftop Ven Hồ Hotel": (
        "Ven Hồ Hotel rooftop terrace overlooking West Lake Hanoi,\n"
        "open rooftop with terracotta floor tiles,\n"
        "black metal rooftop railing with simple circular details on top bar,\n"
        "panoramic view of calm West Lake, distant Hanoi skyline,\n"
        "huge sky with soft clouds, light local atmosphere."
    ),
    "Hotel Room (Lake View)": (
        "Ven Hồ Hotel authentic lake view room, Hanoi mini hotel interior,\n"
        "long narrow room layout, white walls, white ceiling with simple crown molding,\n"
        "warm recessed LED ceiling lights,\n"
        "dark reddish-brown mahogany wood furniture: queen bed with dark wood frame and headboard, white bedding,\n"
        "light wood laminate flooring,\n"
        "large black aluminum cross-mullion window (2x2 pane grid, not floor-to-ceiling height),\n"
        "dark gray-brown thick curtains pulled open to both sides,\n"
        "black ornate wrought-iron decorative railing outside window with scroll and floral pattern,\n"
        "two wooden armchairs with cushions and small glass-top wooden table in front of window,\n"
        "West Lake water and mature green trees visible through window beyond the railing,\n"
        "authentic functional Hanoi mini hotel atmosphere, not luxury, not resort, not boutique designer."
    ),
    "West Lake Café": (
        "Cozy West Lake Hanoi café, large windows facing the lake,\n"
        "warm natural light, authentic Vietnamese café atmosphere,\n"
        "West Lake visible outside, calm morning mood."
    ),
    "West Lake Landscape (Wide)": (
        "Panoramic West Lake Hanoi view from elevated position,\n"
        "calm jade-teal water surface #4E8FA0 extending to horizon,\n"
        "low and mid-rise Hanoi skyline in distance, slightly hazy,\n"
        "mature green tree belt along the shore, huge open sky 40–55% frame,\n"
        "authentic Hanoi atmosphere, not Singapore, not Seoul, not Shanghai."
    ),
}

_TECH_BLOCK = (
    "Fujifilm GFX100S, 85mm lens, shallow depth of field, photorealistic 8K,\n"
    "natural skin texture, editorial luxury lifestyle photography, authentic Vietnamese atmosphere."
)

_NEGATIVE_BLOCK = (
    "Do not make the subject look Korean, Japanese, Chinese, European, or generic fashion model. "
    "Avoid anime style, cartoon style, plastic skin, beauty filter, K-pop styling, "
    "futuristic architecture, Singapore skyline, Seoul skyline, Tokyo skyline, Shanghai skyline, "
    "luxury skyscraper wall, distorted hands, extra fingers, "
    "floor-to-ceiling glass wall hotel, marble luxury interior, modern minimalist designer room, "
    "beige boutique aesthetic, cream and white luxury room, generic AI hotel room, "
    "artificial lighting, over-sharpening, excessive HDR, AI artifacts, "
    "duplicate objects, floating objects, unrealistic reflections, "
    "green railing, pink stone pillars, old Hồ Tây railing style, "
    "resort luxury pool, marina lifestyle, tropical ocean scene, tourist crowd."
)

_SCENARIO_SUBJECT: dict[str, str | None] = {
    "Nguyễn Đình Thi (Street Level)": "westlake",
    "Rooftop Ven Hồ Hotel": "outside",
    "Hotel Room (Lake View)": "lake_view_room",
    "West Lake Café": None,
    "West Lake Landscape (Wide)": "westlake",
}

_PILLARS: dict[str, dict[str, str]] = {
    "P1 — Khám Phá Hồ Tây (40%)": {
        "funnel": "TOFU",
        "golden_rule": "Inspire",
        "persona": "Persona 1 — Khách du lịch Việt (25–45)",
        "hashtags": "#VenHoHotel #HoTay #TayHo #HanoiSunset #BinhMinhHaNoi",
    },
    "P2 — Ẩm Thực Hồ Tây (20%)": {
        "funnel": "TOFU",
        "golden_rule": "Educate",
        "persona": "Persona 1 — Khách du lịch Việt (25–45)",
        "hashtags": "#VenHoHotel #HoTay #HanoiFood #HanoiCafe #AmThucHaNoi",
    },
    "P3 — Kinh Nghiệm Công Tác (15%)": {
        "funnel": "MOFU",
        "golden_rule": "Educate",
        "persona": "Persona 2 — Khách công tác (28–55)",
        "hashtags": "#VenHoHotel #HoTay #BusinessTravel #CongTacHaNoi #WorkFromHanoi",
    },
    "P4 — Trải Nghiệm Khách Hàng (15%)": {
        "funnel": "MOFU",
        "golden_rule": "Trust",
        "persona": "Persona 1 — Khách du lịch Việt (25–45)",
        "hashtags": "#VenHoHotel #HoTay #GuestLove #ReviewThat #AgodaReview #CheckinHanoi",
    },
    "P5 — Thương Hiệu Ven Hồ Hotel (10%)": {
        "funnel": "BOFU",
        "golden_rule": "Inspire",
        "persona": "Persona 1 — Khách du lịch Việt (25–45)",
        "hashtags": "#VenHoHotel #HoTay #KhachSanHoTay #BoutiqueHotel #HanoiHotel",
    },
}

_VIDEO_PILLARS = ["View & Vibe", "Room Tour", "Local Life", "Deal", "Guest Story"]

# Each scene: (desc_vi, seedance_action, env_scenario_key, camera_move, lighting)
_SCENE_STRUCTURES: dict[str, list[tuple[str, str, str, str, str]]] = {
    "View & Vibe": [
        ("Cảnh Hồ Tây rộng từ rooftop", "standing at the rooftop railing, arms resting lightly, looking towards the calm West Lake", "Rooftop Ven Hồ Hotel", "slow pan right", "golden hour, warm honey light, soft lake haze"),
        ("Khoảnh khắc thư giãn tại phòng", "sitting in the armchair by the window, holding a small cup of tea, gazing at the lake outside", "Hotel Room (Lake View)", "slow push in", "soft afternoon light through window, warm and serene"),
        ("Cinematic close-up hoàng hôn", "gentle turn toward camera with a soft warm smile, golden light on face, West Lake bokeh behind", "Rooftop Ven Hồ Hotel", "gentle zoom in", "cinematic backlight, golden hour glow, dreamy"),
    ],
    "Room Tour": [
        ("Exterior khách sạn — Nguyễn Đình Thi", "walking toward the hotel entrance along the lakeside sidewalk, relaxed confident stride", "Nguyễn Đình Thi (Street Level)", "tracking shot", "bright morning light, fresh local atmosphere"),
        ("Khám phá trong phòng", "opening the dark grey curtains slowly to reveal the lake view, turning to look at the room interior", "Hotel Room (Lake View)", "slow pull back", "natural light flooding in, warm and inviting"),
        ("Reveal view Hồ Tây qua cửa sổ", "standing at the window, both hands on the iron railing outside, West Lake filling the frame beyond", "Hotel Room (Lake View)", "static then push in", "soft afternoon light, calm and elegant"),
    ],
    "Local Life": [
        ("Bắt đầu từ khách sạn — buổi sáng", "stepping out of the hotel entrance onto Nguyễn Đình Thi street, looking left toward the lake with a smile", "Nguyễn Đình Thi (Street Level)", "tracking shot", "early morning golden light, fresh authentic atmosphere"),
        ("Dạo bộ ven hồ Nguyễn Đình Thi", "walking slowly along the ivory railing beside West Lake, one hand trailing the railing, looking at the water", "Nguyễn Đình Thi (Street Level)", "tracking side", "midday soft light, green tree shadows, local calm"),
        ("Quay về nghỉ ngơi — chiều tối", "sitting in the hotel room armchair, feet curled up, looking out the window at the fading lake light, peaceful", "Hotel Room (Lake View)", "slow push in", "warm evening ambient light, cozy and relaxing"),
    ],
    "Deal": [
        ("Hook — đứng trước khách sạn tự tin", "standing confidently in front of the hotel facade, slight warm smile directly at camera", "Nguyễn Đình Thi (Street Level)", "slow push in", "clean bright daylight, professional and fresh"),
        ("Phòng đẹp — showcase value", "sitting in the room armchair, gesturing naturally toward the large lake-view window, inviting expression", "Hotel Room (Lake View)", "slow pan", "soft natural light, warm and comfortable"),
        ("CTA — rooftop với toàn cảnh hồ", "standing at the rooftop railing, looking directly at camera with confident warm smile, West Lake panorama behind", "Rooftop Ven Hồ Hotel", "gentle zoom out", "golden hour, cinematic warm light"),
    ],
    "Guest Story": [
        ("Quote / Review — trong phòng", "sitting on the bed edge, looking at phone screen showing a review, soft smile of satisfaction", "Hotel Room (Lake View)", "slow push in", "warm room light, intimate and authentic"),
        ("Cảnh phòng + view Hồ Tây", "standing beside the window with one hand on the dark iron railing, West Lake stretching beyond, reflective mood", "Hotel Room (Lake View)", "static wide", "natural afternoon light, calm and beautiful"),
        ("CTA cảm xúc — rooftop hoàng hôn", "at the rooftop, turning from the lake to face camera with a genuine peaceful smile, warm golden sky behind", "Rooftop Ven Hồ Hotel", "slow push in", "golden hour backlight, emotional and warm"),
    ],
}

_OUTFIT_BY_PILLAR: dict[str, str] = {
    "View & Vibe": "B — West Lake Sunset",
    "Room Tour": "D — Business Travel",
    "Local Life": "A — Cafe Girl",
    "Deal": "B — West Lake Sunset",
    "Guest Story": "A — Cafe Girl",
}

_DAY_NAMES_VI = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ Nhật"]

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


def _resolve_repo_path(path: str) -> Path:
    resolved = Path(path)
    return resolved if resolved.is_absolute() else BASE_DIR / resolved


def _save_uploaded_images(uploaded_files: list, target_dir: Path) -> list[Path]:
    target_dir.mkdir(parents=True, exist_ok=True)
    saved_paths = []
    for uploaded_file in uploaded_files:
        filename = Path(uploaded_file.name).name
        if not filename:
            continue
        destination = target_dir / filename
        destination.write_bytes(uploaded_file.getbuffer())
        saved_paths.append(destination)
    return saved_paths


def _image_input_selector(default_dir: str, key_prefix: str) -> Path | None:
    source = st.radio(
        "Nguồn ảnh input",
        ["Folder có sẵn", "Upload ảnh"],
        horizontal=True,
        key=f"{key_prefix}_source",
    )
    input_dir = st.text_input("Folder ảnh input", value=default_dir, key=f"{key_prefix}_input_dir")
    if not input_dir.strip():
        return None

    input_path = _resolve_repo_path(input_dir)
    if source == "Upload ảnh":
        uploaded_files = st.file_uploader(
            "Upload ảnh",
            type=["jpg", "jpeg", "png", "webp", "heic"],
            accept_multiple_files=True,
            key=f"{key_prefix}_uploader",
        )
        if uploaded_files:
            saved_paths = _save_uploaded_images(uploaded_files, input_path)
            if saved_paths:
                st.success(f"Đã lưu {len(saved_paths)} ảnh vào `{input_path}`.")
    return input_path


def _provider_selector(key: str) -> str | None:
    provider = st.selectbox(
        "Provider",
        ["mock", "openai", "claude", "config mặc định"],
        help="Chọn mock để test offline không cần API key. Chỉ chọn openai/claude khi đã cấu hình credentials.",
        key=key,
    )
    return None if provider == "config mặc định" else provider


def _mode_a_output_path(output_dir: str) -> Path:
    if output_dir.strip():
        return _resolve_repo_path(output_dir)
    return BASE_DIR / "data" / "projects" / "_inbox" / "output"


def _mode_b_output_path(project: str) -> Path:
    return BASE_DIR / "data" / "projects" / project / "knowledge"


def _open_folder(path: Path) -> tuple[bool, str | None]:
    path.mkdir(parents=True, exist_ok=True)
    try:
        if sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=True)
        elif sys.platform.startswith("win"):
            subprocess.run(["cmd", "/c", "start", "", str(path)], check=True)
        else:
            subprocess.run(["xdg-open", str(path)], check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        return False, str(exc)
    return True, None


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


# ============================================================
# Creative Studio helpers
# ============================================================


def _slugify(text: str, max_chars: int = 30) -> str:
    normalized = unicodedata.normalize("NFD", text.lower()).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")
    return (slug or "item")[:max_chars]


def _read_dna_compact(subject: str) -> str:
    subject_upper = subject.upper()
    path = (
        BASE_DIR
        / "data"
        / "projects"
        / "venho_hotel"
        / "knowledge"
        / f"VENHO_HOTEL_{subject_upper}_DNA_COMPACT.md"
    )
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _extract_dna_section(compact: str, section: str) -> str:
    in_section = False
    lines: list[str] = []
    for line in compact.splitlines():
        if line.strip().startswith(f"## {section}"):
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if in_section:
            lines.append(line)
    return "\n".join(lines).strip()


def _assemble_image_prompt(
    scenario: str,
    has_linh_an: bool,
    outfit_key: str,
    action: str,
    dna_compact: str,
) -> str:
    parts: list[str] = []
    if has_linh_an:
        outfit_desc = _OUTFITS.get(outfit_key, "")
        act = action.strip()
        if act:
            subject_prefix = "" if act.lower().startswith("linh an") else "Linh An "
            is_sport = outfit_key.startswith("E — Sport")
            hair_desc = (
                "long dark chocolate brown hair tied back in a sporty ponytail"
                if is_sport else
                "long dark chocolate brown layered wavy hair"
            )
            # Single integrated sentence: character description woven into action
            # No paragraph break — gpt-image-2 treats \n\n as separate entities
            integrated = (
                f"{subject_prefix}{act}, "
                f"she is a Vietnamese female lifestyle influencer, 24 years old, "
                f"fair warm ivory skin, healthy natural glow, realistic skin texture, "
                f"{hair_desc}, small pearl drop earrings, wearing {outfit_desc}, "
                f"slim elegant 168cm figure, she is the MAIN SUBJECT in the foreground, "
                f"full body visible, no conical hat, photorealistic, natural beauty."
            )
            parts.append(integrated)
        else:
            parts.append(f"{_LINH_AN_FACE_LOCK}\nOutfit: {outfit_desc}.")
    env = _ENV_BLOCKS.get(scenario, "")
    if env:
        parts.append(env)
    if dna_compact:
        invariant = _extract_dna_section(dna_compact, "INVARIANT")
        if invariant:
            parts.append(f"[DNA Invariants — {scenario}]\n{invariant}")
    # Action shots need wider lens (35mm) for full body; portrait shots keep 85mm
    has_action = has_linh_an and bool(action.strip())
    if has_action:
        parts.append(
            "Fujifilm GFX100S, 35mm lens, moderate depth of field, photorealistic 8K,\n"
            "natural skin texture, editorial lifestyle photography, authentic Vietnamese atmosphere."
        )
    else:
        parts.append(_TECH_BLOCK)
    action_extra_negative = (
        " No conical hat on main subject, no dark work clothes on main subject,"
        " no anonymous passerby as main subject, no decorative ornate wrought-iron railing."
        if has_action else ""
    )
    parts.append(f"Negative: {_NEGATIVE_BLOCK}{action_extra_negative}")
    return "\n\n".join(parts)


def _run_generate_image(
    prompt: str,
    output_rel: str,
    size: str,
    has_linh_an: bool,
    use_ref: bool = True,
) -> "tuple[bool, str, Path | None]":
    if not SOCIAL_MANAGER_DIR.exists():
        return False, f"VenHoSocialManager không tồn tại: {SOCIAL_MANAGER_DIR}", None
    cmd = ["python3", "generate_image.py", prompt, output_rel, size]
    if has_linh_an and use_ref:
        cmd.extend(["--ref", "assets/linh-an-master-face.png"])
    try:
        result = subprocess.run(
            cmd,
            cwd=str(SOCIAL_MANAGER_DIR),
            capture_output=True,
            text=True,
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        return False, "Timeout 300s — gpt-image-2 không phản hồi. Thử lại hoặc kiểm tra kết nối.", None
    except Exception as exc:  # noqa: BLE001
        return False, str(exc), None
    img = SOCIAL_MANAGER_DIR / output_rel / "image.png"
    if result.returncode != 0:
        return False, result.stderr or result.stdout, None
    return True, result.stdout, img if img.exists() else None


def _next_video_script_number() -> int:
    if not VIDEO_SCRIPTS_DIR.exists():
        return 6
    nums = [
        int(f.name.split("-")[0])
        for f in VIDEO_SCRIPTS_DIR.glob("*.md")
        if f.name.split("-")[0].isdigit()
    ]
    return (max(nums) + 1) if nums else 6


def _build_caption_prompt(
    concept: str,
    pillar: str,
    funnel: str,
    persona: str,
    golden_rule: str,
    has_linh_an: bool,
    hashtags: str,
) -> str:
    funnel_desc = {
        "TOFU": "Thu hút người chưa biết (60%)",
        "MOFU": "Xây dựng niềm tin (30%)",
        "BOFU": "Chuyển đổi — đặt phòng (10%)",
    }
    linh_an_note = (
        "Có — đề cập tự nhiên, Linh An là người sống gần Hồ Tây, không phải người quảng cáo"
        if has_linh_an
        else "Không"
    )
    return (
        f"Bạn là social media manager của khách sạn Ven Hồ Hotel tại Hà Nội.\n\n"
        f"CONCEPT: {concept}\n"
        f"PILLAR: {pillar}\n"
        f"FUNNEL: {funnel} — {funnel_desc.get(funnel, funnel)}\n"
        f"PERSONA: {persona}\n"
        f"NGUYÊN TẮC VÀNG: {golden_rule}\n"
        f"CÓ LINH AN: {linh_an_note}\n\n"
        "BRAND VOICE: Boutique · Local · Trustworthy · Helpful\n"
        "KHÔNG: quảng cáo lộ liễu · 'sang trọng đẳng cấp' · hard-sell · CTA ép buộc · emoji spam\n"
        "LUÔN: cụ thể · hình ảnh rõ · câu chuyện thật · CTA mềm kiểu 'Nếu bạn đang tìm...'\n"
        "HỒ TÂY LÀ NHÂN VẬT CHÍNH — khách sạn là nơi trải nghiệm Hồ Tây tốt nhất\n\n"
        "---\n\n"
        "Viết 3 caption theo format CHÍNH XÁC dưới đây:\n\n"
        "## FACEBOOK (150–250 từ · storytelling · tiếng Việt)\n"
        "Hook 1 câu → câu chuyện 3–4 câu → thông tin thực tế → CTA mềm\n"
        "Kết thúc với:\n"
        "📍 181 Nguyễn Đình Thi, Tây Hồ, Hà Nội\n"
        "📞 024 3847 4646\n"
        "🌐 venhohotel.com\n"
        f"Hashtag 5–8 không dấu: {hashtags} [thêm phù hợp]\n\n"
        "## INSTAGRAM (80–120 từ · lifestyle · visual)\n"
        "Hook mạnh dòng 1 · Nội dung 3–5 dòng\n"
        "📍 181 Nguyễn Đình Thi, Tây Hồ, Hà Nội\n"
        "📲 Đặt phòng: Link in bio\n"
        "Hashtag 15–20 không dấu\n\n"
        "## THREADS (100–150 từ · conversational · gần gũi · ít emoji · 3–5 hashtag)"
    )


def _generate_video_script(
    concept: str,
    pillar: str,
    date_str: str,
    outfit_desc: str,
    scenes: "list[tuple[str, str, str, str, str]]",
    script_num: int,
) -> str:
    scenes_md_parts: list[str] = []
    for i, (desc_vi, action, scenario_key, camera, lighting) in enumerate(scenes):
        env = _ENV_BLOCKS.get(scenario_key, "")
        seedance = (
            f"[Shot {i + 1}/3 · 5 seconds · 9:16 vertical]\n\n"
            "Linh An: a Vietnamese woman in her mid-20s, long dark brown wavy hair flowing "
            "past her shoulders, elegant East Asian features, soft natural makeup (subtle warm "
            f"eyeshadow, rosy cheeks, nude-pink lips), small pearl-drop earrings, fair porcelain skin.\n"
            f"Outfit: {outfit_desc}.\n"
            f"{action}\n"
            f"{env}\n"
            f"Camera: {camera}.\n"
            f"Style: {lighting}. Ultra-realistic, 4K, cinematic depth of field."
        )
        scenes_md_parts.append(
            f"### Scene {i + 1} — {desc_vi} ({i * 5}–{(i + 1) * 5}s)\n"
            f"**Mô tả:** {desc_vi}\n\n"
            f"**Seedance Prompt:**\n```\n{seedance}\n```"
        )

    scenes_block = "\n\n".join(scenes_md_parts)
    return (
        f"# Script {script_num:03d} — {concept}\n\n"
        f"**Pillar:** {pillar}  \n"
        f"**Đăng:** {date_str}  \n"
        "**Thời lượng:** 15 giây (3 cảnh × 5 giây)  \n"
        "**Tool:** LitMedia Seedance 2.0 — litmedia.ai  \n"
        "**Nhân vật:** Linh An (AI KOL — Fashion & Lifestyle Creator)\n\n"
        "---\n\n"
        "## Concept\n\n"
        f"{concept}\n\n"
        "---\n\n"
        "## Scene Breakdown + Seedance Prompts\n\n"
        f"{scenes_block}\n\n"
        "---\n\n"
        "## Hướng dẫn generate trên LitMedia\n\n"
        "1. Vào **litmedia.ai** → chọn model **Seedance 2.0**\n"
        "2. Settings: **9:16** · **1080p** · **Full** (không phải Fast)\n"
        "3. Generate Scene 1 → Download → Scene 2 → Download → Scene 3 → Download\n"
        "4. Ghép 3 clips trong CapCut + thêm nhạc + text overlay + AI Caption\n\n"
        "---\n\n"
        "## Nhạc gợi ý\n\n"
        f"Tìm trên CapCut phù hợp với pillar **{pillar}**: ambient/soft instrumental, 80–100 BPM.\n\n"
        "---\n\n"
        "## Caption\n\n"
        "### TikTok\n"
        "```\n"
        "[Hook mạnh dòng đầu — gây tò mò hoặc cảm xúc ngay]\n\n"
        "Ven Hồ Hotel, 181 Nguyễn Đình Thi, Tây Hồ\n"
        "Link đặt phòng in bio\n\n"
        "#VenHoHotel #HoTay #TayHo #HanoiHotel\n"
        "```\n\n"
        "### Instagram Reels\n"
        "```\n"
        "[Kể chuyện 3–5 dòng — tone lifestyle, chân thực]\n\n"
        "📍 181 Nguyễn Đình Thi, Tây Hồ, Hà Nội\n"
        "📲 Đặt phòng: Link in bio\n\n"
        "#VenHoHotel #HoTay #TayHo #HanoiHotel #KhachSanHaNoi #HanoiTravel\n"
        "```\n\n"
        "---\n\n"
        "## Checklist\n\n"
        "- [ ] Generate 3 clips trên Seedance 2.0\n"
        "- [ ] Ghép clips trong CapCut (Scene 1 → 2 → 3)\n"
        "- [ ] Thêm nhạc nền\n"
        "- [ ] Text overlay: tên khách sạn + CTA ở cuối\n"
        "- [ ] AI Caption bật\n"
        "- [ ] Export 9:16 · 1080p · 30fps\n"
        "- [ ] Đăng đúng giờ: TikTok 20:00–22:00 / Reels 11:00–13:00\n"
    )


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
            padding: 32px 32px 72px;
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
            display: grid;
            gap: 24px;
            grid-template-columns: 1fr auto 1fr;
            min-height: 72px;
            margin-bottom: 24px;
            padding: 16px 24px;
            position: sticky;
            top: 0;
            z-index: 3;
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
        .oc-header-actions {
            align-items: center;
            color: var(--oc-secondary);
            display: flex;
            font-size: 13px;
            gap: 14px;
            justify-content: flex-end;
        }
        .oc-header-icon {
            align-items: center;
            background: #F2F0EC;
            border-radius: 999px;
            color: var(--oc-primary);
            display: inline-flex;
            font-size: 13px;
            font-weight: 800;
            height: 34px;
            justify-content: center;
            width: 34px;
        }
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
            font-size: 28px;
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
        .oc-workspace-grid {
            display: grid;
            gap: 24px;
            grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
            margin: 24px 0;
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
            grid-template-columns: repeat(3, minmax(0, 1fr));
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
            .oc-workspace-grid { grid-template-columns: 1fr; }
            .oc-status-grid {
                display: flex;
                overflow-x: auto;
                scroll-snap-type: x mandatory;
            }
            .oc-status-card { flex: 0 0 220px; scroll-snap-align: start; }
            .oc-two-col { grid-template-columns: 1fr; }
            .oc-action-grid { display: flex; overflow-x: auto; }
            .oc-action-chip { flex: 0 0 auto; min-height: 48px; }
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
                <div class="oc-brand-subtitle">{_esc(header.get('subtitle', 'Workspace'))}</div>
            </div>
            <div class="oc-header-meta">
                <strong>{_esc(header.get('project_scope', snapshot.project.display_name))}</strong>
            </div>
            <div class="oc-header-actions">
                <span>Last Sync {_esc(header.get('last_sync', 'Recent'))}</span>
                <span class="oc-header-icon" aria-label="Notifications">!</span>
                <span class="oc-header-icon" aria-label="User">U</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_today_focus(focus: dict) -> None:
    st.markdown(
        f"""
        <div class="oc-card oc-focus-card" style="min-height: 140px;">
            <div>
                <div class="oc-label">Today's Focus</div>
                <div class="oc-focus-title">{_esc(focus.get('objective', 'Define today mission'))}</div>
                <div class="oc-muted">
                    Priority #1: <strong>{_esc(focus.get('priority', 'Choose focus'))}</strong><br>
                    Milestone: {_esc(focus.get('milestone', 'Workspace'))}
                </div>
            </div>
            <div class="oc-focus-side">
                <div class="oc-small">ETA: {_esc(focus.get('eta', '10 min'))}</div>
                <span class="oc-btn">{_esc(focus.get('next_action', 'Continue'))}</span>
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
                <div class="oc-label">Current Work</div>
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


def _render_workspace_list(title: str, items: list[dict], empty_message: str) -> None:
    if not items:
        rows = f'<div class="oc-empty">{_esc(empty_message)}</div>'
    else:
        rendered = []
        for item in items[:5]:
            source = str(item.get("source", "Workspace"))
            rendered.append(
                f"""
                <div class="oc-task-row">
                    <div class="oc-task-icon oc-tone-{_status_tone(str(item.get('status', 'Ready')))}">{_esc(source[:1].upper())}</div>
                    <div>
                        <div class="oc-task-title">{_esc(item.get('title', 'Untitled'))}</div>
                        <div class="oc-small">{_esc(source)}</div>
                    </div>
                    <span class="oc-btn oc-btn-secondary">{_esc(item.get('action_label', 'Open'))} &gt;</span>
                </div>
                """
            )
        rows = "".join(rendered)
    st.markdown(
        f"""
        <div class="oc-card">
            <h2 class="oc-section-title">{_esc(title)}</h2>
            {rows}
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
    st.sidebar.markdown("### VENHO OS")
    st.sidebar.caption("Business Operating Workspace")
    section = st.sidebar.radio(
        "Navigation",
        [
            "Home Workspace",
            "Projects",
            "Tasks",
            "Knowledge",
            "Workbench",
            "Creative Studio",
            "Publishing",
            "Reports",
            "Settings",
        ],
        key="m10_section",
    )
    project = st.sidebar.text_input("Project", value="venho_hotel", key="m10_project")
    snapshot = build_dashboard_snapshot(BASE_DIR, project=project)
    oc = snapshot.operating_center

    _render_operating_header(snapshot)
    if section == "Home Workspace":
        _render_today_focus(oc["today_focus"])
        _render_current_focus(oc["current_focus"])
        left, right = st.columns(2)
        with left:
            _render_workspace_list(
                "Needs Review",
                oc.get("needs_review", oc["today_tasks"]),
                "No items need review right now.",
            )
        with right:
            _render_workspace_list(
                "Ready to Publish",
                oc.get("ready_to_publish", []),
                "No content is waiting for publishing approval.",
            )
        _render_quick_actions(oc["quick_actions"])
        _render_recent_activity(oc["recent_activity"])
        st.markdown(
            """
            <div class="oc-bottom-nav">
                <div class="oc-bottom-item">Home</div>
                <div class="oc-bottom-item">Projects</div>
                <div class="oc-bottom-item">Tasks</div>
                <div class="oc-bottom-item">Publish</div>
                <div class="oc-bottom-item">Settings</div>
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

    elif section == "Tasks":
        _render_page_header("Tasks", "Daily execution queue grouped by priority and review state.")
        task_cards = [
            {
                "label": task.get("priority", "Task"),
                "title": task.get("task", "Untitled task"),
                "meta": f"{task.get('source', 'Workspace')} · {task.get('status', 'Pending')}",
                "status": task.get("status", "Pending"),
                "action": task.get("action_label", "Open"),
            }
            for task in oc["today_tasks"]
        ]
        _render_card_grid("Today Tasks", task_cards, "No tasks are queued for today.")
        _render_workspace_list("Needs Review", oc.get("needs_review", []), "No items need review right now.")

    elif section == "Knowledge":
        _render_page_header("Knowledge", "Browse DNA subjects and identify missing knowledge without exposing raw JSON.")
        knowledge_cards = [
            {
                "label": "DNA Subject",
                "title": asset.subject,
                "meta": (
                    f"Config: {'yes' if asset.has_config else 'no'} · "
                    f"Overrides: {'yes' if asset.has_overrides else 'no'} · "
                    f"Compact: {'yes' if asset.has_compact else 'no'}"
                ),
                "status": "Ready" if asset.has_dna_json else "Need Review",
                "action": "Open" if asset.has_dna_json else "Build DNA",
            }
            for asset in snapshot.subjects
        ]
        _render_card_grid("Knowledge Assets", knowledge_cards, "No knowledge assets available yet.")

    elif section == "Workbench":
        _render_workbench(snapshot)

    elif section == "Creative Studio":
        _render_page_header("Creative Studio", "AI creation skills for daily production.")
        skill_cards = [
            {
                "label": "Current Skill",
                "title": "Image Creator",
                "meta": "Generate AI image prompts and production-ready image concepts.",
                "status": "Ready",
                "action": "Open from sidebar",
            },
            {
                "label": "Current Skill",
                "title": "Content Creator",
                "meta": "Create social post drafts from Ven Hồ Hotel context.",
                "status": "Ready",
                "action": "Open from sidebar",
            },
            {
                "label": "Current Skill",
                "title": "Video Script Creator",
                "meta": "Build short-form video scripts and scene packages.",
                "status": "Ready",
                "action": "Open from sidebar",
            },
            {
                "label": "Future Skill",
                "title": "Voice / SEO / Email / Translation",
                "meta": "Reserved extension area for future VenHo OS skills.",
                "status": "Planned",
                "action": "Plan",
            },
        ]
        _render_card_grid("Creative Skills", skill_cards, "No creative skills configured.")

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

    elif section == "Reports":
        _render_page_header("Reports", "Review operational reports without turning Home into a KPI wall.")
        report_cards = _cards_from_records(snapshot.analytics_items, label="Report", title_key="id")
        _render_card_grid("Reports", report_cards, "No reports or analytics snapshots are available yet.")
        _render_recent_activity(oc["recent_activity"])

    else:
        _render_page_header("Settings", "Developer and system tools stay here so Workspace remains focused.")
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
        if snapshot.analytics_items:
            _render_card_grid(
                "Analytics",
                _cards_from_records(snapshot.analytics_items, label="Analytics", title_key="id"),
                "No analytics snapshot available.",
            )
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
                width="stretch",
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
            st.dataframe(oc["system_health"], width="stretch", hide_index=True)
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


# ============================================================
# Creative Studio render functions
# ============================================================


def _render_tao_anh_ai() -> None:
    st.title("Tạo Ảnh AI")
    st.caption("gpt-image-2 · Linh An v3.1 · Hotel DNA")

    topic = st.text_input(
        "Topic / concept",
        placeholder="VD: Hoàng hôn Hồ Tây nhìn từ rooftop",
        key="tai_topic",
    )
    has_linh_an = st.checkbox("Có Linh An trong ảnh", value=False, key="tai_has_la")
    scenario = st.selectbox("Scenario / Loại cảnh", list(_ENV_BLOCKS.keys()), key="tai_scenario")

    col1, col2 = st.columns(2)
    with col1:
        size_label = st.selectbox(
            "Kích thước",
            ["portrait — 4:5 (Instagram)", "square — 1:1 (Đa nền tảng)", "story — 9:16 (Reels)"],
            key="tai_size",
        )
        size_key = size_label.split(" ")[0]
    with col2:
        count = st.number_input("Số lượng ảnh", min_value=1, max_value=4, value=1, key="tai_count")

    outfit_key = "A — Cafe Girl"
    action = ""
    use_ref = True
    if has_linh_an:
        outfit_key = st.selectbox("Outfit Linh An", list(_OUTFITS.keys()), key="tai_outfit")
        action = st.text_input(
            "Hành động / Pose (tiếng Anh)",
            placeholder="VD: riding a bicycle along the lakeside street",
            key="tai_action",
        )
        st.caption("Nhập tiếng Anh · Ví dụ: riding a bicycle · sitting at a café table · leaning on the railing")
        use_ref = st.checkbox(
            "Dùng reference image (khuyến nghị cho portrait / đứng)",
            value=True,
            key="tai_use_ref",
        )
        if not use_ref:
            st.info("Text-to-image mode — AI tự do tạo bất kỳ pose/action. Face consistency thấp hơn (7–8.5 thay vì 9).")

    subject = _SCENARIO_SUBJECT.get(scenario)
    dna_compact = _read_dna_compact(subject) if subject else ""
    if dna_compact:
        with st.expander(f"DNA Compact — {subject} (INVARIANT + FORBIDDEN)"):
            st.code(dna_compact, language="markdown")

    assembled = _assemble_image_prompt(scenario, has_linh_an, outfit_key, action, dna_compact)
    prompt_text = st.text_area("Image Prompt (có thể chỉnh sửa)", value=assembled, height=260, key="tai_prompt")

    today = datetime.date.today()
    slug = _slugify(topic or "image-ai")
    folder_name = f"{today.strftime('%d-%m')}-{slug}"
    output_rel = f"photos-ai/{today.year}/{folder_name}"
    st.caption(f"Output: `ops/VenHoSocialManager/{output_rel}/`")

    if st.button("▶ Tạo ảnh", type="primary", key="tai_run"):
        if not topic.strip():
            st.error("Cần nhập topic.")
            return
        if not SOCIAL_MANAGER_DIR.exists():
            st.error(f"Không tìm thấy VenHoSocialManager tại: {SOCIAL_MANAGER_DIR}")
            return
        for i in range(int(count)):
            with st.spinner(f"Đang tạo ảnh {i + 1}/{count}..."):
                ok, msg, img_path = _run_generate_image(prompt_text, output_rel, size_key, has_linh_an, use_ref)
            if ok:
                st.success(f"Ảnh {i + 1} xong!")
                if img_path and img_path.exists():
                    if count > 1:
                        renamed = img_path.parent / f"image-{i + 1}.png"
                        img_path.rename(renamed)
                        img_path = renamed
                    st.image(str(img_path))
            else:
                st.error(f"Ảnh {i + 1} lỗi: {msg}")
                break


def _render_tao_social_post() -> None:
    st.title("Tạo Social Post")
    st.caption("Content Strategy v2.0 · Captions + Ảnh AI · gpt-image-2")

    concept = st.text_area(
        "Concept bài viết",
        placeholder="VD: Hoàng hôn Hồ Tây tháng 7 — ánh vàng chiều tà trên mặt hồ",
        key="tsp_concept",
    )
    col1, col2 = st.columns(2)
    with col1:
        pillar = st.selectbox("Content Pillar", list(_PILLARS.keys()), key="tsp_pillar")
    with col2:
        has_linh_an = st.checkbox("Có Linh An trong ảnh", value=False, key="tsp_has_la")

    size_label = st.selectbox(
        "Kích thước ảnh",
        ["portrait — 4:5 (Instagram)", "square — 1:1 (Đa nền tảng)", "story — 9:16 (Reels)"],
        key="tsp_size",
    )
    size_key = size_label.split(" ")[0]

    pillar_info = _PILLARS.get(pillar, {})
    funnel = pillar_info.get("funnel", "TOFU")
    golden_rule = pillar_info.get("golden_rule", "Inspire")
    persona = pillar_info.get("persona", "Persona 1")
    hashtags = pillar_info.get("hashtags", "#VenHoHotel #HoTay")

    if concept.strip():
        st.markdown("---")
        st.subheader("Phân tích Content Strategy v2.0")
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("Persona", persona.split("—")[0].strip())
        with col_b:
            st.metric("Funnel Stage", funnel)
        with col_c:
            st.metric("Nguyên tắc vàng", golden_rule)

        st.markdown("---")
        st.subheader("Prompt cho ChatGPT / Claude — Viết 3 Caption")
        caption_prompt = _build_caption_prompt(
            concept, pillar, funnel, persona, golden_rule, has_linh_an, hashtags
        )
        st.text_area(
            "Copy prompt này → dán vào ChatGPT hoặc Claude để viết caption",
            value=caption_prompt,
            height=280,
            key="tsp_caption_prompt",
        )

        st.markdown("---")
        st.subheader("Tạo ảnh")
        scenario = st.selectbox("Scenario ảnh", list(_ENV_BLOCKS.keys()), key="tsp_scenario")
        outfit_key = "A — Cafe Girl"
        action = ""
        if has_linh_an:
            outfit_key = st.selectbox("Outfit Linh An", list(_OUTFITS.keys()), key="tsp_outfit")
            action = st.text_input(
                "Hành động / Pose",
                placeholder="VD: looking at West Lake from the rooftop railing",
                key="tsp_action",
            )

        subject = _SCENARIO_SUBJECT.get(scenario)
        dna_compact = _read_dna_compact(subject) if subject else ""
        assembled = _assemble_image_prompt(scenario, has_linh_an, outfit_key, action, dna_compact)
        img_prompt = st.text_area("Image Prompt", value=assembled, height=200, key="tsp_img_prompt")

        today = datetime.date.today()
        slug = _slugify(concept)
        folder_rel = f"database/{today.year}/{today.strftime('%m')}/{today.strftime('%Y-%m-%d')}_{slug}"
        st.caption(f"Output: `ops/VenHoSocialManager/{folder_rel}/`")

        if st.button("▶ Tạo ảnh", type="primary", key="tsp_run"):
            if not SOCIAL_MANAGER_DIR.exists():
                st.error(f"Không tìm thấy VenHoSocialManager tại: {SOCIAL_MANAGER_DIR}")
                return
            with st.spinner("Đang tạo ảnh..."):
                ok, msg, img_path = _run_generate_image(img_prompt, folder_rel, size_key, has_linh_an)
            if ok:
                st.success("Ảnh xong!")
                if img_path and img_path.exists():
                    st.image(str(img_path))
                meta = {
                    "date": today.isoformat(),
                    "concept": concept,
                    "pillar": pillar,
                    "funnel_stage": funnel,
                    "persona": persona,
                    "golden_rule": golden_rule,
                    "score": 0,
                    "linh_an": has_linh_an,
                    "source": "streamlit-skill",
                    "status": "pending_review",
                }
                meta_path = SOCIAL_MANAGER_DIR / folder_rel / "meta.json"
                meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
                st.info(f"meta.json đã lưu: `{meta_path}`")
            else:
                st.error(f"Lỗi: {msg}")


def _render_tao_video_script() -> None:
    st.title("Tạo Video Script")
    st.caption("LitMedia Seedance 2.0 · 15 giây · 3 cảnh · Linh An")

    concept = st.text_area(
        "Concept video",
        placeholder="VD: Buổi sáng tại Ven Hồ Hotel — Linh An thưởng thức cà phê nhìn ra Hồ Tây",
        key="tvs_concept",
    )
    col1, col2 = st.columns(2)
    with col1:
        pillar = st.selectbox("Content Pillar", _VIDEO_PILLARS, key="tvs_pillar")
    with col2:
        today = datetime.date.today()
        scheduled_date = st.date_input("Ngày đăng dự kiến", value=today, key="tvs_date")

    next_num = _next_video_script_number()
    slug = _slugify(concept or "video-script")
    filename = f"{next_num:03d}-{slug}.md"
    st.caption(f"File sẽ lưu: `local-generated/social-video/scripts/{filename}`")

    scenes = _SCENE_STRUCTURES.get(
        pillar,
        [
            ("Cảnh 1", "standing in hotel area", "Hotel Room (Lake View)", "slow push in", "natural light"),
            ("Cảnh 2", "looking at West Lake", "Rooftop Ven Hồ Hotel", "slow pan", "golden hour"),
            ("Cảnh 3", "relaxing by the window", "Hotel Room (Lake View)", "static", "soft evening light"),
        ],
    )
    outfit_key = _OUTFIT_BY_PILLAR.get(pillar, "A — Cafe Girl")
    outfit_desc = _OUTFITS.get(outfit_key, "")
    date_str = f"{_DAY_NAMES_VI[scheduled_date.weekday()]}, {scheduled_date.strftime('%d/%m/%Y')}"

    if st.button("▶ Tạo Script", type="primary", key="tvs_run"):
        if not concept.strip():
            st.error("Cần nhập concept.")
            return
        script = _generate_video_script(concept, pillar, date_str, outfit_desc, scenes, next_num)
        st.session_state["_tvs_content"] = script
        st.session_state["_tvs_filename"] = filename

    if "_tvs_content" in st.session_state:
        st.markdown("---")
        with st.expander("Preview Script", expanded=True):
            st.markdown(st.session_state["_tvs_content"])
        col_save, col_clear = st.columns([2, 1])
        with col_save:
            if st.button("Lưu file script", key="tvs_save"):
                VIDEO_SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
                out = VIDEO_SCRIPTS_DIR / st.session_state["_tvs_filename"]
                out.write_text(st.session_state["_tvs_content"], encoding="utf-8")
                st.success(f"Đã lưu: `{out}`")
        with col_clear:
            if st.button("Xóa preview", key="tvs_clear"):
                del st.session_state["_tvs_content"]
                del st.session_state["_tvs_filename"]
                st.rerun()


st.set_page_config(page_title="VENHO OS", page_icon="🧬", layout="wide")

mode = st.sidebar.radio(
    "Chọn màn hình",
    [
        "VENHO OS — Home Workspace",
        "Mode A — Observe (bất kỳ ảnh nào)",
        "Mode B — Build DNA (nhiều ảnh cùng 1 subject)",
        "─── Creative Studio ───",
        "Tạo Ảnh AI",
        "Tạo Social Post",
        "Tạo Video Script",
    ],
)

if mode.startswith("VENHO OS"):
    _render_dashboard()

elif mode == "Tạo Ảnh AI":
    _render_tao_anh_ai()

elif mode == "Tạo Social Post":
    _render_tao_social_post()

elif mode == "Tạo Video Script":
    _render_tao_video_script()

elif mode.startswith("─"):
    st.info("Chọn một skill từ sidebar bên trái.")

elif mode.startswith("Mode A"):
    st.title("VENHO AI Studio")
    st.caption("Studio Shell")
    st.header("Mode A — Observe")
    st.caption("Mỗi ảnh → 1 file quan sát .md + .json. Không tạo DNA.")

    input_path = _image_input_selector("data/projects/_inbox/media", "mode_a")
    output_dir = st.text_input("Folder output (để trống = mặc định trong settings.yaml)", value="")
    output_path = _mode_a_output_path(output_dir)
    st.caption(f"Output sẽ lưu tại: `{output_path}`")
    if st.button("Mở folder output", key="mode_a_open_output"):
        opened, error = _open_folder(output_path)
        if opened:
            st.success(f"Đã mở folder output: `{output_path}`")
        else:
            st.error(f"Không mở được folder output: {error}")
    provider = _provider_selector("mode_a_provider")

    if st.button("▶ Chạy Mode A", type="primary"):
        if input_path is None:
            st.error("Cần nhập folder ảnh input.")
        elif not input_path.is_dir():
            st.error(f"Không tìm thấy folder: {input_path}")
        else:
            kwargs = {
                "input_dir": input_path,
                "output_dir": output_path,
                "provider": provider,
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

    default_input = f"data/projects/{project}/media/{resolved_subject}"
    input_path = _image_input_selector(default_input, "mode_b")
    output_path = _mode_b_output_path(project)
    st.caption(f"Output sẽ lưu tại: `{output_path}`")
    if st.button("Mở folder output", key="mode_b_open_output"):
        opened, error = _open_folder(output_path)
        if opened:
            st.success(f"Đã mở folder output: `{output_path}`")
        else:
            st.error(f"Không mở được folder output: {error}")
    dna_version = st.text_input("DNA version", value="1.0")
    provider = _provider_selector("mode_b_provider")

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
        elif input_path is None:
            st.error("Cần nhập folder ảnh input.")
        else:
            if not input_path.is_dir() or not any(input_path.iterdir()):
                st.error(f"Folder rỗng hoặc không tồn tại: {input_path}")
            else:
                kwargs = {
                    "project": project,
                    "subject": resolved_subject,
                    "input_dir": input_path,
                    "dna_version": dna_version,
                    "provider": provider,
                }
                result, error, _ = _run_with_live_log(run_mode_b, kwargs)
                if error:
                    st.error(f"Lỗi: {error}")
                elif result:
                    st.success("Xong!")
                    _show_output_paths(result)
