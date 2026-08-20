"""Identity Restoration bounded context (GW plan v2.1, GW-D2).

MODULE_ID = "IDR" — deliberately NOT an M-module number. Identity Restoration
is a bounded context inside venho-ai-studio, not a new numbered pipeline
module. See docs/Image studio/VENHO_LINH_AN_GPU_IDENTITY_RESTORATION_CLEAN_ARCHITECTURE_PLAN_v2_0.md
and VENHO_GW_PLAN_PATCH_v2_0_TO_v2_1.md for the full contract.

Extract, don't recreate (patch v2.1 §2.2): this package wraps the proven,
already-running Action Composite pipeline (image_studio_runtime/action_composite/)
behind a clean Port. It does not reimplement face restoration.
"""

MODULE_ID = "IDR"
