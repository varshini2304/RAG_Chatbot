"""
tests/validation/validate_audio_extraction.py — Standalone Validation Runner for Audio Extraction & Duration Sync

Executes audio extraction, resampling, EBU R128 loudness normalization, silence trimming,
and source-duration synchronization across all real repository fixtures.
Generates machine-readable telemetry artifacts at:
- tests/day4_audio_validation_results.json
- tests/results/audio_validation_results.json
"""

from __future__ import annotations

import json
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

# Ensure project root is in sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
APP_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(APP_ROOT))

# Ensure UTF-8 output encoding for console
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from app.audio.audio_extractor import AudioExtractor
from app.audio.exceptions import NoAudioStreamError
from app.video.exceptions import (
    CorruptMediaError,
    InvalidInputError,
    VideoProcessingError,
)
from app.video.video_loader import extract_metadata_ffprobe

VIDEOS_DIR = APP_ROOT.parent.parent / "RND" / "02_docs_and_video" / "videos"
DOCS_DIR = APP_ROOT.parent.parent / "RND" / "02_docs_and_video"
RESULTS_DIR = SCRIPT_DIR.parent / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class BoundaryTestCase:
    """Descriptor for controlled tolerance boundary unit evaluations."""

    name: str
    source_dur: float
    audio_dur: float
    expected: bool


def run_boundary_tests() -> list[dict[str, Any]]:
    """
    Executes explicit tolerance boundary evaluations using controlled mathematical inputs.
    Clearly labeled as unit boundary checks to verify the +/-2.0s boundary logic.
    """
    boundary_cases: list[BoundaryTestCase] = [
        BoundaryTestCase("exact_positive_boundary", 100.0, 102.0, True),
        BoundaryTestCase("exact_negative_boundary", 100.0, 98.0, True),
        BoundaryTestCase("exceeding_positive_boundary", 100.0, 102.001, False),
        BoundaryTestCase("exceeding_negative_boundary", 100.0, 97.999, False),
    ]
    results = []
    for c in boundary_cases:
        res = AudioExtractor.calculate_duration_sync(c.source_dur, c.audio_dur, tolerance_sec=2.0)
        passed_test = (res.is_within_tolerance == c.expected)
        results.append({
            "test_case": c.name,
            "type": "controlled_boundary_unit_check",
            "source_duration_sec": c.source_dur,
            "audio_duration_sec": c.audio_dur,
            "delta_sec": res.duration_difference_sec,
            "tolerance_sec": 2.0,
            "is_within_tolerance": res.is_within_tolerance,
            "expected_within_tolerance": c.expected,
            "test_passed": passed_test,
        })
    return results


def validate_fixtures() -> dict[str, Any]:
    """Runs complete audio extraction and duration sync validation against media fixtures."""
    extractor = AudioExtractor()

    # Discover video fixtures
    fixture_files = sorted([
        f for f in VIDEOS_DIR.iterdir()
        if f.suffix.lower() in (".mp4", ".webm", ".ogv")
    ])

    fixture_records: list[dict[str, Any]] = []

    print("=" * 90)
    print("DAY 4 / STEP 3: AUDIO EXTRACTION & DURATION SYNCHRONIZATION VALIDATION")
    print("=" * 90)
    print(f"Discovered {len(fixture_files)} media fixtures in {VIDEOS_DIR}")
    print("-" * 90)

    for vp in fixture_files:
        print(f"\nEvaluating: {vp.name}")
        t_start = time.perf_counter()

        # Step 1: Probe source metadata via FFprobe
        try:
            source_meta = extract_metadata_ffprobe(vp)
            has_audio_stream = bool(source_meta.audio_codec)
            source_dur = round(source_meta.duration_sec, 4)
            source_codec = source_meta.audio_codec or "none"
        except Exception as e:  # noqa: BLE001
            source_meta = None
            has_audio_stream = False
            source_dur = 0.0
            source_codec = "error"
            print(f"  [!] FFprobe probe error: {e}")

        # Step 2: Extract audio with Loudnorm (baseline)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            out_wav = Path(tmp.name)

        record: dict[str, Any] = {
            "filename": vp.name,
            "file_size_bytes": vp.stat().st_size,
            "has_audio_stream": has_audio_stream,
            "source_audio_codec": source_codec,
            "source_duration_sec": source_dur,
            "audio_extracted": False,
            "sample_rate": None,
            "channels": None,
            "sample_format": "s16 (pcm_s16le)",
            "output_duration_sec": None,
            "raw_duration_sec": None,
            "raw_duration_delta_sec": None,
            "tolerance_sec": 2.0,
            "duration_sync_passed": None,
            "silence_trimming_enabled": False,
            "trimmed_duration_sec": None,
            "silence_trim_delta_sec": None,
            "loudness_measurement": None,
            "execution_time_sec": 0.0,
            "error_type": None,
            "error_message": None,
        }

        try:
            res = extractor.extract_to_file(vp, output_path=out_wav, enable_loudnorm=True)
            record["audio_extracted"] = True
            record["sample_rate"] = res.sample_rate
            record["channels"] = res.channels
            record["output_duration_sec"] = res.duration_sec
            record["raw_duration_sec"] = res.raw_duration_sec
            record["execution_time_sec"] = res.extraction_time_sec

            if res.duration_sync:
                record["raw_duration_delta_sec"] = res.duration_sync.duration_difference_sec
                record["duration_sync_passed"] = res.duration_sync.is_within_tolerance

            if res.loudness_measurement:
                record["loudness_measurement"] = asdict(res.loudness_measurement)

            sync_status = "PASS" if record["duration_sync_passed"] else "FAIL"
            delta_str = f"{record['raw_duration_delta_sec']:+.4f}s" if record['raw_duration_delta_sec'] is not None else "N/A"
            print(f"  [✓] Extracted: {res.duration_sec:.3f}s | Delta: {delta_str} | Sync: {sync_status} ({res.extraction_time_sec:.2f}s)")
            if res.loudness_measurement:
                print(f"      Loudness: I={res.loudness_measurement.input_i:.1f} -> {res.loudness_measurement.output_i:.1f} LUFS | TP={res.loudness_measurement.output_tp:.1f} dBTP")

        except Exception as e:  # noqa: BLE001
            record["error_type"] = type(e).__name__
            record["error_message"] = str(e)
            record["duration_sync_passed"] = False
            print(f"  [✗] Extraction Failed: {type(e).__name__}: {e}")
        finally:
            if out_wav.exists():
                out_wav.unlink()

        # Step 3: Test silence trimming on this fixture to record trimmed duration
        if record["audio_extracted"]:
            with tempfile.NamedTemporaryFile(suffix="_trimmed.wav", delete=False) as tmp_trim:
                out_trimmed = Path(tmp_trim.name)
            try:
                res_trim = extractor.extract_to_file(vp, output_path=out_trimmed, enable_silence_trimming=True)
                record["silence_trimming_enabled"] = True
                record["trimmed_duration_sec"] = res_trim.trimmed_duration_sec
                if res_trim.trimmed_duration_sec is not None and record["raw_duration_sec"] is not None:
                    trim_delta = round(res_trim.trimmed_duration_sec - record["raw_duration_sec"], 4)
                    record["silence_trim_delta_sec"] = trim_delta
                    print(f"      Silence Trimming: {res_trim.trimmed_duration_sec:.3f}s (delta: {trim_delta:+.3f}s)")
            except Exception as e:  # noqa: BLE001
                print(f"      [!] Silence trimming sub-test failed: {e}")
            finally:
                if out_trimmed.exists():
                    out_trimmed.unlink()

        record["total_elapsed_sec"] = round(time.perf_counter() - t_start, 4)
        fixture_records.append(record)

    # Step 4: Test non-video fixture rejection (PDF document)
    pdf_fixture = DOCS_DIR / "milling_machine_operating_manual.pdf"
    if pdf_fixture.exists():
        print(f"\nEvaluating Non-Video Fixture: {pdf_fixture.name}")
        pdf_record: dict[str, Any] = {
            "filename": pdf_fixture.name,
            "file_size_bytes": pdf_fixture.stat().st_size,
            "has_audio_stream": False,
            "source_audio_codec": "none",
            "source_duration_sec": 0.0,
            "audio_extracted": False,
            "tolerance_sec": 2.0,
            "duration_sync_passed": None,
            "error_type": None,
            "error_message": None,
            "correctly_rejected": False,
        }
        try:
            extractor.extract_to_file(pdf_fixture)
            pdf_record["correctly_rejected"] = False
            print("  [✗] False acceptance: PDF was not rejected!")
        except (NoAudioStreamError, CorruptMediaError, VideoProcessingError, InvalidInputError) as e:
            pdf_record["correctly_rejected"] = True
            pdf_record["error_type"] = type(e).__name__
            pdf_record["error_message"] = str(e)
            print(f"  [✓] Correctly Rejected: {type(e).__name__}")
        fixture_records.append(pdf_record)

    # Boundary test execution
    boundary_results = run_boundary_tests()

    # Dynamic metrics calculation
    valid_fixtures = [r for r in fixture_records if r.get("has_audio_stream") and r["filename"] != "controlled_synthetic_corrupt.mp4"]
    corrupt_fixtures = [r for r in fixture_records if r["filename"] == "controlled_synthetic_corrupt.mp4" or not r.get("has_audio_stream")]

    total_valid = len(valid_fixtures)
    valid_sync_passed = sum(1 for r in valid_fixtures if r.get("duration_sync_passed") is True)
    false_rejections = total_valid - valid_sync_passed

    total_invalid = len(corrupt_fixtures)
    # A false acceptance on invalid fixture is if duration_sync_passed is True or invalid file accepted
    false_acceptances = sum(
        1 for r in corrupt_fixtures
        if r.get("duration_sync_passed") is True or (r.get("correctly_rejected") is False)
    )

    loudnorm_successes = sum(1 for r in fixture_records if r.get("loudness_measurement") is not None)

    counts: dict[str, Any] = {
        "total_fixtures_evaluated": len(fixture_records),
        "valid_media_fixtures": total_valid,
        "valid_sync_passed": valid_sync_passed,
        "valid_sync_pass_rate_pct": round((valid_sync_passed / total_valid) * 100, 2) if total_valid > 0 else 0.0,
        "false_rejections": false_rejections,
        "false_rejection_rate_pct": round((false_rejections / total_valid) * 100, 2) if total_valid > 0 else 0.0,
        "invalid_or_corrupt_fixtures": total_invalid,
        "false_acceptances": false_acceptances,
        "false_acceptance_rate_pct": round((false_acceptances / total_invalid) * 100, 2) if total_invalid > 0 else 0.0,
        "loudnorm_diagnostics_captured": loudnorm_successes,
        "controlled_boundary_tests_run": len(boundary_results),
        "controlled_boundary_tests_passed": sum(1 for b in boundary_results if b["test_passed"]),
    }

    summary: dict[str, Any] = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "tolerance_sec": 2.0,
        "authoritative_row03_tolerance": "+/-2.0s",
        "implementation_baseline_ebu_r128": {
            "target_i_lufs": -23.0,
            "lra_lu": 7.0,
            "tp_dbtp": -2.0,
            "status": "implementation_baseline (not R&D-validated)",
        },
        "implementation_baseline_silence_trimming": {
            "threshold_db": -50.0,
            "duration_sec": 0.2,
            "default_enabled": False,
            "status": "implementation_baseline (not R&D-validated)",
        },
        "counts": counts,
        "boundary_evaluations": boundary_results,
        "fixture_records": fixture_records,
    }

    print("\n" + "=" * 90)
    print("VALIDATION SUMMARY REPORT")
    print("=" * 90)
    print(f"Total Fixtures Evaluated:           {counts['total_fixtures_evaluated']}")
    print(f"Valid Media Fixtures:               {counts['valid_media_fixtures']}")
    print(f"Valid Duration Sync Passed (<=2s):  {counts['valid_sync_passed']} / {total_valid} ({counts['valid_sync_pass_rate_pct']}%)")
    print(f"False Rejections:                   {counts['false_rejections']}")
    print(f"False Acceptances:                  {counts['false_acceptances']}")
    print(f"Loudnorm JSON Telemetry Captured:   {counts['loudnorm_diagnostics_captured']}")
    print(f"Boundary Unit Tests Passed:         {counts['controlled_boundary_tests_passed']} / {len(boundary_results)}")
    print("=" * 90)

    # Save artifacts to both paths
    primary_artifact = RESULTS_DIR / "audio_validation_results.json"
    day4_artifact = SCRIPT_DIR.parent / "day4_audio_validation_results.json"

    with open(primary_artifact, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"Saved primary artifact to: {primary_artifact}")

    with open(day4_artifact, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"Saved day4 artifact to:    {day4_artifact}")

    return summary


if __name__ == "__main__":
    validate_fixtures()
