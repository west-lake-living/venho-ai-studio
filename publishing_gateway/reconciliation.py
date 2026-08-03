from __future__ import annotations


def reconcile_publication(publication: dict, platform_lookup: dict | None = None) -> dict:
    if publication.get("status") != "UNKNOWN":
        return publication
    lookup = platform_lookup or {}
    platform_post_id = lookup.get("platform_post_id")
    if platform_post_id:
        return {
            **publication,
            "status": "PUBLISHED",
            "platform_post_id": platform_post_id,
            "permalink": lookup.get("permalink"),
            "reconciliation_proof": lookup.get("reconciliation_proof") or f"lookup:{publication.get('platform')}:{platform_post_id}",
        }
    return {**publication, "status": "NEEDS_OPERATOR"}


def apply_reconciliation(publication: dict, platform_lookup: dict | None = None, *, registry=None) -> dict:
    reconciled = reconcile_publication(publication, platform_lookup)
    if registry is None:
        return reconciled
    return registry.update(
        reconciled["publication_id"],
        status=reconciled["status"],
        platform_post_id=reconciled.get("platform_post_id"),
        permalink=reconciled.get("permalink"),
        reconciliation_proof=reconciled.get("reconciliation_proof"),
    )
