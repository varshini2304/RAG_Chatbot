"""
run_all_benchmarks.py — Master runner for all 18 row benchmarks.
Executes each row benchmark sequentially, updates all JSON/CSV evidence,
and writes comprehensive execution logs to each respective row folder in RND/03_Evidence/all_test_results.
"""
import subprocess, sys, time, os
from pathlib import Path
from datetime import datetime, timezone

# Ensure UTF-8 execution across Windows terminals
os.environ["PYTHONIOENCODING"] = "utf-8"
if hasattr(sys.stdout, "reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
if hasattr(sys.stderr, "reconfigure"):
    try: sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

PYTHON = sys.executable
SCRIPT_DIR = Path(__file__).parent
EVIDENCE_DIR = Path(r"d:\company_projects\RAG_Chatbot\RND\03_Evidence\all_test_results")

ROW_CONFIG = [
    ("01", SCRIPT_DIR / "row_01_video_input.py",           "01_video_input",               "ROW_01_Video_Input___Ingestion.log",          "Video Input & Ingestion"),
    ("02", SCRIPT_DIR / "row_02_video_validation.py",       "02_video_validation",          "ROW_02_Video_Validation___Metadata.log",       "Video Validation & Metadata"),
    ("03", SCRIPT_DIR / "row_03_audio_extraction.py",       "03_audio_processing",          "ROW_03_Audio_Extraction___Resampling.log",    "Audio Extraction & Resampling"),
    ("04", SCRIPT_DIR / "row_04_frame_seeking.py",          "04_visual_processing",         "ROW_04_Visual_Processing___Frame_Seeking.log", "Visual Processing / Frame Seeking"),
    ("05", SCRIPT_DIR / "row_05_speech_transcription.py",   "05_speech_transcription",      "ROW_05_Speech_Transcription__faster_whisper_.log", "Speech Transcription"),
    ("06", SCRIPT_DIR / "row_06_timestamp_alignment.py",    "06_transcript_alignment",      "ROW_06_Timestamp_Alignment.log",              "Timestamp Alignment"),
    ("07", SCRIPT_DIR / "row_07_work_step.py",              "07_work_step",                 "ROW_07_Work_Step_Identification.log",          "Work-Step Identification"),
    ("08", SCRIPT_DIR / "row_08_keyframe_selection.py",     "08_keyframe_selection",        "ROW_08_Keyframe_Selection.log",               "Keyframe Selection"),
    ("09", SCRIPT_DIR / "row_09_visual_information.py",     "09_visual_information",        "ROW_09_Visual_Information___Tool_ID.log",      "Visual Information & Tool ID"),
    ("10", SCRIPT_DIR / "row_10_safety_detection.py",       "10_safety_detection",          "ROW_10_Safety___Checkpoint_Detection.log",      "Safety & Checkpoint Detection"),
    ("11", SCRIPT_DIR / "row_11_ocr.py",                    "11_ocr",                       "ROW_11_OCR_Text___Gauge_Extraction.log",      "OCR Text & Label Extraction"),
    ("12", SCRIPT_DIR / "rows_12_to_18.py",                 "12_document_ingestion",        "ROW_12_Document_Ingestion_Pipeline.log",       "Document Ingestion Pipeline"),
    ("13", SCRIPT_DIR / "rows_12_to_18.py",                 "13_embedding_retrieval",       "ROW_13_Chunking___Vector_Retrieval.log",       "Chunking & Vector Retrieval"),
    ("14", SCRIPT_DIR / "rows_12_to_18.py",                 "14_hybrid_retrieval",          "ROW_14_Hybrid_Retrieval___RRF_Fusion.log",     "Hybrid Retrieval & RRF Fusion"),
    ("15", SCRIPT_DIR / "rows_12_to_18.py",                 "15_conflict_detection",        "ROW_15_Cross_Source_Conflict_Detection.log",   "Cross-Source Conflict Detection"),
    ("16", SCRIPT_DIR / "rows_12_to_18.py",                 "16_human_conflict_resolution", "ROW_16_Human_Conflict_Confirmation.log",       "Human Conflict Confirmation"),
    ("17", SCRIPT_DIR / "rows_12_to_18.py",                 "17_bilingual_generation",      "ROW_17_Bilingual_SOP_Generation.log",          "Bilingual Work Instruction Gen"),
    ("18", SCRIPT_DIR / "rows_12_to_18.py",                 "18_visual_sop",                "ROW_18_Visual_SOP_Data_Contract.log",          "Visual SOP Generation"),
]

TIMEOUT = {
    "01": 180, "02": 120, "03": 300, "04": 240, "05": 900,
    "06": 400, "07": 180, "08": 180, "09": 300, "10": 180,
    "11": 600, "12": 180, "13": 600, "14": 600, "15": 120,
    "16": 60,  "17": 120, "18": 120,
}

def safe_print(text: str):
    try:
        sys.stdout.write(text + "\n")
        sys.stdout.flush()
    except Exception:
        try:
            ascii_text = text.replace("✓", "[PASS]").replace("✗", "[FAIL]").replace("~", "[PARTIAL]").replace("?", "[INFO]")
            sys.stdout.write(ascii_text + "\n")
            sys.stdout.flush()
        except Exception:
            pass

def run_row(row_num: str, script: Path, folder_name: str, log_name: str, display_name: str) -> bool:
    target_dir = EVIDENCE_DIR / folder_name
    target_dir.mkdir(parents=True, exist_ok=True)
    canonical_log = target_dir / log_name
    generic_log = target_dir / f"ROW_{row_num}_benchmark.log"
    
    args = [PYTHON, str(script)]
    if script.name == "rows_12_to_18.py":
        args.append(row_num)
        
    timeout = TIMEOUT.get(row_num, 180)
    start = time.perf_counter()
    safe_print(f"\n{'='*70}")
    safe_print(f"  ROW {row_num} — {display_name}")
    safe_print(f"  Script: {script.name}")
    safe_print(f"  Target: {target_dir}")
    safe_print(f"  Log:    {canonical_log.name}")
    safe_print(f"{'='*70}")
    
    try:
        result = subprocess.run(
            args, capture_output=True, text=True,
            timeout=timeout, encoding="utf-8", errors="replace",
            cwd=str(SCRIPT_DIR.parent)
        )
        elapsed = round(time.perf_counter() - start, 2)
        output = result.stdout + ("\n--- STDERR ---\n" + result.stderr if result.stderr.strip() else "")
        
        # Write exclusively to canonical descriptive log
        log_header = f"======================================================================\nLOG: ROW_{row_num} - {display_name}\nExecuted: {datetime.now(timezone.utc).isoformat()}\nInterpreter: {PYTHON}\nElapsed: {elapsed}s\nReturnCode: {result.returncode}\n======================================================================\n\n"
        canonical_log.write_text(log_header + output, encoding="utf-8", errors="replace")
        
        # Remove generic duplicate if present
        if generic_log.exists():
            try: generic_log.unlink()
            except Exception: pass
            
        safe_print(output)
        
        if result.returncode == 0:
            safe_print(f"  [PASS] COMPLETED in {elapsed}s")
            return True
        else:
            safe_print(f"  [FAIL] (rc={result.returncode}) in {elapsed}s")
            return False
    except subprocess.TimeoutExpired:
        elapsed = round(time.perf_counter() - start, 2)
        safe_print(f"  [!] TIMEOUT after {elapsed}s")
        timeout_msg = f"ROW {row_num} TIMEOUT after {elapsed}s"
        canonical_log.write_text(timeout_msg, encoding="utf-8", errors="replace")
        return False
    except Exception as e:
        safe_print(f"  [!] ERROR: {e}")
        return False

def main():
    target_rows = sys.argv[1:] if len(sys.argv) > 1 else None
    safe_print(f"\n{'#'*70}")
    safe_print(f"  MASTER 18-ROW BENCHMARK RUNNER")
    safe_print(f"  Started: {datetime.now(timezone.utc).isoformat()}")
    safe_print(f"  Python:  {PYTHON}")
    safe_print(f"{'#'*70}")
    
    summary = []
    for row_num, script, folder, log_file, name in ROW_CONFIG:
        if target_rows and row_num not in target_rows:
            continue
        ok = run_row(row_num, script, folder, log_file, name)
        summary.append({"row": row_num, "name": name, "status": "PASS" if ok else "FAIL"})
        
    safe_print(f"\n\n{'='*70}")
    safe_print("  EXECUTION SUMMARY ACROSS ALL ROWS")
    safe_print(f"{'='*70}")
    passed = sum(1 for s in summary if s["status"] == "PASS")
    for s in summary:
        icon = "[PASS]" if s["status"] == "PASS" else "[FAIL]"
        safe_print(f"  {icon} ROW {s['row']:>2s} — {s['name']}")
    safe_print(f"\nTotal: {passed}/{len(summary)} rows executed successfully.")

if __name__ == "__main__":
    main()
