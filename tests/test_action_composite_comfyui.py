"""ComfyUI adapter contract, exercised against a local fake HTTP server.

No ComfyUI installation, no model files and no paid API call are involved.
"""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from io import BytesIO
from urllib.parse import parse_qs, urlparse

import pytest
from PIL import Image

from image_studio_runtime.action_composite.providers import (
    DEFAULT_NODE_BINDINGS, ComfyUIIdentityRestorer, inject_inputs,
)

WORKFLOW = {
    "1": {"class_type": "LoadImage", "inputs": {"image": ""}, "_meta": {"title": "base_image"}},
    "2": {"class_type": "LoadImage", "inputs": {"image": ""}, "_meta": {"title": "face_mask"}},
    "3": {"class_type": "LoadImage", "inputs": {"image": ""}, "_meta": {"title": "identity_reference"}},
    "4": {"class_type": "SaveImage", "inputs": {}, "_meta": {"title": "output"}},
}


def _png_bytes(color=(10, 20, 30, 255)) -> bytes:
    buffer = BytesIO()
    Image.new("RGBA", (8, 8), color).save(buffer, format="PNG")
    return buffer.getvalue()


class FakeComfyUI:
    """Records what the adapter sent and replays a scripted history response."""

    def __init__(self, *, history_status="success", output_filename="result.png"):
        self.uploads: list[str] = []
        self.submitted_prompt: dict | None = None
        self.view_queries: list[dict] = []
        self.history_status = history_status
        self.output_filename = output_filename
        self.server = HTTPServer(("127.0.0.1", 0), self._handler())
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    @property
    def endpoint(self) -> str:
        return f"http://127.0.0.1:{self.server.server_port}"

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def _handler(self):
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):  # keep pytest output clean
                pass

            def _reply(self, payload: bytes, content_type="application/json"):
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def do_POST(self):
                body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
                if self.path == "/upload/image":
                    name = body.split(b'filename="')[1].split(b'"')[0].decode()
                    fake.uploads.append(name)
                    self._reply(json.dumps({"name": name, "subfolder": "", "type": "input"}).encode())
                elif self.path == "/prompt":
                    fake.submitted_prompt = json.loads(body)["prompt"]
                    self._reply(json.dumps({"prompt_id": "p1"}).encode())
                else:
                    self.send_error(404)

            def do_GET(self):
                parsed = urlparse(self.path)
                if parsed.path == "/history/p1":
                    if fake.history_status == "error":
                        item = {"status": {"status_str": "error", "messages": [["execution_error", {}]]}}
                    else:
                        item = {"status": {"status_str": "success"},
                                "outputs": {"4": {"images": [{"filename": fake.output_filename,
                                                              "subfolder": "", "type": "output"}]}}}
                    self._reply(json.dumps({"p1": item}).encode())
                elif parsed.path == "/view":
                    fake.view_queries.append({k: v[0] for k, v in parse_qs(parsed.query, keep_blank_values=True).items()})
                    self._reply(_png_bytes((200, 150, 130, 255)), content_type="image/png")
                elif parsed.path == "/system_stats":
                    self._reply(b"{}")
                else:
                    self.send_error(404)

        return Handler


@pytest.fixture
def fake_comfyui():
    servers: list[FakeComfyUI] = []

    def factory(**kwargs):
        server = FakeComfyUI(**kwargs)
        servers.append(server)
        return server

    yield factory
    for server in servers:
        server.close()


def _restore(server: FakeComfyUI, **config):
    restorer = ComfyUIIdentityRestorer(server.endpoint)
    return restorer.restore(Image.new("RGBA", (16, 16), (1, 2, 3, 255)), _png_bytes(),
                            Image.new("L", (16, 16), 0), {},
                            {"workflow": WORKFLOW, "node_bindings": DEFAULT_NODE_BINDINGS, **config})


def test_restore_uploads_all_three_assets_and_wires_them_into_the_workflow(fake_comfyui):
    server = fake_comfyui()

    result = _restore(server)

    assert len(server.uploads) == 3, "base image, face mask and A2 reference must all reach ComfyUI"
    assert [name.rsplit("_", 1)[-1] for name in server.uploads] == ["base.png", "mask.png", "a2.png"]
    wired = {server.submitted_prompt[node]["inputs"]["image"] for node in ("1", "2", "3")}
    assert wired == set(server.uploads)
    assert result.size == (8, 8)


def test_workflow_missing_a_bound_node_fails_loudly():
    with pytest.raises(ValueError, match="face_mask"):
        inject_inputs({"1": {"inputs": {}, "_meta": {"title": "base_image"}}},
                      {"mask": "uploaded.png"}, DEFAULT_NODE_BINDINGS)


def test_inject_inputs_does_not_mutate_the_registered_workflow():
    inject_inputs(WORKFLOW, {"base": "uploaded.png"}, DEFAULT_NODE_BINDINGS)
    assert WORKFLOW["1"]["inputs"]["image"] == ""


def test_comfyui_error_status_fails_fast_instead_of_waiting_for_timeout(fake_comfyui):
    server = fake_comfyui(history_status="error")

    with pytest.raises(RuntimeError, match="failed"):
        # A long timeout: a broken graph must surface now, not in two minutes.
        _restore(server, timeout_seconds=120)


def test_output_filename_with_special_characters_is_encoded(fake_comfyui):
    server = fake_comfyui(output_filename="Linh An & face_00001.png")

    _restore(server)

    assert server.view_queries[0]["filename"] == "Linh An & face_00001.png"


def test_missing_workflow_is_rejected_before_any_upload(fake_comfyui):
    server = fake_comfyui()
    restorer = ComfyUIIdentityRestorer(server.endpoint)

    with pytest.raises(ValueError, match="workflow JSON is required"):
        restorer.restore(Image.new("RGBA", (16, 16)), b"", Image.new("L", (16, 16)), {}, {})
    assert server.uploads == []


def test_health_check_reports_unreachable_endpoint():
    assert ComfyUIIdentityRestorer("http://127.0.0.1:1").health_check() is False
