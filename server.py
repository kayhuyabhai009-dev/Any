#!/usr/bin/env python3
"""Small local receiver and static server for the PDF splitter.

Run with: python3 server.py
The browser UI uploads files to ./uploads; that directory is ignored by git.
"""

from __future__ import annotations

import argparse
import cgi
import json
import os
import re
import sys
import time
import uuid
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
UPLOAD_DIR = ROOT / "uploads"
# Large enough for the shared study PDFs, but still protects a preview server.
MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_MB", "2048")) * 1024 * 1024


def json_bytes(payload: object) -> bytes:
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def safe_filename(original: str) -> str:
    name = Path(original).name.strip() or "uploaded-file"
    name = re.sub(r"[^A-Za-z0-9._()\- ]+", "_", name)
    name = re.sub(r"\s+", " ", name).strip(" .")
    return name[:180] or "uploaded-file"


def unique_destination(original: str) -> Path:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    token = uuid.uuid4().hex[:8]
    return UPLOAD_DIR / f"{stamp}-{token}-{safe_filename(original)}"


def file_records() -> list[dict[str, object]]:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    records = []
    for path in UPLOAD_DIR.iterdir():
        if not path.is_file() or path.name in {".gitkeep"} or path.name.endswith(".uploading"):
            continue
        stat = path.stat()
        records.append({
            "name": path.name,
            "size": stat.st_size,
            "modified": stat.st_mtime,
        })
    return sorted(records, key=lambda item: float(item["modified"]), reverse=True)


class ReceiverHandler(SimpleHTTPRequestHandler):
    server_version = "StudyFileReceiver/1.0"

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def send_json(self, payload: object, status: int = HTTPStatus.OK) -> None:
        body = json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/api/health":
            self.send_json({"ok": True, "maxUploadBytes": MAX_UPLOAD_BYTES})
            return
        if path == "/api/uploads":
            self.send_json({"ok": True, "files": file_records()})
            return
        # Uploaded material is kept in the workspace, not exposed as a public
        # static directory through the preview server.
        if path == "/uploads" or path.startswith("/uploads/"):
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path != "/api/upload":
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        raw_length = self.headers.get("Content-Length")
        try:
            content_length = int(raw_length or "0")
        except ValueError:
            self.send_json({"ok": False, "error": "Invalid Content-Length."}, HTTPStatus.BAD_REQUEST)
            return
        if content_length <= 0:
            self.send_json({"ok": False, "error": "No file data received."}, HTTPStatus.BAD_REQUEST)
            return
        if content_length > MAX_UPLOAD_BYTES + 4 * 1024 * 1024:
            self.send_json({
                "ok": False,
                "error": f"File is larger than the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB receiver limit.",
            }, HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
            return
        if not (self.headers.get_content_type() == "multipart/form-data"):
            self.send_json({"ok": False, "error": "Use multipart/form-data."}, HTTPStatus.BAD_REQUEST)
            return

        try:
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={
                    "REQUEST_METHOD": "POST",
                    "CONTENT_TYPE": self.headers.get("Content-Type", ""),
                    "CONTENT_LENGTH": str(content_length),
                },
                keep_blank_values=False,
            )
            fields = form.list or []
            uploaded = [field for field in fields if getattr(field, "filename", None)]
            if not uploaded:
                self.send_json({"ok": False, "error": "No file field received."}, HTTPStatus.BAD_REQUEST)
                return

            UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
            results = []
            for field in uploaded:
                filename = safe_filename(field.filename)
                destination = unique_destination(filename)
                temporary = destination.with_suffix(destination.suffix + ".uploading")
                written = 0
                try:
                    with temporary.open("wb") as output:
                        while True:
                            chunk = field.file.read(1024 * 1024)
                            if not chunk:
                                break
                            written += len(chunk)
                            if written > MAX_UPLOAD_BYTES:
                                raise ValueError("file exceeds receiver limit")
                            output.write(chunk)
                        output.flush()
                        os.fsync(output.fileno())
                    temporary.replace(destination)
                except Exception:
                    temporary.unlink(missing_ok=True)
                    raise
                results.append({"name": destination.name, "originalName": filename, "size": written})

            self.send_json({"ok": True, "files": results})
        except ValueError as exc:
            self.send_json({"ok": False, "error": str(exc)}, HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
        except Exception as exc:  # keep the receiver usable and return a readable error
            print(f"upload error: {exc}", file=sys.stderr)
            self.send_json({"ok": False, "error": f"Upload failed: {exc}"}, HTTPStatus.BAD_REQUEST)

    def log_message(self, format: str, *args: object) -> None:
        # Keep useful request logs while making large uploads less noisy.
        sys.stderr.write(f"[{self.log_date_time_string()}] {format % args}\n")


class ReceiverServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the PDF splitter and receive files into ./uploads")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    server = ReceiverServer((args.host, args.port), ReceiverHandler)
    print(f"PDF splitter: http://{args.host}:{args.port}")
    print(f"Receiving files in: {UPLOAD_DIR}")
    print(f"Maximum upload: {MAX_UPLOAD_BYTES // (1024 * 1024)} MB")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping receiver…")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
