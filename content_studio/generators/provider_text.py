from __future__ import annotations

from typing import Protocol


class TextProvider(Protocol):
    def generate_candidates(self, brief: dict) -> list[dict]:
        ...


class MockTextProvider:
    def generate_candidates(self, brief: dict) -> list[dict]:
        message = brief["single_minded_message"]
        platform = (brief.get("platforms") or ["facebook"])[0]
        proof_points = brief.get("proof_points", [])
        entities = brief.get("visual", {}).get("required_entities", [])
        return [
            {
                "id": f"{brief['id']}-{angle}",
                "creative_brief_id": brief["id"],
                "platform": platform,
                "language": "vi",
                "angle_type": angle,
                "hook": hook,
                "body": f"{message} {body}",
                "cta": brief.get("cta", {}).get("type", "booking_link"),
                "hashtags": ["#VenHoHotel", "#HoTay"],
                "alt_text": message,
                "claims": proof_points,
                "scene_summary": {
                    "location": brief.get("visual", {}).get("scenario_key", ""),
                    "time_of_day": "morning",
                    "entities": entities,
                    "mood": "calm",
                },
                "rubric": {},
            }
            for angle, hook, body in (
                ("emotional", "Một buổi sáng chậm bên Hồ Tây", "Không gian nhỏ, thật và gần hồ."),
                ("practical", "Cần chỗ nghỉ gọn gần Hồ Tây?", "Ven Hồ phù hợp cho lịch trình cần di chuyển nhẹ."),
                ("proof_led", "12 phòng boutique cạnh Hồ Tây", "Các điểm chính được kiểm chứng trước khi đăng."),
            )
        ]
