from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from io import BytesIO
from typing import Any, Mapping, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .error_mapper import (
    map_connection_failure,
    map_empty_outputs,
    map_history_status,
    map_prompt_submission_error,
    map_timeout,
    map_undecodable_view_response,
)

# v2.0 PHẦN 8.2/8.3. Two silent hazards of /upload/image (GW-E9):
#   1. Default overwrite behaviour clobbers same-named files across jobs.
#   2. When overwrite=false, ComfyUI renames on collision — the name you sent
#      is not guaranteed to be the name that exists on the worker.
# Rule: always namespace by run/attempt, always read `name` back from the
# response, never assume the requested filename survived.


@dataclass(frozen=True)
class UploadedRef:
    name: str
    subfolder: str
    type: str

    @property
    def qualified_name(self) -> str:
        return f"{self.subfolder}/{self.name}" if self.subfolder else self.name


@dataclass
class ComfyUIHttpClient:
    base_url: str
    timeout_s: float = 30.0
    client_id: str = "venho-identity-restoration"

    def upload_image(self, data: bytes, filename: str, *, run_id: str, attempt_id: str) -> UploadedRef:
        boundary = f"----venho{uuid.uuid4().hex}"
        subfolder = f"venho/{run_id}/{attempt_id}"
        body = b"".join([
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="image"; filename="{filename}"\r\n'.encode(),
            b"Content-Type: image/png\r\n\r\n", data, b"\r\n",
            f'--{boundary}\r\nContent-Disposition: form-data; name="overwrite"\r\n\r\nfalse\r\n'.encode(),
            f'--{boundary}\r\nContent-Disposition: form-data; name="type"\r\n\r\ninput\r\n'.encode(),
            f'--{boundary}\r\nContent-Disposition: form-data; name="subfolder"\r\n\r\n{subfolder}\r\n'.encode(),
            f"--{boundary}--\r\n".encode(),
        ])
        request = Request(self._url("/upload/image"), data=body, method="POST",
                          headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
        try:
            with urlopen(request, timeout=self.timeout_s) as response:
                result = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, OSError) as exc:
            raise map_connection_failure(f"upload {filename!r} failed: {exc}") from exc
        # Source of truth is the response, never the requested filename (GW-E9).
        return UploadedRef(name=result["name"], subfolder=result.get("subfolder", ""),
                           type=result.get("type", "input"))

    def submit_prompt(self, workflow: Mapping[str, Any]) -> str:
        payload = json.dumps({"prompt": workflow, "client_id": self.client_id}).encode()
        request = Request(self._url("/prompt"), data=payload, method="POST",
                          headers={"Content-Type": "application/json"})
        try:
            with urlopen(request, timeout=self.timeout_s) as response:
                body = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise map_prompt_submission_error(exc.code, exc.read().decode("utf-8", "replace")) from exc
        except (URLError, OSError) as exc:
            raise map_connection_failure(f"POST /prompt failed: {exc}") from exc
        prompt_id = body.get("prompt_id")
        if not prompt_id:
            raise map_prompt_submission_error(200, "response had no prompt_id")
        return prompt_id

    def free_memory(self) -> Mapping[str, Any]:
        """Release resident ComfyUI models using the worker's existing API."""
        payload = json.dumps({"unload_models": True, "free_memory": True}).encode()
        request = Request(
            self._url("/free"), data=payload, method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urlopen(request, timeout=self.timeout_s) as response:
                body = response.read().decode("utf-8")
                return json.loads(body) if body else {}
        except HTTPError as exc:
            raise map_prompt_submission_error(exc.code, exc.read().decode("utf-8", "replace")) from exc
        except (URLError, OSError, ValueError) as exc:
            raise map_connection_failure(f"POST /free failed: {exc}") from exc

    def poll_until_complete(self, prompt_id: str, *, timeout_seconds: float) -> Mapping[str, Any]:
        """GW-D8: polling, not WebSocket. Backoff: first poll after 2s, x1.5, cap 10s."""
        deadline = time.monotonic() + timeout_seconds
        delay = 2.0
        while time.monotonic() < deadline:
            time.sleep(min(delay, max(deadline - time.monotonic(), 0)))
            history = self._get(f"/history/{prompt_id}")
            item = history.get(prompt_id)
            if item is not None:
                status = item.get("status", {})
                error = map_history_status(status, prompt_id=prompt_id)
                if error is not None:
                    raise error
                outputs = self._first_output(item)
                if outputs is not None:
                    return outputs
                if status.get("completed") or status.get("status_str") == "success":
                    raise map_empty_outputs(prompt_id)
            delay = min(delay * 1.5, 10.0)
        self.interrupt()
        raise map_timeout(prompt_id, timeout_seconds)

    def download(self, image_info: Mapping[str, Any]) -> bytes:
        query = urlencode({"filename": image_info["filename"], "subfolder": image_info.get("subfolder", ""),
                           "type": image_info.get("type", "output")})
        try:
            with urlopen(Request(self._url(f"/view?{query}")), timeout=self.timeout_s) as response:
                data = response.read()
        except (HTTPError, URLError, OSError) as exc:
            raise map_connection_failure(f"GET /view failed: {exc}") from exc
        if not data:
            raise map_undecodable_view_response(image_info.get("filename", "?"))
        return data

    def interrupt(self) -> None:
        # Best-effort cleanup on timeout; success is not load-bearing.
        try:
            urlopen(Request(self._url("/interrupt"), data=b"", method="POST"), timeout=5)
        except (HTTPError, URLError, OSError):
            pass

    def _first_output(self, item: Mapping[str, Any]) -> Optional[dict[str, Any]]:
        for _, output in sorted(item.get("outputs", {}).items()):
            for image_info in output.get("images", []):
                return image_info
        return None

    def _get(self, path: str) -> dict[str, Any]:
        try:
            with urlopen(Request(self._url(path)), timeout=self.timeout_s) as response:
                return json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, OSError) as exc:
            raise map_connection_failure(f"GET {path} failed: {exc}") from exc

    def _url(self, path: str) -> str:
        return self.base_url.rstrip("/") + path
