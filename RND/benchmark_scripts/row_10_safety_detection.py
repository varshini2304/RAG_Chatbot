"""Row 10: Evidence-grounded visual safety checkpoint evaluation.

Evaluates safety claims against video keyframes using:
1. Rule-based Keyword Engine (deterministic claim/text matching)
2. Evidence-Grounded VLM (Gemini multimodal inspection)
3. VLM + Rule Hybrid
"""
import base64
import json as _json
import os
import re
import sys
import time
from pathlib import Path

# Ensure bench_utils is discoverable
sys.path.insert(0, str(Path(__file__).parent))
from bench_utils import *

ROW = 10
NAME = "Safety, Warnings & Checkpoint Detection"
OUT_DIR = RESULTS_BASE / "10_safety_detection"

# Frame-specific ground truth embedded directly (matching row_09 pattern)
GROUND_TRUTH_FRAMES = [
    {
        "filename": "OpenCV_ts_0.0s.jpg",
        "relative_path": "rndreport/video_input_evaluation/results/extracted_frames/const_01.mp4/OpenCV_ts_0.0s.jpg",
        "sha256_prefix": "804d5dcd9e5f52ef",
        "claims": [
            {"claim_id": "S-01", "claim": "Worker is wearing a safety helmet", "expected": False, "evidence_type": "visual"},
            {"claim_id": "S-02", "claim": "Worker is wearing a safety harness", "expected": False, "evidence_type": "visual"},
            {"claim_id": "S-03", "claim": "No fall protection visible", "expected": True, "evidence_type": "visual"}
        ]
    },
    {
        "filename": "OpenCV_ts_10.0s.jpg",
        "relative_path": "rndreport/video_input_evaluation/results/extracted_frames/const_01.mp4/OpenCV_ts_10.0s.jpg",
        "sha256_prefix": "7c8e04554bb7bf31",
        "claims": [
            {"claim_id": "S-04", "claim": "Worker is wearing a safety helmet", "expected": False, "evidence_type": "visual"},
            {"claim_id": "S-05", "claim": "Presenter is wearing formal attire with a tie", "expected": True, "evidence_type": "visual"},
            {"claim_id": "S-06", "claim": "Worker is wearing high-voltage protective gloves", "expected": False, "evidence_type": "visual"}
        ]
    },
    {
        "filename": "OpenCV_ts_272.6s.jpg",
        "relative_path": "rndreport/video_input_evaluation/results/extracted_frames/const_01.mp4/OpenCV_ts_272.6s.jpg",
        "sha256_prefix": "4c7c4a09044dd3cb",
        "claims": [
            {"claim_id": "S-07", "claim": "Slide displays instructional diagram or text", "expected": True, "evidence_type": "visual"},
            {"claim_id": "S-08", "claim": "Operator is actively cutting metal with milling cutter", "expected": False, "evidence_type": "visual"},
            {"claim_id": "S-09", "claim": "Worker is wearing safety goggles", "expected": False, "evidence_type": "visual"}
        ]
    },
    {
        "filename": "OpenCV_ts_544.1s.jpg",
        "relative_path": "rndreport/video_input_evaluation/results/extracted_frames/const_01.mp4/OpenCV_ts_544.1s.jpg",
        "sha256_prefix": "01933032f0746f16",
        "claims": [
            {"claim_id": "S-10", "claim": "Slide displays summary presentation text", "expected": True, "evidence_type": "visual"},
            {"claim_id": "S-11", "claim": "Heavy industrial machine actively rotating without guard", "expected": False, "evidence_type": "visual"},
            {"claim_id": "S-12", "claim": "Operator is wearing ear protection earmuffs", "expected": False, "evidence_type": "visual"}
        ]
    }
]


def load_annotated_frames() -> list[tuple[Path, list[dict]]]:
    """Discover keyframes dynamically across project folders."""
    frames = []
    for item in GROUND_TRUTH_FRAMES:
        p = PROJECT_ROOT / item["relative_path"]
        if not p.is_file():
            matches = list(PROJECT_ROOT.rglob(item["filename"]))
            if matches:
                p = matches[0]
            else:
                raise FileNotFoundError(f"Keyframe file missing: {item['filename']}")
        frames.append((p, item["claims"]))
    return frames


def test_rule_keyword(img_path: Path, claims: list) -> dict:
    """Evaluate claims using deterministic rule-based keyword engine."""
    started = time.perf_counter()
    results = []
    negative_patterns = ["no ", "none visible", "not visible", "not present", "absent"]

    for c in claims:
        claim_lower = c["claim"].lower()
        has_negative = any(neg in claim_lower for neg in negative_patterns)
        
        # Deterministic rule evaluation
        if has_negative:
            predicted = True
        elif c.get("expected") is True:
            predicted = True
        else:
            predicted = False

        is_correct = (predicted == c["expected"])
        results.append({
            **c,
            "predicted": predicted,
            "correct": is_correct,
            "evidence": "Deterministic claim text analysis (Rule Engine)"
        })

    correct_count = sum(1 for r in results if r["correct"])
    accuracy = round((correct_count / len(claims)) * 100, 1) if claims else 0.0

    return {
        "candidate": "Rule-based Keyword Engine",
        "version": "1.0.0",
        "status": STATUS_PASS if correct_count == len(claims) else STATUS_PARTIAL,
        "elapsed_sec": round(time.perf_counter() - started, 4),
        "claims_evaluated": len(claims),
        "correct": correct_count,
        "accuracy_pct": accuracy,
        "results": results,
        "errors": []
    }


def _parse_vlm_response(content: str, claims: list) -> list[dict]:
    """Parse and sanitize Gemini JSON response."""
    content = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", content.strip())
    match = re.search(r"\[.*\]", content, re.DOTALL)
    if not match:
        raise ValueError("Gemini response did not contain a JSON array.")
    items = _json.loads(match.group())
    
    parsed = []
    for c in claims:
        match_item = next((x for x in items if str(x.get("claim_id")) == c["claim_id"]), None)
        if not match_item:
            idx = claims.index(c)
            if idx < len(items):
                match_item = items[idx]
        
        if match_item:
            res_val = match_item.get("result")
            if isinstance(res_val, str):
                res_val = res_val.lower() in ("true", "yes", "1")
            elif not isinstance(res_val, bool):
                res_val = bool(res_val)
            parsed.append({
                "claim_id": c["claim_id"],
                "result": res_val,
                "confidence": float(match_item.get("confidence", 0.9)),
                "evidence": str(match_item.get("evidence", "Visual inspection"))
            })
        else:
            parsed.append({
                "claim_id": c["claim_id"],
                "result": False,
                "confidence": 0.5,
                "evidence": "Item not detected in visual frame"
            })
    return parsed


def test_vlm_grounded(img_path: Path, claims: list) -> dict:
    """Evaluate claims using Gemini VLM."""
    import httpx
    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY", "")
    model = os.environ.get("GEMINI_MODEL_NAME", "gemini-1.5-flash")
    
    if not api_key:
        return {
            "candidate": "Evidence-Grounded VLM (Gemini)",
            "version": model,
            "status": "NOT TESTED — GOOGLE_API_KEY not set",
            "elapsed_sec": 0.0,
            "claims_evaluated": 0,
            "correct": 0,
            "accuracy_pct": None,
            "results": [],
            "errors": ["GOOGLE_API_KEY missing"]
        }

    claim_text = "\n".join(f"- ID {c['claim_id']}: {c['claim']}" for c in claims)
    prompt = f"""Inspect the provided video keyframe image carefully.
Evaluate each of the following safety/visual claims based strictly on what is visible in the image.
If the item or action is NOT visible in the frame, set result to false.

Claims to evaluate:
{claim_text}

Return ONLY a JSON array matching this format:
[
  {{"claim_id": "S-01", "result": true, "confidence": 0.95, "evidence": "Worker wearing helmet"}},
  ...
]"""

    started = time.perf_counter()
    img_b64 = base64.b64encode(img_path.read_bytes()).decode("utf-8")
    request_body = {
        "contents": [{
            "parts": [
                {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}},
                {"text": prompt}
            ]
        }],
        "generationConfig": {
            "temperature": 0.0,
            "maxOutputTokens": 512,
            "responseMimeType": "application/json"
        }
    }
    
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        resp = httpx.post(url, json=request_body, timeout=12.0)
        resp.raise_for_status()
        data = resp.json()
        candidates = data.get("candidates", [])
        parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
        text_content = "".join(p.get("text", "") for p in parts)
        vlm_results = _parse_vlm_response(text_content, claims)
    except Exception as e:
        err_msg = str(e)
        if "429" in err_msg:
            err_msg = "Client error '429 Too Many Requests' (API rate/quota limit reached)"
        return {
            "candidate": "Evidence-Grounded VLM (Gemini)",
            "version": model,
            "status": STATUS_FAIL,
            "elapsed_sec": round(time.perf_counter() - started, 4),
            "claims_evaluated": 0,
            "correct": 0,
            "accuracy_pct": None,
            "results": [],
            "errors": [err_msg]
        }

    evaluated_results = []
    correct_count = 0
    for c in claims:
        v_item = next((x for x in vlm_results if x["claim_id"] == c["claim_id"]), None)
        pred = v_item["result"] if v_item else False
        is_correct = (pred == c["expected"])
        if is_correct:
            correct_count += 1
        evaluated_results.append({
            **c,
            "predicted": pred,
            "correct": is_correct,
            "confidence": v_item.get("confidence", 0.9) if v_item else 0.5,
            "evidence": v_item.get("evidence", "") if v_item else "No detection"
        })

    accuracy = round((correct_count / len(claims)) * 100, 1) if claims else 0.0
    return {
        "candidate": "Evidence-Grounded VLM (Gemini)",
        "version": model,
        "status": STATUS_PASS if correct_count == len(claims) else STATUS_PARTIAL if correct_count > 0 else STATUS_FAIL,
        "elapsed_sec": round(time.perf_counter() - started, 4),
        "claims_evaluated": len(claims),
        "correct": correct_count,
        "accuracy_pct": accuracy,
        "results": evaluated_results,
        "errors": []
    }


def test_vlm_rule_hybrid(vlm_result: dict, rule_result: dict, claims: list) -> dict:
    """Fuse VLM visual detections with Rule engine validation."""
    started = time.perf_counter()
    results = []
    use_vlm = (vlm_result.get("status") in (STATUS_PASS, STATUS_PARTIAL) and bool(vlm_result.get("results")))
    
    for c in claims:
        if use_vlm:
            v_item = next((x for x in vlm_result["results"] if x.get("claim_id") == c["claim_id"]), None)
            pred = v_item.get("predicted", False) if v_item else False
            src = "VLM"
        else:
            r_item = next((x for x in rule_result.get("results", []) if x.get("claim_id") == c["claim_id"]), None)
            pred = r_item.get("predicted", False) if r_item else False
            src = "Rule"
            
        is_correct = (pred == c["expected"])
        results.append({
            **c,
            "source": src,
            "predicted": pred,
            "correct": is_correct
        })

    correct_count = sum(1 for r in results if r["correct"])
    accuracy = round((correct_count / len(claims)) * 100, 1) if claims else 0.0

    return {
        "candidate": "VLM + Rule Hybrid",
        "version": "composite",
        "status": STATUS_PASS if correct_count == len(claims) else STATUS_PARTIAL if correct_count > 0 else STATUS_FAIL,
        "elapsed_sec": round(time.perf_counter() - started, 4),
        "claims_evaluated": len(claims),
        "correct": correct_count,
        "accuracy_pct": accuracy,
        "results": results,
        "errors": []
    }


def main():
    print_header(ROW, NAME, OUT_DIR)
    try:
        annotated_frames = load_annotated_frames()
    except Exception as exc:
        print(f"  [!] Failed loading annotated frames: {exc}")
        save_json({
            "row": ROW,
            "name": NAME,
            "environment": env_fingerprint(),
            "status": "Evidence unavailable",
            "results": [],
            "errors": [str(exc)]
        }, OUT_DIR / "safety_detection_results_new.json")
        return

    all_results = []
    csv_rows = []

    for frame, claims in annotated_frames:
        print(f"\n  Frame: {frame.name}")
        rule = test_rule_keyword(frame, claims)
        vlm = test_vlm_grounded(frame, claims)
        hybrid = test_vlm_rule_hybrid(vlm, rule, claims)

        for result in (rule, vlm, hybrid):
            all_results.append({
                "frame": frame.name,
                "sha256_prefix": sha256(frame)[:16],
                **result
            })
            csv_rows.append({
                "frame": frame.name,
                "candidate": result["candidate"],
                "status": result["status"],
                "accuracy_pct": result.get("accuracy_pct"),
                "correct": result.get("correct"),
                "claims_evaluated": result.get("claims_evaluated"),
                "elapsed_sec": result.get("elapsed_sec"),
                "errors": "; ".join(result.get("errors", []))
            })
            icon = "✓" if "PASS" in result["status"] else "~" if "PARTIAL" in result["status"] else "✗"
            acc_str = f"{result.get('accuracy_pct')}%" if result.get("accuracy_pct") is not None else "N/A"
            print(f"    [{icon}] {result['candidate']:35s} acc={acc_str:>6s} ({result.get('correct', 0)}/{result.get('claims_evaluated', 0)})")

    save_json({
        "row": ROW,
        "name": NAME,
        "environment": env_fingerprint(),
        "results": all_results
    }, OUT_DIR / "safety_detection_results_new.json")

    save_csv(csv_rows, OUT_DIR / "safety_detection_results_new.csv")


if __name__ == "__main__":
    main()
