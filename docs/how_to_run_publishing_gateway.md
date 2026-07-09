# How to Run Publishing Gateway

Automated mode is dry-run first:

```bash
venho-publish publish --package-file data/projects/venho_hotel/publishing/fixtures/approved_package.json --dry-run
```

Retry one platform:

```bash
venho-publish retry --package-file data/projects/venho_hotel/publishing/fixtures/approved_package.json --platform instagram --dry-run
```

Receipt lookup:

```bash
venho-publish receipt --package-id pkg_20260709_westlake
```

Rules:

- Do not run live mode from pytest.
- Do not commit real platform tokens.
- Use `M07_APPROVAL_SECRET` or an explicit `--approval-secret` outside tests.
- Conditional platforms remain disabled until API access is confirmed.

Controlled real API checklist:

1. Use a test page, account, or sandbox where the platform supports it.
2. Export required token environment variables only in the local shell.
3. Run a dry-run with the same package first.
4. Confirm the platform payload, media URLs, and approval signature.
5. Run live mode manually.
6. Save the receipt and verify public URL/post ID.
7. Use platform rollback/delete tools manually if the post must be removed.
