from __future__ import annotations

from publishing_gateway.schemas.delivery_receipt import DeliveryReceipt


def render_receipt_markdown(receipt: DeliveryReceipt) -> str:
    lines = [
        f"# Delivery Receipt — {receipt.package_id}",
        "",
        f"- Project: {receipt.project}",
        f"- Status: {receipt.overall_status}",
        f"- Published timestamp: {receipt.published_timestamp}",
        f"- Idempotency key: {receipt.idempotency_key}",
        "",
        "## Platform Results",
    ]
    for platform, result in receipt.platform_results.items():
        lines.extend(
            [
                "",
                f"### {platform}",
                f"- Status: {result.status}",
                f"- Success: {result.success}",
                f"- Post ID: {result.post_id or ''}",
                f"- Public URL: {result.public_url or ''}",
                f"- Error: {result.error_code or ''}",
            ]
        )
    return "\n".join(lines) + "\n"
