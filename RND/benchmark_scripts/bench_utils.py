"""
bench_utils.py — Shared utilities for all 18 benchmark scripts.
Every script imports from this module for consistent traceability.
"""
import hashlib
import json
import os
import platform
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Reconfigure stdout/stderr for utf-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Register FFmpeg shared DLL directory for TorchCodec and PyAV
FFMPEG_SHARED_BIN = r"C:\Users\Admin\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Shared_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.1-full_build-shared\bin"
if os.path.isdir(FFMPEG_SHARED_BIN):
    if FFMPEG_SHARED_BIN not in os.environ.get("PATH", ""):
        os.environ["PATH"] = FFMPEG_SHARED_BIN + os.pathsep + os.environ.get("PATH", "")
    if hasattr(os, "add_dll_directory"):
        try:
            os.add_dll_directory(FFMPEG_SHARED_BIN)
        except Exception:
            pass

# Register MediaInfo directory on PATH
MEDIAINFO_BIN = r"C:\Users\Admin\AppData\Local\Microsoft\WinGet\Packages\MediaArea.MediaInfo_Microsoft.Winget.Source_8wekyb3d8bbwe"
if os.path.isdir(MEDIAINFO_BIN):
    if MEDIAINFO_BIN not in os.environ.get("PATH", ""):
        os.environ["PATH"] = MEDIAINFO_BIN + os.pathsep + os.environ.get("PATH", "")

# ── Paths ────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path("d:/company_projects/RAG_Chatbot")
VIDEOS_DIR   = PROJECT_ROOT / "RND/docs_and_video/videos"
if not VIDEOS_DIR.exists() or not any(VIDEOS_DIR.iterdir()):
    VIDEOS_DIR = PROJECT_ROOT / "rndreport/video_input_evaluation/videos"
RESULTS_BASE = PROJECT_ROOT / "RND/03_Evidence/all_test_results"
EVIDENCE_BASE = PROJECT_ROOT / "RND/03_Evidence"
ENV_FILE     = PROJECT_ROOT / "apps/internal-document-rag/.env"

# Load .env into os.environ (simple parse, no library needed)
def load_env(env_path: Path = ENV_FILE) -> None:
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                k = k.strip(); v = v.strip()
                if k and k not in os.environ:
                    os.environ[k] = v

load_env()

# ── SHA-256 ───────────────────────────────────────────────────────────────────
def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

# ── Timing ────────────────────────────────────────────────────────────────────
class Timer:
    def __init__(self):
        self._start = time.perf_counter()
        self.elapsed = 0.0
    def __enter__(self):
        self._start = time.perf_counter()
        return self
    def __exit__(self, *args):
        self.elapsed = round(time.perf_counter() - self._start, 4)

# ── Memory snapshot ───────────────────────────────────────────────────────────
def mem_mb() -> float:
    try:
        import psutil
        return round(psutil.Process(os.getpid()).memory_info().rss / 1024**2, 1)
    except ImportError:
        return -1.0

# ── Timestamp ─────────────────────────────────────────────────────────────────
def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()

# ── Environment fingerprint ───────────────────────────────────────────────────
def env_fingerprint() -> dict:
    return {
        "os": platform.platform(),
        "python_version": sys.version.split()[0],
        "python_executable": sys.executable,
        "cpu": platform.processor(),
        "timestamp_utc": utcnow(),
    }

# ── Save results ──────────────────────────────────────────────────────────────
# Secret redaction — applied at every sink (save_json/save_csv/save_log/TeeLogger)
# so no API key can reach disk or the console, regardless of how a call site
# captures an error. Covers: keys embedded in request URLs (?key=… / &key=…),
# provider-prefixed tokens anywhere (Google AQ./AIza, Groq gsk_, OpenAI sk-),
# x-goog-api-key headers, and the literal live values loaded from .env.
_URL_KEY_RE = re.compile(r'([?&](?:key|api_key)=)[^&\s\'"\\<>]+', re.IGNORECASE)
_HDR_KEY_RE = re.compile(r'(x-goog-api-key["\':\s]{1,4})[A-Za-z0-9_\-.]{12,}', re.IGNORECASE)
_TOKEN_RES = [
    re.compile(r'AQ\.[A-Za-z0-9_\-.]{20,}'),   # Google new-format API key
    re.compile(r'AIza[0-9A-Za-z_\-]{30,}'),     # Google legacy API key
    re.compile(r'gsk_[0-9A-Za-z]{20,}'),        # Groq
    re.compile(r'sk-[0-9A-Za-z_\-]{20,}'),      # OpenAI-style
    re.compile(r'xai-[0-9A-Za-z]{20,}'),        # xAI
]
_REDACTION = "REDACTED_API_KEY"

def _live_secret_values():
    vals = []
    for var in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GROQ_API_KEY", "OPENAI_API_KEY"):
        v = os.environ.get(var)
        if v and len(v) >= 12:
            vals.append(v)
    return vals

def redact(text):
    """Strip API keys from any string before it is written to disk/console."""
    if not isinstance(text, str):
        return text
    # 1) literal live key values (strongest guarantee, format-independent)
    for v in _live_secret_values():
        if v in text:
            text = text.replace(v, _REDACTION)
    # 2) keys carried in request URLs / headers (keep the param name, drop value)
    text = _URL_KEY_RE.sub(lambda m: m.group(1) + _REDACTION, text)
    text = _HDR_KEY_RE.sub(lambda m: m.group(1) + _REDACTION, text)
    # 3) any provider-prefixed token anywhere
    for pat in _TOKEN_RES:
        text = pat.sub(_REDACTION, text)
    return text

def json_default(obj):
    if hasattr(obj, "item"):
        return obj.item()
    if hasattr(obj, "tolist"):
        return obj.tolist()
    if isinstance(obj, (bool, )):
        return bool(obj)
    return str(obj)

def save_json(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, indent=2, ensure_ascii=False, default=json_default)
    with open(path, "w", encoding="utf-8") as f:
        f.write(redact(payload))
    print(f"  [SAVED] {path}")

def save_csv(rows: list[dict], path: Path) -> None:
    import csv
    import io
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
    with open(path, "w", newline="", encoding="utf-8") as f:
        f.write(redact(buf.getvalue()))
    print(f"  [SAVED] {path}")

def save_log(content: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(redact(content))
    print(f"  [SAVED] {path}")

# ── Tee Logger for Automated Terminal Logging ─────────────────────────────────
class TeeLogger:
    def __init__(self, log_path: Path):
        self.terminal = sys.stdout
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.file = open(log_path, "w", encoding="utf-8", errors="replace")

    def write(self, message):
        message = redact(message)
        try:
            self.terminal.write(message)
        except Exception:
            try:
                clean_msg = message.replace("✓", "[PASS]").replace("✗", "[FAIL]").replace("~", "[PARTIAL]").replace("?", "[INFO]")
                self.terminal.write(clean_msg)
            except Exception:
                pass
        try:
            self.file.write(message)
            self.file.flush()
        except Exception:
            pass

    def flush(self):
        try: self.terminal.flush()
        except Exception: pass
        try: self.file.flush()
        except Exception: pass

# ── Status labels ─────────────────────────────────────────────────────────────
STATUS_PASS     = "PASS — REAL TESTED"
STATUS_PARTIAL  = "PARTIAL"
STATUS_FAIL     = "FAIL — REAL TESTED"
STATUS_NOT_TESTED = "NOT TESTED"
STATUS_RESEARCH = "PASS — RESEARCH SUPPORTED"

ROW_LOG_NAMES = {
    1: "ROW_01_Video_Input___Ingestion.log",
    2: "ROW_02_Video_Validation___Metadata.log",
    3: "ROW_03_Audio_Extraction___Resampling.log",
    4: "ROW_04_Visual_Processing___Frame_Seeking.log",
    5: "ROW_05_Speech_Transcription__faster_whisper_.log",
    6: "ROW_06_Timestamp_Alignment.log",
    7: "ROW_07_Work_Step_Identification.log",
    8: "ROW_08_Keyframe_Selection.log",
    9: "ROW_09_Visual_Information___Tool_ID.log",
    10: "ROW_10_Safety___Checkpoint_Detection.log",
    11: "ROW_11_OCR_Text___Gauge_Extraction.log",
    12: "ROW_12_Document_Ingestion_Pipeline.log",
    13: "ROW_13_Chunking___Vector_Retrieval.log",
    14: "ROW_14_Hybrid_Retrieval___RRF_Fusion.log",
    15: "ROW_15_Cross_Source_Conflict_Detection.log",
    16: "ROW_16_Human_Conflict_Resolution.log",
    17: "ROW_17_Bilingual_SOP_Generation.log",
    18: "ROW_18_Visual_SOP_Data_Contract.log",
}

# ── Print header & Auto-logger ────────────────────────────────────────────────
def print_header(row: int, name: str, out_dir: Path = None) -> None:
    if out_dir is not None:
        log_name = ROW_LOG_NAMES.get(row, f"ROW_{row:02d}_benchmark.log")
        log_file = out_dir / log_name
        sys.stdout = TeeLogger(log_file)
    sep = "=" * 70
    print(f"\n{sep}")
    print(f"  ROW {row:02d} — {name}")
    print(f"  Started: {utcnow()}")
    print(f"  Environment: {sys.executable} (Python {platform.python_version()})")
    print(sep)
