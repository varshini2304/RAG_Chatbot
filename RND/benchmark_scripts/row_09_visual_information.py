"""
row_09_visual_information.py — Row 9: Visual Information, Tool/Part & Action ID
Candidates: Gemini VLM | OpenCV feature detection (ORB+MSER) | YOLOv8n (COCO pretrained)
Evaluates object detection, feature extraction, and latency across project keyframes on CPU.
"""
import sys, os, base64, json as _json
from pathlib import Path

# Ensure bench_utils is discoverable
sys.path.insert(0, str(Path(__file__).parent))
from bench_utils import *

ROW = 9
NAME = "Visual Information, Tool/Part & Action ID"
OUT_DIR = RESULTS_BASE / "09_visual_information"

# Real keyframes from the project
KEYFRAME_DIR = PROJECT_ROOT / "rndreport/video_input_evaluation/results/extracted_frames/const_01.mp4"
KEYFRAME_PATHS = []
for folder in [KEYFRAME_DIR, PROJECT_ROOT / "rndreport", OUT_DIR]:
    found = list(folder.rglob("OpenCV_ts_*.jpg")) if folder.exists() else []
    if found:
        KEYFRAME_PATHS = sorted(found)[:4]
        break

if not KEYFRAME_PATHS:
    for folder in (PROJECT_ROOT / "rndreport").iterdir() if (PROJECT_ROOT / "rndreport").exists() else []:
        if folder.is_dir():
            found = list(folder.rglob("*.jpg"))
            if found:
                KEYFRAME_PATHS = sorted(found)[:4]
                break

GROUND_TRUTH = {
    "OpenCV_ts_0.0s.jpg":    {"expected_category": "Blank / Intro", "expected_keywords": ["blank", "black", "intro"]},
    "OpenCV_ts_10.0s.jpg":   {"expected_category": "Presenter / Person", "expected_keywords": ["person", "man", "speaker", "presenter", "tie"]},
    "OpenCV_ts_272.6s.jpg":  {"expected_category": "Slide / Diagram", "expected_keywords": ["text", "slide", "diagram", "table"]},
    "OpenCV_ts_544.1s.jpg":  {"expected_category": "Slide / Summary", "expected_keywords": ["text", "slide", "summary"]},
}

def encode_image_b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("utf-8")

def test_gemini_vlm(img_path: Path) -> dict:
    import httpx
    api_key = os.environ.get("GOOGLE_API_KEY", "")
    model = os.environ.get("GEMINI_MODEL_NAME", "gemini-2.5-flash")
    if not api_key:
        return {"candidate": "Gemini VLM", "version": model, "status": "NOT TESTED — GOOGLE_API_KEY not set", "elapsed_sec": 0, "errors": ["GOOGLE_API_KEY missing"]}
        
    prompt = """Analyze this industrial video keyframe. Return ONLY a JSON object:
{
  "primary_action": "brief action description",
  "detected_objects": [{"name": "object_name", "category": "Person|Safety|Tool|Slide|Other", "confidence": 0.0-1.0}],
  "has_visible_content": true/false
}"""
    img_b64 = encode_image_b64(img_path)
    with Timer() as t:
        try:
            r = httpx.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}",
                json={"contents": [{"parts": [
                    {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}},
                    {"text": prompt}
                ]}], "generationConfig": {"temperature": 0.1, "maxOutputTokens": 512}},
                timeout=30.0)
            r.raise_for_status()
            content = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            match = __import__("re").search(r'\{.*\}', content, __import__("re").DOTALL)
            parsed = _json.loads(match.group()) if match else {"raw": content}
            objects = parsed.get("detected_objects", [])
            status = STATUS_PASS if objects else STATUS_PARTIAL
        except Exception as e:
            parsed = {}; objects = []; status = STATUS_FAIL
            
    gt = GROUND_TRUTH.get(img_path.name, {})
    keywords_found = 0
    response_text = _json.dumps(parsed).lower()
    for kw in gt.get("expected_keywords", []):
        if kw in response_text:
            keywords_found += 1
            
    return {
        "candidate": "Gemini VLM",
        "version": model,
        "status": status,
        "elapsed_sec": t.elapsed,
        "objects_detected": len(objects),
        "response": parsed,
        "keywords_found": keywords_found,
        "keywords_expected": len(gt.get("expected_keywords", [])),
        "errors": []
    }

def test_opencv_features(img_path: Path) -> dict:
    import cv2
    with Timer() as t:
        try:
            img = cv2.imread(str(img_path))
            if img is None:
                raise RuntimeError("Cannot read image")
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            orb = cv2.ORB_create()
            kps, desc = orb.detectAndCompute(gray, None)
            edges = cv2.Canny(gray, 100, 200)
            edge_density = float(edges.mean())
            mser = cv2.MSER_create()
            regions, _ = mser.detectRegions(gray)
            status = STATUS_PASS
        except Exception as e:
            return {"candidate": "OpenCV ORB+MSER", "version": cv2.__version__, "status": STATUS_FAIL, "elapsed_sec": 0, "errors": [str(e)]}
            
    return {
        "candidate": "OpenCV ORB+MSER",
        "version": cv2.__version__,
        "status": status,
        "elapsed_sec": t.elapsed,
        "keypoints_detected": len(kps) if kps else 0,
        "mser_regions": len(regions) if regions else 0,
        "edge_density": round(edge_density, 3),
        "note": "Feature detection for local scene changes; no semantic class labels without weights",
        "errors": []
    }

def test_yolo(img_path: Path) -> dict:
    try:
        from ultralytics import YOLO
    except ImportError:
        return {"candidate": "YOLOv8n (COCO pretrained)", "status": "NOT TESTED — ultralytics not installed", "errors": ["ultralytics not installed"]}
        
    errors = []
    with Timer() as t:
        try:
            model = YOLO("yolov8n.pt")
            results = model.predict(source=str(img_path), save=False, verbose=False, device="cpu")
            detections = []
            for r in results:
                for box in r.boxes:
                    cls_id = int(box.cls[0].item())
                    cls_name = model.names[cls_id]
                    conf = round(float(box.conf[0].item()), 4)
                    detections.append({"class_id": cls_id, "name": cls_name, "confidence": conf})
            status = STATUS_PASS if detections else STATUS_PARTIAL
        except Exception as e:
            detections = []; errors.append(str(e)); status = STATUS_FAIL
            
    gt = GROUND_TRUTH.get(img_path.name, {})
    keywords_found = sum(1 for kw in gt.get("expected_keywords", []) if any(kw in d["name"].lower() for d in detections))
    return {
        "candidate": "YOLOv8n (COCO pretrained)",
        "version": "8.4.127",
        "status": status,
        "elapsed_sec": t.elapsed,
        "objects_detected": len(detections),
        "detected_classes": [d["name"] for d in detections],
        "detections": detections,
        "keywords_found": keywords_found,
        "keywords_expected": len(gt.get("expected_keywords", [])),
        "note": "COCO 80-class pretrained weights on CPU; detects general classes (person, tie)",
        "errors": errors
    }

def main():
    print_header(ROW, NAME, OUT_DIR)
    env = env_fingerprint()
    if not KEYFRAME_PATHS:
        print("  [!] No keyframe JPGs found. Cannot run visual information test.")
        return
        
    print(f"  Found {len(KEYFRAME_PATHS)} keyframes: {[p.name for p in KEYFRAME_PATHS]}")
    all_results = []
    csv_rows = []
    
    for kp in KEYFRAME_PATHS:
        img_hash = sha256(kp)
        print(f"\n  Frame: {kp.name}  SHA256:{img_hash[:16]}...")
        r_cv = test_opencv_features(kp)
        r_yolo = test_yolo(kp)
        r_vlm = test_gemini_vlm(kp)
        
        for r in [r_cv, r_yolo, r_vlm]:
            all_results.append({
                "frame": kp.name,
                "sha256_prefix": img_hash[:16],
                **r
            })
            csv_rows.append({
                "frame": kp.name,
                "candidate": r["candidate"],
                "version": r.get("version", "N/A"),
                "status": r["status"],
                "objects_detected": r.get("objects_detected", r.get("keypoints_detected", "N/A")),
                "elapsed_sec": r.get("elapsed_sec", "N/A"),
                "errors": "; ".join(r.get("errors", []))
            })
            icon = "✓" if "PASS" in r["status"] else ("~" if "PARTIAL" in r["status"] else ("?" if "NOT" in r["status"] else "✗"))
            print(f"    [{icon}] {r['candidate']:30s} objs={r.get('objects_detected', r.get('keypoints_detected', 'N/A'))} elapsed={r.get('elapsed_sec', 'N/A')}s")

    save_json({"row": ROW, "name": NAME, "environment": env, "frames_tested": len(KEYFRAME_PATHS), "results": all_results},
              OUT_DIR / "visual_information_results_new.json")
    save_csv(csv_rows, OUT_DIR / "visual_information_results_new.csv")

if __name__ == "__main__":
    main()
