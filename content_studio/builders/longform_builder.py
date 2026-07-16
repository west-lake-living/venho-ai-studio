from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

from prompt_studio.schemas.content_prompt import ContentPromptContract

from content_studio.builders.social_builder import _natural_fact_sentence, _source_refs, prefilter_forbidden
from content_studio.schemas.content_output import ContentOutput, GeneratorInfo, SourcePromptRef, ValidationInfo
from content_studio.schemas.content_request import ContentRequest

LongformGeneratorFn = Callable[[ContentRequest, ContentPromptContract, Dict[str, Any]], Dict[str, Any]]


def _base_output(
    request: ContentRequest,
    prompt: ContentPromptContract,
    *,
    source_prompt_file: Optional[str],
    generated_at: Optional[str],
    title: str,
    hook: str,
    body: str,
    cta: str,
    payload: Dict[str, Any],
    visual_note: Optional[str] = None,
) -> ContentOutput:
    text = "\n".join([title, hook, body, cta])
    prefilter_forbidden(text, prompt)
    return ContentOutput(
        project=request.project,
        content_type=request.content_type,
        target_language=request.target_language,
        generated_at=generated_at or datetime.now(timezone.utc).isoformat(),
        source_knowledge=_source_refs(request, prompt),
        source_prompt=SourcePromptRef(
            file=source_prompt_file,
            prompt_id=prompt.prompt_id,
            prompt_version=prompt.prompt_version,
        ),
        generator=GeneratorInfo(model="deterministic-content-builder"),
        title=title,
        hook=hook,
        body=body,
        cta=cta,
        visual_note=visual_note,
        contract_refs=prompt.contract_refs,
        payload=payload,
        validation=ValidationInfo(required=request.validation_required),
    )


def build_blog_draft(
    request: ContentRequest,
    prompt: ContentPromptContract,
    config: Dict[str, Any],
    *,
    source_prompt_file: Optional[str] = None,
    generated_at: Optional[str] = None,
    generator_fn: Optional[LongformGeneratorFn] = None,
) -> ContentOutput:
    if generator_fn is not None:
        draft = generator_fn(request, prompt, config)
        payload = {k: v for k, v in draft.items() if k not in ("title", "hook", "body", "cta")}
        payload.setdefault("keywords", config.get("seo_keywords", {}).get("keywords", {}).get("vi", [])[:3])
        payload.setdefault("internal_links", ["/vi-tri", "/lien-he"])
        return _base_output(
            request, prompt,
            source_prompt_file=source_prompt_file, generated_at=generated_at,
            title=draft["title"], hook=draft["hook"], body=draft["body"], cta=draft["cta"],
            payload=payload,
        )
    keyword = request.keyword or "khách sạn gần Hồ Tây"
    fact = _natural_fact_sentence(prompt, request.target_language)
    title = f"{keyword}: bắt đầu ngày mới bên Hồ Tây"
    article = (
        f"{fact}. Ven Ho Hotel phù hợp với người muốn một điểm ở gọn gàng, gần hồ, "
        "dễ di chuyển và không quá phô trương. Bài viết nên giữ nhịp tư vấn nhẹ, "
        "ưu tiên thông tin kiểm chứng được từ Knowledge thay vì lời hứa quá mức."
    )
    payload = {
        "seo_title": title,
        "meta_description": f"Gợi ý lưu trú gần Hồ Tây: {request.topic} tại Ven Ho Hotel.",
        "slug": keyword.lower().replace(" ", "-"),
        "keywords": [keyword, *config.get("seo_keywords", {}).get("keywords", {}).get("vi", [])[:3]],
        "outline": ["Vì sao chọn khu Hồ Tây", "Trải nghiệm buổi sáng", "Khi nào nên liên hệ Ven Ho"],
        "article": article,
        "faq": [
            {"question": "Ven Ho phù hợp với ai?", "answer": "Khách muốn ở gần Hồ Tây, gọn gàng và thực tế."},
            {"question": "Có nên đặt trực tiếp không?", "answer": "Có thể nhắn Ven Ho để kiểm tra phòng phù hợp."},
        ],
        "internal_links": ["/vi-tri", "/lien-he"],
    }
    return _base_output(
        request, prompt,
        source_prompt_file=source_prompt_file, generated_at=generated_at,
        title=title, hook=f"Góc nhìn SEO cho {keyword}", body=article,
        cta="Nhắn Ven Ho để kiểm tra phòng phù hợp với lịch của bạn.",
        payload=payload,
    )


def build_website_draft(
    request: ContentRequest,
    prompt: ContentPromptContract,
    config: Dict[str, Any],
    *,
    source_prompt_file: Optional[str] = None,
    generated_at: Optional[str] = None,
    generator_fn: Optional[LongformGeneratorFn] = None,
) -> ContentOutput:
    if generator_fn is not None:
        draft = generator_fn(request, prompt, config)
        payload = {k: v for k, v in draft.items() if k not in ("title", "hook", "body", "cta")}
        return _base_output(
            request, prompt,
            source_prompt_file=source_prompt_file, generated_at=generated_at,
            title=draft["title"], hook=draft["hook"], body=draft["body"], cta=draft["cta"],
            payload=payload,
        )
    fact = _natural_fact_sentence(prompt, request.target_language)
    payload = {
        "hero": "Ven Ho Hotel - điểm dừng gọn gàng bên nhịp sống Hồ Tây.",
        "about": f"{fact}. Nội dung website giữ giọng ấm, rõ và đáng tin.",
        "room_description": "Phòng được mô tả theo DNA thực tế, không nâng cấp thành resort xa hoa.",
        "location": "Gần nhịp sống Hồ Tây, phù hợp cho lịch trình Hà Nội nhẹ nhàng.",
        "cta_block": "Xem phòng còn trống hoặc nhắn Ven Ho để được gợi ý.",
        "seo_metadata": {"title": "Ven Ho Hotel gần Hồ Tây", "description": "Lưu trú gọn gàng gần Hồ Tây, Hà Nội."},
    }
    return _base_output(
        request, prompt,
        source_prompt_file=source_prompt_file, generated_at=generated_at,
        title="Website copy Ven Ho", hook=payload["hero"], body=payload["about"],
        cta=payload["cta_block"], payload=payload,
    )


def build_ota_draft(
    request: ContentRequest,
    prompt: ContentPromptContract,
    config: Dict[str, Any],
    *,
    source_prompt_file: Optional[str] = None,
    generated_at: Optional[str] = None,
    generator_fn: Optional[LongformGeneratorFn] = None,
) -> ContentOutput:
    if generator_fn is not None:
        draft = generator_fn(request, prompt, config)
        payload = {k: v for k, v in draft.items() if k not in ("title", "hook", "body", "cta")}
        payload.setdefault("channels", ["Agoda", "Google Business", "direct"])
        return _base_output(
            request, prompt,
            source_prompt_file=source_prompt_file, generated_at=generated_at,
            title=draft["title"], hook=draft["hook"], body=draft["body"], cta=draft["cta"],
            payload=payload,
        )
    fact = _natural_fact_sentence(prompt, request.target_language)
    payload = {
        "channels": ["Agoda", "Google Business", "direct"],
        "short_description": "Ven Ho Hotel là lựa chọn gọn gàng gần Hồ Tây cho chuyến đi Hà Nội.",
        "long_description": f"{fact}. Mô tả OTA tập trung vào sự rõ ràng, vị trí và cảm giác lưu trú thực tế.",
        "facilities_highlight": ["phòng gọn gàng", "gần Hồ Tây", "liên hệ trực tiếp để kiểm tra phòng"],
        "location_highlight": "Khu Hồ Tây, Hà Nội.",
        "guest_fit_messaging": "Phù hợp khách leisure hoặc business muốn nhịp ở bình tĩnh.",
        "rules_notes": "Không tự thêm chính sách chưa có trong Knowledge.",
    }
    return _base_output(
        request, prompt,
        source_prompt_file=source_prompt_file, generated_at=generated_at,
        title="OTA description draft", hook=payload["short_description"], body=payload["long_description"],
        cta="Đặt trực tiếp hoặc nhắn Ven Ho để kiểm tra tình trạng phòng.",
        payload=payload,
    )


def build_faq_draft(
    request: ContentRequest,
    prompt: ContentPromptContract,
    config: Dict[str, Any],
    *,
    source_prompt_file: Optional[str] = None,
    generated_at: Optional[str] = None,
    generator_fn: Optional[LongformGeneratorFn] = None,
) -> ContentOutput:
    if generator_fn is not None:
        draft = generator_fn(request, prompt, config)
        payload = {k: v for k, v in draft.items() if k not in ("title", "hook", "body", "cta")}
        return _base_output(
            request, prompt,
            source_prompt_file=source_prompt_file, generated_at=generated_at,
            title=draft["title"], hook=draft["hook"], body=draft["body"], cta=draft["cta"],
            payload=payload,
        )
    payload = {
        "items": [
            {
                "question": "Ven Ho Hotel phù hợp với kiểu khách nào?",
                "short_answer": "Khách muốn ở gần Hồ Tây trong không gian gọn gàng, thực tế.",
                "long_answer": _natural_fact_sentence(prompt, request.target_language),
                "related_cta": "Nhắn Ven Ho để hỏi phòng phù hợp.",
            },
            {
                "question": "Nội dung này có dựa trên Knowledge không?",
                "short_answer": "Có, draft được sinh từ content prompt của Module 02.",
                "long_answer": "Content Studio không tự bịa chính sách hoặc claim ngoài nguồn.",
                "related_cta": "Xem thêm thông tin phòng trước khi đặt.",
            },
        ]
    }
    return _base_output(
        request, prompt,
        source_prompt_file=source_prompt_file, generated_at=generated_at,
        title="FAQ draft", hook="Câu hỏi thường gặp về Ven Ho",
        body="FAQ chỉ dùng thông tin có nguồn và tránh bịa chính sách.",
        cta="Nhắn Ven Ho nếu bạn cần xác nhận chi tiết trước chuyến đi.",
        payload=payload,
    )


def build_email_draft(
    request: ContentRequest,
    prompt: ContentPromptContract,
    config: Dict[str, Any],
    *,
    source_prompt_file: Optional[str] = None,
    generated_at: Optional[str] = None,
    generator_fn: Optional[LongformGeneratorFn] = None,
) -> ContentOutput:
    if generator_fn is not None:
        draft = generator_fn(request, prompt, config)
        payload = {k: v for k, v in draft.items() if k not in ("title", "hook", "body", "cta")}
        return _base_output(
            request, prompt,
            source_prompt_file=source_prompt_file, generated_at=generated_at,
            title=draft["title"], hook=draft["hook"], body=draft["body"], cta=draft["cta"],
            payload=payload,
        )
    payload = {
        "subject_options": ["Một gợi ý ở gần Hồ Tây", "Bắt đầu ngày Hà Nội nhẹ hơn cùng Ven Ho"],
        "preview_text": "Một lời mời nhẹ để kiểm tra phòng phù hợp gần Hồ Tây.",
        "body": (
            "Chào bạn,\n\n"
            f"{_natural_fact_sentence(prompt, request.target_language)}. "
            "Nếu bạn đang tìm một điểm ở gọn gàng gần Hồ Tây, Ven Ho có thể là lựa chọn vừa đủ cho lịch trình."
        ),
        "follow_up_variation": "Nhắn lại Ven Ho khi bạn có ngày dự kiến, đội ngũ sẽ kiểm tra phòng phù hợp.",
    }
    return _base_output(
        request, prompt,
        source_prompt_file=source_prompt_file, generated_at=generated_at,
        title="Email draft", hook=payload["preview_text"], body=payload["body"],
        cta="Nhắn Ven Ho để kiểm tra phòng còn trống.",
        payload=payload,
    )
