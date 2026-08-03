from __future__ import annotations


class M05ContentBridge:
    def generate_candidates(self, brief: dict) -> list[dict]:
        message = brief["single_minded_message"]
        platforms = brief.get("platforms", ["facebook"])
        candidates = []
        for angle in ("emotional", "practical", "proof_led"):
            candidates.append(
                {
                    "id": f"{brief['id']}-{angle}",
                    "creative_brief_id": brief["id"],
                    "platform": platforms[0],
                    "language": "vi",
                    "angle_type": angle,
                    "hook": message,
                    "body": message,
                    "cta": brief.get("cta", {}).get("type", "booking_link"),
                    "hashtags": ["#VenHoHotel", "#HoTay"],
                    "alt_text": message,
                    "claims": brief.get("proof_points", []),
                    "scene_summary": {
                        "location": brief.get("visual", {}).get("scenario_key", ""),
                        "time_of_day": "morning",
                        "entities": brief.get("visual", {}).get("required_entities", []),
                        "mood": "calm",
                    },
                    "rubric": {"total": 0},
                }
            )
        return candidates
