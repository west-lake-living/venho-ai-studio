from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

import numpy as np
from PIL import Image

from ...application.ports.identity_restorer import IdentityRestorerPort, RestorerDescriptor
from ...domain.entities import RestorationRequest, RestoredCrop

# GW-D10: mock is the default restorer in every test. 0 network call. The
# transform below is a deterministic function of (seed, input bytes) — never
# `random` — so the same request always produces the same fixture output,
# which is what lets a golden-master comparison be meaningful for this
# restorer too.


@dataclass
class MockIdentityRestorer:
    restorer_id: str = "mock"

    def restore(self, request: RestorationRequest) -> RestoredCrop:
        image = Image.open(BytesIO(request.crop_png)).convert("RGBA")
        array = np.asarray(image).astype(np.int16)
        # Deterministic, visible-but-small nudge keyed off the seed so the
        # output is never byte-identical to the input (§3.2 anti-fake-success)
        # while staying reproducible across runs.
        delta = (request.seed % 32) + 1
        array[..., :3] = np.clip(array[..., :3] + delta, 0, 255)
        restored = Image.fromarray(array.astype("uint8")).convert("RGBA")
        buffer = BytesIO()
        restored.save(buffer, format="PNG")
        data = buffer.getvalue()
        return RestoredCrop(png_bytes=data, width=restored.width, height=restored.height)

    def describe(self) -> RestorerDescriptor:
        return RestorerDescriptor(restorer_id="mock", workflow_id=None, workflow_sha256=None)
