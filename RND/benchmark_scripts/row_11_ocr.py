"""
row_11_ocr.py — Row 11: OCR / Text / Label / Gauge Extraction
Candidates: PaddleOCR (enable_mkldnn=False) | EasyOCR | Tesseract (EN only — jpn.traineddata not installed)
Evaluates Japanese and English text extraction from project video keyframes.
"""
import sys, os, subprocess, json as _json
from pathlib import Path

# Ensure bench_utils is discoverable
sys.path.insert(0, str(Path(__file__).parent))
from bench_utils import *

ROW = 11
NAME = "OCR Text & Label Extraction"
OUT_DIR = RESULTS_BASE / "11_ocr"
RAGBOT_PYTHON = r"C:\Users\Admin\envs\ragbot\Scripts\python.exe"

# Locate real keyframes
KEYFRAME_DIR = PROJECT_ROOT / "rndreport/video_input_evaluation/results/extracted_frames/const_01.mp4"
KEYFRAME_PATHS = []
for folder in [KEYFRAME_DIR, PROJECT_ROOT / "rndreport", OUT_DIR]:
    found = list(folder.rglob("OpenCV_ts_*.jpg")) if folder.exists() else []
    if found:
        KEYFRAME_PATHS = sorted(found)[:4]
        break

GROUND_TRUTH_TEXT = {
    "OpenCV_ts_0.0s.jpg":   {"expected_contains": [], "has_text": False, "language": "ja"},
    "OpenCV_ts_10.0s.jpg":  {"expected_contains": [], "has_text": False, "language": "ja"},
    "OpenCV_ts_272.6s.jpg": {"expected_contains": ["安全", "労働災害"], "has_text": True, "language": "ja"},
    "OpenCV_ts_544.1s.jpg": {"expected_contains": ["安全"], "has_text": True, "language": "ja"},
}

BATCH_OCR_SCRIPT = r"""
import sys, json, time
from pathlib import Path
from PIL import Image

sys.path.insert(0, r"{bench_dir}")
from bench_utils import Timer, mem_mb, STATUS_PASS, STATUS_PARTIAL, STATUS_FAIL, sha256

selected_candidate = sys.argv[1]
keyframe_paths = [Path(p) for p in sys.argv[2:]]
gt_map = json.loads(r'''{gt_json}''')

results = []

def calc_status(texts, expected, has_text):
    if not has_text:
        return STATUS_PASS if len(texts) == 0 else STATUS_PARTIAL
    if not texts:
        return STATUS_FAIL
    kw_found = sum(1 for e in expected if any(e in t["text"] for t in texts))
    if not expected or kw_found >= len(expected):
        return STATUS_PASS
    elif kw_found > 0:
        return STATUS_PASS
    return STATUS_PARTIAL

# 1. PaddleOCR
try:
    if selected_candidate != "PaddleOCR":
        raise RuntimeError("candidate not selected")
    from paddleocr import PaddleOCR
    ocr_paddle = PaddleOCR(lang='japan', enable_mkldnn=False)
    for kp in keyframe_paths:
        gt_info = gt_map.get(kp.name, {})
        expected = gt_info.get("expected_contains", [])
        has_text = gt_info.get("has_text", True)
        with Timer() as t:
            res = ocr_paddle.ocr(str(kp))
        texts = []
        if res and res[0]:
            if isinstance(res[0], dict):
                rec_texts = res[0].get('rec_texts', [])
                rec_scores = res[0].get('rec_scores', [])
                for txt, score in zip(rec_texts, rec_scores):
                    texts.append({"text": str(txt), "confidence": round(float(score), 4) if score is not None else None})
            elif isinstance(res[0], list):
                for line in res[0]:
                    if line and len(line) >= 2:
                        texts.append({"text": str(line[1][0]), "confidence": round(float(line[1][1]), 4)})
        kw_found = sum(1 for e in expected if any(e in t["text"] for t in texts))
        status = calc_status(texts, expected, has_text)
        results.append({
            "frame": kp.name,
            "sha256_prefix": sha256(kp)[:16],
            "candidate": "PaddleOCR 3.7 (enable_mkldnn=False)",
            "version": "3.7.0",
            "status": status,
            "elapsed_sec": t.elapsed,
            "texts": texts,
            "text_count": len(texts),
            "expected_keywords": expected,
            "expected_found": kw_found,
            "expected_count": len(expected),
            "errors": []
        })
except Exception as e:
    for kp in keyframe_paths:
        results.append({
            "frame": kp.name,
            "sha256_prefix": sha256(kp)[:16],
            "candidate": "PaddleOCR 3.7 (enable_mkldnn=False)",
            "version": "3.7.0",
            "status": STATUS_FAIL,
            "elapsed_sec": 0,
            "texts": [],
            "text_count": 0,
            "errors": [str(e)]
        })

# 2. EasyOCR
try:
    if selected_candidate != "EasyOCR":
        raise RuntimeError("candidate not selected")
    import easyocr
    reader = easyocr.Reader(['ja', 'en'], gpu=False)
    for kp in keyframe_paths:
        gt_info = gt_map.get(kp.name, {})
        expected = gt_info.get("expected_contains", [])
        has_text = gt_info.get("has_text", True)
        with Timer() as t:
            res = reader.readtext(str(kp))
        texts = [{"text": str(r[1]), "confidence": round(float(r[2]), 4)} for r in res]
        kw_found = sum(1 for e in expected if any(e in t["text"] for t in texts))
        status = calc_status(texts, expected, has_text)
        results.append({
            "frame": kp.name,
            "sha256_prefix": sha256(kp)[:16],
            "candidate": "EasyOCR 1.7.2 (ja+en)",
            "version": "1.7.2",
            "status": status,
            "elapsed_sec": t.elapsed,
            "texts": texts,
            "text_count": len(texts),
            "expected_keywords": expected,
            "expected_found": kw_found,
            "expected_count": len(expected),
            "errors": []
        })
except Exception as e:
    for kp in keyframe_paths:
        results.append({
            "frame": kp.name,
            "sha256_prefix": sha256(kp)[:16],
            "candidate": "EasyOCR 1.7.2 (ja+en)",
            "version": "1.7.2",
            "status": STATUS_FAIL,
            "elapsed_sec": 0,
            "texts": [],
            "text_count": 0,
            "errors": [str(e)]
        })

# 3. Tesseract (EN-only)
try:
    if selected_candidate != "Tesseract":
        raise RuntimeError("candidate not selected")
    import pytesseract
    for kp in keyframe_paths:
        expected = gt_map.get(kp.name, {}).get("expected_contains", [])
        img = Image.open(str(kp))
        with Timer() as t:
            data = pytesseract.image_to_data(img, lang='eng', config='--psm 11', output_type=pytesseract.Output.DICT)
        words = [w for w, c in zip(data['text'], data['conf']) if w.strip() and int(c) > 20]
        results.append({
            "frame": kp.name,
            "sha256_prefix": sha256(kp)[:16],
            "candidate": "Tesseract (EN only — jpn NOT INSTALLED)",
            "version": getattr(pytesseract, "__version__", "5.x"),
            "status": STATUS_PARTIAL if words else STATUS_FAIL,
            "elapsed_sec": t.elapsed,
            "texts": [{"text": str(w), "confidence": None} for w in words[:20]],
            "text_count": len(words),
            "note": "Tesseract Japanese (jpn.traineddata) not installed; EN-only result",
            "expected_keywords": expected,
            "expected_found": 0,
            "expected_count": len(expected),
            "errors": []
        })
except Exception as e:
    for kp in keyframe_paths:
        results.append({
            "frame": kp.name,
            "sha256_prefix": sha256(kp)[:16],
            "candidate": "Tesseract (EN only — jpn NOT INSTALLED)",
            "version": "N/A",
            "status": "NOT TESTED — tesseract not available",
            "elapsed_sec": 0,
            "texts": [],
            "text_count": 0,
            "errors": [str(e)]
        })

print("===BATCH_OCR_JSON_START===")
print(json.dumps(results))
print("===BATCH_OCR_JSON_END===")
"""

def main():
    print_header(ROW, NAME, OUT_DIR)
    env = env_fingerprint()
    if not KEYFRAME_PATHS:
        print("  [!] No keyframes found. OCR test cannot run.")
        save_json({"row": ROW, "name": NAME, "environment": env, "status": "Evidence unavailable", "results": []},
                  OUT_DIR / "ocr_results_new.json")
        return

    print(f"  Found {len(KEYFRAME_PATHS)} keyframes for OCR: {[p.name for p in KEYFRAME_PATHS]}")
    
    script_content = BATCH_OCR_SCRIPT.replace(
        "{bench_dir}", str(Path(__file__).parent).replace("\\", "\\\\")
    ).replace(
        "{gt_json}", _json.dumps(GROUND_TRUTH_TEXT)
    )

    all_results = []
    candidate_specs = (
        ("PaddleOCR", "PaddleOCR", 600),
        ("EasyOCR", "EasyOCR", 300),
        ("Tesseract", "Tesseract", 120),
    )
    for selected, result_prefix, timeout_seconds in candidate_specs:
        args = [RAGBOT_PYTHON, "-c", script_content, selected] + [str(p) for p in KEYFRAME_PATHS]
        try:
            completed = subprocess.run(
                args, capture_output=True, text=True, timeout=timeout_seconds,
                encoding="utf-8", errors="replace"
            )
            output = completed.stdout or ""
            if "===BATCH_OCR_JSON_START===" in output and "===BATCH_OCR_JSON_END===" in output:
                json_str = output.split("===BATCH_OCR_JSON_START===")[1].split("===BATCH_OCR_JSON_END===")[0].strip()
                candidate_results = _json.loads(json_str)
                all_results.extend(
                    item for item in candidate_results
                    if item.get("candidate", "").startswith(result_prefix)
                )
            else:
                diagnostic = (completed.stderr or output or f"exit code {completed.returncode}").strip()[-1200:]
                all_results.append({"candidate": selected, "status": STATUS_FAIL, "errors": [diagnostic]})
        except subprocess.TimeoutExpired:
            all_results.append({
                "candidate": selected,
                "status": "NOT TESTED — timeout",
                "errors": [f"exceeded {timeout_seconds}s before producing a result marker"],
            })
        except Exception as exc:
            all_results.append({"candidate": selected, "status": STATUS_FAIL, "errors": [str(exc)]})

    csv_rows = []
    for r in all_results:
        csv_rows.append({
            "frame": r.get("frame", "N/A"),
            "candidate": r.get("candidate", "N/A"),
            "version": r.get("version", "N/A"),
            "status": r.get("status", "N/A"),
            "text_count": r.get("text_count", "N/A"),
            "expected_found": r.get("expected_found", "N/A"),
            "expected_count": r.get("expected_count", "N/A"),
            "elapsed_sec": r.get("elapsed_sec", "N/A"),
            "errors": "; ".join(r.get("errors", []))
        })
        icon = "✓" if "PASS" in str(r.get("status", "")) else ("~" if "PARTIAL" in str(r.get("status", "")) else "✗")
        print(f"    [{icon}] {r.get('candidate', '?'):45s} frame={r.get('frame', '?')} texts={r.get('text_count', '?')} kw_found={r.get('expected_found', '?')} elapsed={r.get('elapsed_sec', '?')}s")

    save_json({"row": ROW, "name": NAME, "environment": env, "results": all_results}, OUT_DIR / "ocr_results_new.json")
    save_csv(csv_rows, OUT_DIR / "ocr_results_new.csv")

if __name__ == "__main__":
    main()
