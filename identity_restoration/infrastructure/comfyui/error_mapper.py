from __future__ import annotations

from typing import Mapping

from ...domain.errors import RestorationError

# v2.0 PHẦN 8.5 — the full symptom -> ERR_GW_* table. Single source: nothing
# outside this module should be inspecting ComfyUI response bodies to decide
# an error code.


def map_history_status(status: Mapping[str, object], *, prompt_id: str) -> RestorationError | None:
    status_str = status.get("status_str")
    if status_str != "error":
        return None
    messages = status.get("messages") or []
    detail = " ".join(str(item) for item in messages) if messages else "no detail reported"
    if "oom" in detail.lower() or "out of memory" in detail.lower() or "cuda out of memory" in detail.lower():
        return RestorationError("ERR_GW_VRAM_EXHAUSTED", f"job {prompt_id}: {detail}", retryable=True)
    return RestorationError("ERR_GW_WORKFLOW_INVALID", f"job {prompt_id}: {detail}", retryable=False)


def map_prompt_submission_error(status_code: int, body: str) -> RestorationError:
    if status_code == 400:
        return RestorationError("ERR_GW_WORKFLOW_INVALID", body[:500], retryable=False)
    return RestorationError("ERR_GW_UPLOAD_FAILED", f"HTTP {status_code}: {body[:400]}", retryable=True)


def map_missing_node_title(title: str) -> RestorationError:
    return RestorationError("ERR_GW_NODE_BINDING_FAILED",
                            f"workflow has no node titled {title!r} — registry is out of sync with workflow file",
                            retryable=False)


def map_connection_failure(detail: str) -> RestorationError:
    return RestorationError("ERR_GW_WORKER_OFFLINE", detail, retryable=True)


def map_empty_outputs(prompt_id: str) -> RestorationError:
    return RestorationError("ERR_GW_EMPTY_OUTPUT",
                            f"job {prompt_id} completed but reported no output images", retryable=False)


def map_undecodable_view_response(prompt_id: str) -> RestorationError:
    return RestorationError("ERR_GW_EMPTY_OUTPUT", f"/view for job {prompt_id} did not return decodable bytes",
                            retryable=False)


def map_timeout(prompt_id: str, timeout_seconds: float) -> RestorationError:
    return RestorationError("ERR_GW_WORKER_TIMEOUT", f"job {prompt_id} exceeded {timeout_seconds}s", retryable=True)
