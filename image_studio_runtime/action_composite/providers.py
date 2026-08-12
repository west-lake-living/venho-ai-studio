from __future__ import annotations

import json
import time
import uuid
from io import BytesIO
from typing import Any, Mapping, Optional, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from PIL import Image

#: Workflow node inputs that receive each uploaded asset. Overridable per
#: workflow version so a new ComfyUI graph never requires an adapter change.
DEFAULT_NODE_BINDINGS = {"base": "base_image", "mask": "face_mask", "reference": "identity_reference"}


class IdentityRestorer(Protocol):
    def restore(self, base_image: Image.Image, identity_reference: bytes, face_mask: Image.Image,
                geometry: dict[str, Any], config: dict[str, Any]) -> Image.Image: ...


def inject_inputs(workflow: dict[str, Any], uploads: Mapping[str, str],
                  bindings: Mapping[str, str]) -> dict[str, Any]:
    """Point the workflow's loader nodes at the freshly uploaded assets.

    ``bindings`` maps a role (base/mask/reference) to a node ``_meta.title``, so
    the graph declares its own wiring instead of the adapter guessing node ids.
    """
    prepared = json.loads(json.dumps(workflow))
    titles = {str(node.get("_meta", {}).get("title", "")): node_id
              for node_id, node in prepared.items() if isinstance(node, dict)}
    for role, uploaded_name in uploads.items():
        title = bindings.get(role)
        if title is None:
            continue
        node_id = titles.get(title)
        if node_id is None:
            raise ValueError(f"Workflow has no node titled {title!r} for the {role!r} input")
        prepared[node_id].setdefault("inputs", {})["image"] = uploaded_name
    return prepared


class ComfyUIIdentityRestorer:
    """HTTP adapter for ComfyUI server mode; no UI automation is required."""

    def __init__(self, endpoint: str = "http://127.0.0.1:8188", *, client_id: str = "venho-action-composite",
                 request_timeout: float = 30.0) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.client_id = client_id
        self.request_timeout = request_timeout

    def health_check(self) -> bool:
        try:
            with urlopen(Request(self.endpoint + "/system_stats"), timeout=5) as response:
                return response.status == 200
        except (OSError, ValueError):
            return False

    def restore(self, base_image: Image.Image, identity_reference: bytes, face_mask: Image.Image,
                geometry: dict[str, Any], config: dict[str, Any]) -> Image.Image:
        workflow = config.get("workflow")
        if not isinstance(workflow, dict) or not workflow:
            raise ValueError("ComfyUI workflow JSON is required")
        timeout_seconds = float(config.get("timeout_seconds", 120))
        bindings = config.get("node_bindings") or DEFAULT_NODE_BINDINGS
        prefix = f"venho_{uuid.uuid4().hex[:12]}"

        uploads = {
            "base": self._upload_image(self._to_png(base_image), f"{prefix}_base.png"),
            "mask": self._upload_image(self._to_png(face_mask), f"{prefix}_mask.png"),
            "reference": self._upload_image(identity_reference, f"{prefix}_a2.png"),
        }
        prepared = inject_inputs(workflow, uploads, bindings)

        payload = json.dumps({"prompt": prepared, "client_id": self.client_id}).encode()
        prompt = self._request("POST", "/prompt", payload)
        prompt_id = prompt.get("prompt_id")
        if not prompt_id:
            raise RuntimeError("ComfyUI did not return prompt_id")

        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            item = self._request("GET", f"/history/{prompt_id}").get(prompt_id, {})
            status = item.get("status", {})
            # Fail fast: without this a broken graph would only surface as a
            # timeout, minutes after ComfyUI already gave up.
            if status.get("status_str") == "error":
                raise RuntimeError(f"ComfyUI job {prompt_id} failed: {self._error_detail(status)}")
            image_info = self._first_output(item)
            if image_info is not None:
                return self._download(image_info)
            time.sleep(0.25)
        raise TimeoutError(f"ComfyUI job {prompt_id} timed out after {timeout_seconds}s")

    @staticmethod
    def _to_png(image: Image.Image) -> bytes:
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()

    @staticmethod
    def _first_output(item: Mapping[str, Any]) -> Optional[dict[str, Any]]:
        """Pick the output deterministically; dict order is not a contract."""
        for _, output in sorted(item.get("outputs", {}).items()):
            for image_info in output.get("images", []):
                return image_info
        return None

    @staticmethod
    def _error_detail(status: Mapping[str, Any]) -> str:
        messages = status.get("messages") or []
        return json.dumps(messages, ensure_ascii=False) if messages else "no detail reported"

    def _download(self, image_info: Mapping[str, Any]) -> Image.Image:
        query = urlencode({"filename": image_info["filename"],
                           "subfolder": image_info.get("subfolder", ""),
                           "type": image_info.get("type", "output")})
        with urlopen(Request(f"{self.endpoint}/view?{query}"), timeout=self.request_timeout) as response:
            return Image.open(BytesIO(response.read())).convert("RGBA")

    def _upload_image(self, data: bytes, filename: str) -> str:
        boundary = f"----venho{uuid.uuid4().hex}"
        body = b"".join([
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="image"; filename="{filename}"\r\n'.encode(),
            b"Content-Type: image/png\r\n\r\n", data, b"\r\n",
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"overwrite\"\r\n\r\ntrue\r\n".encode(),
            f"--{boundary}--\r\n".encode(),
        ])
        request = Request(self.endpoint + "/upload/image", data=body, method="POST",
                          headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
        try:
            with urlopen(request, timeout=self.request_timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError) as exc:
            raise RuntimeError(f"ComfyUI upload failed for {filename}: {exc}") from exc
        name = result.get("name", filename)
        subfolder = result.get("subfolder") or ""
        return f"{subfolder}/{name}" if subfolder else name

    def _request(self, method: str, path: str, body: Optional[bytes] = None) -> dict[str, Any]:
        request = Request(self.endpoint + path, data=body, method=method, headers={"Content-Type": "application/json"})
        with urlopen(request, timeout=self.request_timeout) as response:
            return json.loads(response.read().decode("utf-8"))
