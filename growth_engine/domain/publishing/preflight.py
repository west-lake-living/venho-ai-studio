from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class PreflightInput:
    approval_valid: bool
    channel_enabled: bool
    config_hash_matches: bool
    media_exists: bool
    media_hash_matches: bool
    media_policy_valid: bool
    media_fetch_ok: bool
    caption_hash_matches: bool
    caption_has_placeholder: bool
    facts_valid: bool
    qc_revoked: bool
    now_ms: int
    deadline_at_ms: int
    mode_allows: bool
    paused: bool
    epoch_matches: bool

    def __post_init__(self) -> None:
        for name in (
            "approval_valid", "channel_enabled", "config_hash_matches", "media_exists",
            "media_hash_matches", "media_policy_valid", "media_fetch_ok",
            "caption_hash_matches", "caption_has_placeholder", "facts_valid",
            "qc_revoked", "mode_allows", "paused", "epoch_matches",
        ):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f"{name} must be boolean")
        if type(self.now_ms) is not int or type(self.deadline_at_ms) is not int:
            raise ValueError("preflight timestamps must be integer epoch milliseconds")


@dataclass(frozen=True)
class PreflightIssue:
    code: str
    blocking: bool
    message_vi: str


Rule = Callable[[PreflightInput], PreflightIssue | None]


def run_preflight(value: PreflightInput) -> list[PreflightIssue]:
    return [issue for rule in _RULES if (issue := rule(value)) is not None]


def _approval_invalid(value: PreflightInput) -> PreflightIssue | None:
    return _issue(not value.approval_valid, "PF_APPROVAL_INVALID", True, "Bản duyệt không còn hiệu lực cho phiên bản này.")


def _channel_disabled(value: PreflightInput) -> PreflightIssue | None:
    return _issue(not value.channel_enabled, "PF_CHANNEL_DISABLED", True, "Page đích đang tắt.")


def _config_mismatch(value: PreflightInput) -> PreflightIssue | None:
    return _issue(not value.config_hash_matches, "PF_CONFIG_MISMATCH", True, "Cấu hình đích đã đổi sau khi duyệt.")


def _media_missing(value: PreflightInput) -> PreflightIssue | None:
    return _issue(not value.media_exists, "PF_MEDIA_MISSING", True, "Không tìm thấy tệp ảnh đã duyệt trên máy chủ.")


def _media_hash_mismatch(value: PreflightInput) -> PreflightIssue | None:
    return _issue(not value.media_hash_matches, "PF_MEDIA_HASH_MISMATCH", True, "Ảnh trên máy chủ không khớp ảnh đã duyệt.")


def _media_policy(value: PreflightInput) -> PreflightIssue | None:
    return _issue(not value.media_policy_valid, "PF_MEDIA_POLICY", True, "Ảnh vượt giới hạn kích thước/dung lượng.")


def _media_fetch_failed(value: PreflightInput) -> PreflightIssue | None:
    return _issue(not value.media_fetch_ok, "PF_MEDIA_FETCH_FAILED", False, "Make chưa tải được ảnh; có thể giao lại nếu còn giờ.")


def _caption_hash_mismatch(value: PreflightInput) -> PreflightIssue | None:
    return _issue(not value.caption_hash_matches, "PF_CAPTION_HASH_MISMATCH", True, "Nội dung bài khác bản đã duyệt.")


def _caption_placeholder(value: PreflightInput) -> PreflightIssue | None:
    return _issue(value.caption_has_placeholder, "PF_CAPTION_PLACEHOLDER", True, "Nội dung còn chỗ trống chưa điền.")


def _fact_expired(value: PreflightInput) -> PreflightIssue | None:
    return _issue(not value.facts_valid, "PF_FACT_EXPIRED", True, "Thông tin trong bài đã hết hiệu lực.")


def _qc_revoked(value: PreflightInput) -> PreflightIssue | None:
    return _issue(value.qc_revoked, "PF_QC_REVOKED", True, "Ảnh đã bị cách ly sau khi duyệt.")


def _window_closed(value: PreflightInput) -> PreflightIssue | None:
    return _issue(value.now_ms > value.deadline_at_ms, "PF_WINDOW_CLOSED", True, "Đã quá cửa sổ đăng.")


def _mode_forbids(value: PreflightInput) -> PreflightIssue | None:
    return _issue(not value.mode_allows, "PF_MODE_FORBIDS", False, "Chế độ đăng hiện tại không cho phép.")


def _paused(value: PreflightInput) -> PreflightIssue | None:
    return _issue(value.paused, "PF_PAUSED", False, "Đang tạm dừng đăng.")


def _epoch_mismatch(value: PreflightInput) -> PreflightIssue | None:
    return _issue(not value.epoch_matches, "PF_EPOCH_MISMATCH", True, "Lệnh thuộc phiên vận hành cũ.")


def _issue(triggered: bool, code: str, blocking: bool, message_vi: str) -> PreflightIssue | None:
    return PreflightIssue(code, blocking, message_vi) if triggered else None


_RULES: tuple[Rule, ...] = (
    _approval_invalid,
    _channel_disabled,
    _config_mismatch,
    _media_missing,
    _media_hash_mismatch,
    _media_policy,
    _media_fetch_failed,
    _caption_hash_mismatch,
    _caption_placeholder,
    _fact_expired,
    _qc_revoked,
    _window_closed,
    _mode_forbids,
    _paused,
    _epoch_mismatch,
)
