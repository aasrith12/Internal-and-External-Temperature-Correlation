"""Local dashboard server for the temperature correlation project.

Serves the dashboard UI (this folder) plus the project's data/results files,
and exposes a small JSON API so the dashboard can show live dataset status,
read result CSVs/summaries, and re-run the analysis scripts on demand.

Run with:  python dashboard/server.py
Then open: http://127.0.0.1:8765/dashboard/index.html
"""

import base64
import binascii
import csv
import json
import os
import subprocess
import sys
import time
import urllib.parse
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SENSOR_DIR = PROJECT_ROOT / "Temperature sensors data - split sheets"
PORT = 8765

REQUIRED_FILES = [
    "IdentiCool Temperature Sensor 1.xlsx",
    "IdentiCool Temperature Sensor 2.xlsx",
    "Thermocouple TA 30C.xlsx",
    "Thermocouple TA 37C.xlsx",
    "Wireless Temperature Sensor 1.xlsx",
    "Wireless Temperature Sensor 2.xlsx",
]

# Order matters: compare_thermocouple_relationships.py reads the metrics
# CSVs produced by the identicool/wireless scripts, so those must run first.
SCRIPTS_IN_ORDER = [
    "analyze_sensor_correlations.py",
    "analyze_thermocouple_identicool_correlations.py",
    "analyze_thermocouple_wireless_correlations.py",
    "compare_thermocouple_relationships.py",
    "analyze_lagged_thermocouple_wireless.py",
    "analyze_exponential_thermal_models.py",
]

# Upload feature: each slot maps to exactly one required source workbook.
# Uploading a file for a slot always replaces that sensor's data, never any other.
UPLOAD_SLOTS = {
    "identicool1": "IdentiCool Temperature Sensor 1.xlsx",
    "identicool2": "IdentiCool Temperature Sensor 2.xlsx",
    "thermo30": "Thermocouple TA 30C.xlsx",
    "thermo37": "Thermocouple TA 37C.xlsx",
    "wireless1": "Wireless Temperature Sensor 1.xlsx",
    "wireless2": "Wireless Temperature Sensor 2.xlsx",
}
ALLOWED_UPLOAD_EXT = {".xlsx", ".xls", ".csv"}
MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20MB

RESULT_FOLDERS = [
    "correlation_model_results",
    "thermocouple_identicool_results",
    "thermocouple_wireless_results",
    "thermocouple_relationship_comparison",
    "lagged_thermocouple_wireless_results",
    "exponential_thermal_model_results",
]


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PROJECT_ROOT), **kwargs)

    def log_message(self, fmt, *args):
        pass

    # ---- helpers ----------------------------------------------------
    def _send_json(self, obj, status=200):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _safe_path(self, rel_path, allowed_ext):
        """Resolve rel_path against the project root and make sure it can't
        escape the project directory or read a file of the wrong type."""
        if not rel_path:
            return None
        candidate = (PROJECT_ROOT / rel_path).resolve()
        if candidate.suffix.lower() != allowed_ext:
            return None
        try:
            candidate.relative_to(PROJECT_ROOT)
        except ValueError:
            return None
        if not candidate.is_file():
            return None
        return candidate

    def _read_json_body(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            return json.loads(raw or b"{}")
        except json.JSONDecodeError:
            return {}

    # ---- routing ------------------------------------------------------
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/dataset-status":
            return self._dataset_status()
        if parsed.path == "/api/csv":
            return self._get_csv(parsed)
        if parsed.path == "/api/text":
            return self._get_text(parsed)
        if parsed.path == "/api/results-index":
            return self._results_index()
        return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        payload = self._read_json_body()
        if parsed.path == "/api/run":
            return self._run_script(payload)
        if parsed.path == "/api/run-all":
            return self._run_all()
        if parsed.path == "/api/open-folder":
            return self._open_folder(payload)
        if parsed.path == "/api/upload":
            return self._upload(payload)
        self.send_response(404)
        self.end_headers()

    # ---- endpoints ------------------------------------------------------
    def _dataset_status(self):
        items = []
        for name in REQUIRED_FILES:
            p = SENSOR_DIR / name
            if p.exists():
                stat = p.stat()
                items.append(
                    {
                        "name": name,
                        "found": True,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
                    }
                )
            else:
                items.append({"name": name, "found": False, "modified": None})
        self._send_json({"files": items})

    def _get_csv(self, parsed):
        qs = urllib.parse.parse_qs(parsed.query)
        rel = qs.get("path", [""])[0]
        path = self._safe_path(rel, ".csv")
        if not path:
            return self._send_json({"error": "invalid path"}, 400)
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            columns = reader.fieldnames or []
        self._send_json({"columns": columns, "rows": rows})

    def _get_text(self, parsed):
        qs = urllib.parse.parse_qs(parsed.query)
        rel = qs.get("path", [""])[0]
        path = self._safe_path(rel, ".txt")
        if not path:
            return self._send_json({"error": "invalid path"}, 400)
        self._send_json({"text": path.read_text(encoding="utf-8")})

    def _results_index(self):
        index = {}
        for folder in RESULT_FOLDERS:
            folder_path = SENSOR_DIR / folder
            files = []
            if folder_path.exists():
                for f in sorted(folder_path.iterdir()):
                    if f.is_file():
                        files.append(
                            {
                                "name": f.name,
                                "relpath": str(f.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                                "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(timespec="seconds"),
                            }
                        )
            index[folder] = files
        self._send_json({"folders": index})

    def _run_script(self, payload):
        script = payload.get("script", "")
        if script not in SCRIPTS_IN_ORDER:
            return self._send_json({"error": "unknown script"}, 400)
        self._send_json(self._execute(script))

    def _run_all(self):
        results = []
        for script in SCRIPTS_IN_ORDER:
            result = self._execute(script)
            results.append(result)
            if not result["ok"] and script in (
                "analyze_thermocouple_identicool_correlations.py",
                "analyze_thermocouple_wireless_correlations.py",
            ):
                # compare_thermocouple_relationships.py needs both of these to
                # have succeeded — stop early rather than fail confusingly.
                break
        self._send_json({"results": results})

    def _execute(self, script):
        start = time.time()
        try:
            proc = subprocess.run(
                [sys.executable, script],
                cwd=str(SENSOR_DIR),
                capture_output=True,
                text=True,
                timeout=180,
            )
            return {
                "script": script,
                "ok": proc.returncode == 0,
                "returncode": proc.returncode,
                "stdout": proc.stdout[-4000:],
                "stderr": proc.stderr[-4000:],
                "duration": round(time.time() - start, 2),
            }
        except subprocess.TimeoutExpired:
            return {
                "script": script,
                "ok": False,
                "returncode": None,
                "stdout": "",
                "stderr": "Timed out after 180 seconds",
                "duration": round(time.time() - start, 2),
            }

    def _open_folder(self, payload):
        folder = payload.get("folder", "")
        if folder not in RESULT_FOLDERS:
            return self._send_json({"error": "unknown folder"}, 400)
        target = SENSOR_DIR / folder
        try:
            os.startfile(str(target))  # Windows only
            self._send_json({"ok": True})
        except Exception as exc:  # noqa: BLE001 - surface any OS error to the UI
            self._send_json({"ok": False, "error": str(exc)}, 500)

    def _upload(self, payload):
        """Accept a base64-encoded file for one sensor slot.

        .xlsx uploads go live immediately (replace the required workbook).
        .xls/.csv uploads are staged in _pending_uploads/ rather than replacing
        the live file, since converting them to the expected multi-sheet
        .xlsx layout isn't implemented yet — see the "coming soon" note in
        the upload modal.
        """
        slot = payload.get("slot", "")
        filename = payload.get("filename", "")
        data_b64 = payload.get("data", "")

        if slot not in UPLOAD_SLOTS:
            return self._send_json({"ok": False, "error": "Unknown sensor slot."}, 400)

        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_UPLOAD_EXT:
            return self._send_json({"ok": False, "error": "Only .xlsx, .xls, or .csv files are accepted."}, 400)

        try:
            raw = base64.b64decode(data_b64, validate=True)
        except (binascii.Error, ValueError):
            return self._send_json({"ok": False, "error": "Could not decode the uploaded file."}, 400)

        if not raw:
            return self._send_json({"ok": False, "error": "The uploaded file is empty."}, 400)
        if len(raw) > MAX_UPLOAD_BYTES:
            return self._send_json({"ok": False, "error": "File is larger than the 20MB limit."}, 400)

        target_name = UPLOAD_SLOTS[slot]
        if ext == ".xlsx":
            (SENSOR_DIR / target_name).write_bytes(raw)
            return self._send_json({"ok": True, "replaced": target_name, "note": None})

        pending_dir = SENSOR_DIR / "_pending_uploads"
        pending_dir.mkdir(exist_ok=True)
        staged_name = Path(target_name).stem + ext
        (pending_dir / staged_name).write_bytes(raw)
        return self._send_json(
            {
                "ok": True,
                "replaced": None,
                "note": (
                    f"Saved as _pending_uploads/{staged_name}. {ext} auto-conversion to the required "
                    ".xlsx layout isn't implemented yet — convert it manually and upload the .xlsx to "
                    "use it in the analysis."
                ),
            }
        )


def main():
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://127.0.0.1:{PORT}/dashboard/index.html"
    print(f"Temperature correlation dashboard running at {url}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
