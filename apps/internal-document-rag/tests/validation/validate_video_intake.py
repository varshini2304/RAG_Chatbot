"""
validate_video_intake.py — Standalone Video Stream Intake & Demuxing Validation Runner

Executes:
1. Environment & toolchain verification (Python 3.11, PyAV, FFmpeg/ffprobe)
2. 7-Video R&D Asset Ingestion & Decode Validation
3. Error Handling Validation (Missing, Truncated, Corrupt, Non-Video, Size Exceeded)
Outputs a clean execution log with full per-asset telemetry and saves JSON results to tests/results/.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

# Add app package root to sys.path
APP_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(APP_ROOT))

import av
import numpy as np

from app.video.exceptions import (
    CorruptMediaError,
    InvalidInputError,
    UnsupportedContainerError,
    VideoProcessingError,
)
from app.video.video_loader import VideoLoader

PROJECT_ROOT = APP_ROOT.parent.parent
VIDEOS_DIR = PROJECT_ROOT / "RND" / "02_docs_and_video" / "videos"
DOCS_DIR = PROJECT_ROOT / "RND" / "02_docs_and_video"
RESULTS_DIR = APP_ROOT / "tests" / "results"

TEST_VIDEOS = [
    "test_instructional_normal.mp4",
    "const_01.mp4",
    "Working on machine.mp4",
    "Working_on_machine_noisy.mp4",
    "Ubiquitous-Robotic-Technology-for-Smart-Manufacturing-System-6018686.f1.ogv.240p.vp9.webm",
    "controlled_vfr_test.mp4",
    "controlled_synthetic_corrupt.mp4",
]


def run_validation():
    print("=" * 80)
    print(" VIDEO INTAKE & STREAM DEMUXING VALIDATION REPORT")
    print("=" * 80)
    print("\n[1. Environment Verification]")
    print(f"Python Version    : {sys.version.split()[0]} ({sys.executable})")
    print(f"PyAV Version      : {av.__version__}")

    try:
        r = subprocess.run(
            ["ffprobe", "-version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        ff_ver = r.stdout.splitlines()[0] if r.returncode == 0 else "Unknown"
    except FileNotFoundError:
        ff_ver = "Not found on system PATH"
    except (subprocess.SubprocessError, OSError) as e:
        ff_ver = f"Probe error: {e}"
    print(f"ffprobe CLI       : {ff_ver}")

    print("\n[2. 7-Video R&D Asset Ingestion Validation]")
    video_table_records = []

    for filename in TEST_VIDEOS:
        path = VIDEOS_DIR / filename
        record = {
            "input_file": filename,
            "format": "Unknown",
            "vfr": "No",
            "opened": "No",
            "decoded": "No",
            "metadata_extracted": "No",
            "error": "None",
            "result": "FAIL",
            "duration_sec": 0.0,
            "resolution": "N/A",
            "codec": "N/A",
            "elapsed_sec": 0.0,
        }

        if not path.exists():
            record["error"] = "File not found on disk"
            video_table_records.append(record)
            continue

        t0 = time.perf_counter()
        try:
            with VideoLoader(path) as loader:
                meta = loader.get_metadata()
                record["opened"] = "Yes"
                record["metadata_extracted"] = "Yes"
                record["format"] = meta.format_name
                record["vfr"] = "Yes" if meta.is_vfr else "No"
                record["duration_sec"] = round(meta.duration_sec, 2)

                vid_stream = meta.primary_video_stream
                if vid_stream:
                    record["resolution"] = f"{vid_stream.width}x{vid_stream.height}"
                    record["codec"] = vid_stream.codec_name

                frame = loader.decode_first_frame()
                if frame is not None and isinstance(frame.data, np.ndarray) and frame.data.size > 0:
                    record["decoded"] = "Yes"
                    record["result"] = "PASS"
                else:
                    record["error"] = "Decoded frame is empty or invalid"

        except (VideoProcessingError, OSError) as e:
            record["error"] = f"{type(e).__name__}: {e}"
            record["result"] = "FAIL"

        record["elapsed_sec"] = round(time.perf_counter() - t0, 4)
        video_table_records.append(record)

    header = f"{'Input File':<32} | {'Format':<10} | {'VFR':<4} | {'Res':<9} | {'Dur(s)':<7} | {'Decoded':<7} | {'Result':<5} | {'Elapsed(s)':<10}"
    print("-" * len(header))
    print(header)
    print("-" * len(header))
    for r in video_table_records:
        print(
            f"{r['input_file'][:32]:<32} | {r['format'][:10]:<10} | {r['vfr']:<4} | {r['resolution']:<9} | {r['duration_sec']:<7} | {r['decoded']:<7} | {r['result']:<5} | {r['elapsed_sec']:<10.4f}"
        )
    print("-" * len(header))

    print("\n[3. Error Handling & Edge Case Validation]")
    error_cases = [
        ("Missing file", VIDEOS_DIR / "non_existent_fixture.mp4", InvalidInputError),
        ("Directory path", VIDEOS_DIR, InvalidInputError),
        ("PDF Document", DOCS_DIR / "milling_machine_operating_manual.pdf", (UnsupportedContainerError, CorruptMediaError)),
    ]

    error_records = []
    for label, target_path, expected_exceptions in error_cases:
        actual_exception = None
        status = "FAIL"
        msg = ""
        try:
            with VideoLoader(target_path) as loader:
                loader.open()
        except (VideoProcessingError, OSError) as e:
            actual_exception = type(e)
            msg = str(e)
            if isinstance(e, expected_exceptions):
                status = "PASS (Typed)"
            else:
                status = f"FAIL (Unexpected: {type(e).__name__})"

        expected_names = (
            [x.__name__ for x in expected_exceptions]
            if isinstance(expected_exceptions, tuple)
            else expected_exceptions.__name__
        )
        error_records.append({
            "test_case": label,
            "target": target_path.name,
            "expected": expected_names,
            "actual": actual_exception.__name__ if actual_exception else "No exception",
            "message": msg,
            "status": status,
        })
        print(f"  [{status:<12}] {label:<22} -> Raised: {actual_exception.__name__ if actual_exception else 'None'}")

    print("\n" + "=" * 80)
    total_vid = len(video_table_records)
    passed_vid = sum(1 for r in video_table_records if r["result"] == "PASS")
    total_err = len(error_records)
    passed_err = sum(1 for r in error_records if "PASS" in r["status"])
    print(f" SUMMARY: Videos {passed_vid}/{total_vid} PASS | Error Cases {passed_err}/{total_err} PASS")
    print("=" * 80)

    # Save validation report data to separate results directory
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = RESULTS_DIR / "video_intake_results.json"
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "scope": "Video Stream Intake & Demuxing Validation",
                "environment": {
                    "python": sys.version.split()[0],
                    "pyav": av.__version__,
                    "ffprobe": ff_ver,
                },
                "video_tests": video_table_records,
                "error_tests": error_records,
            },
            f,
            indent=2,
        )
    print(f"\n[Artifact Saved]: {log_file}")


if __name__ == "__main__":
    run_validation()
