"""
row_08_keyframe_selection.py — Row 8: Candidate Keyframe Extraction
Candidates: PySceneDetect | Uniform Sampling | PySceneDetect + Uniform Hybrid
Measures: frames selected, scene cut detection, coverage, speed.
"""
import sys, os, subprocess
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from bench_utils import *

ROW = 8
NAME = "Candidate Keyframe Extraction"
OUT_DIR = RESULTS_BASE / "08_keyframe_selection"
VIDEO_FILES = sorted([v for v in VIDEOS_DIR.iterdir() if v.suffix.lower() in (".mp4",".webm",".ogv")])
UNIFORM_N = 4  # keyframes to select uniformly

def get_duration(vp: Path) -> float:
    r = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",str(vp)],
                       capture_output=True,text=True,timeout=15)
    try: return float(r.stdout.strip())
    except: return 0.0

def test_pyscenedetect(vp: Path) -> dict:
    try:
        from scenedetect import open_video, SceneManager
        from scenedetect.detectors import ContentDetector
        import scenedetect
        version = scenedetect.__version__
    except ImportError as e:
        return {"candidate":"PySceneDetect","version":"N/A","status":"NOT TESTED — not installed","errors":[str(e)]}
    errors = []
    with Timer() as t:
        try:
            video = open_video(str(vp))
            scene_mgr = SceneManager()
            scene_mgr.add_detector(ContentDetector(threshold=27.0))
            scene_mgr.detect_scenes(video, show_progress=False)
            scene_list = scene_mgr.get_scene_list()
            frames = []
            for start_tc, end_tc in scene_list:
                mid_sec = (start_tc.get_seconds() + end_tc.get_seconds()) / 2
                frames.append({"type":"scene_cut","timestamp_sec":round(mid_sec,3),
                               "scene_start_sec":round(start_tc.get_seconds(),3),
                               "scene_end_sec":round(end_tc.get_seconds(),3)})
            status = STATUS_PASS if frames else STATUS_PARTIAL
        except Exception as e:
            errors.append(str(e)); status = STATUS_FAIL; scene_list = []; frames = []
    return {"candidate":"PySceneDetect","version":version,"status":status,
            "elapsed_sec":t.elapsed,"scene_count":len(scene_list),
            "keyframes_selected":len(frames),"frames":frames,"errors":errors}

def test_uniform_sampling(vp: Path, duration: float) -> dict:
    import cv2
    errors = []
    with Timer() as t:
        try:
            cap = cv2.VideoCapture(str(vp))
            if not cap.isOpened(): raise RuntimeError("Cannot open")
            fps = cap.get(cv2.CAP_PROP_FPS)
            n = UNIFORM_N
            timestamps = [round(duration * i / (n - 1), 3) for i in range(n)] if n > 1 else [0.0]
            frames = []
            for ts in timestamps:
                frame_idx = int(ts * fps)
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                frames.append({"type":"uniform","timestamp_sec":ts,
                               "frame_idx":frame_idx,"read_ok":ret and frame is not None})
            cap.release()
            status = STATUS_PASS if all(f["read_ok"] for f in frames) else STATUS_PARTIAL
        except Exception as e:
            errors.append(str(e)); status = STATUS_FAIL; frames = []
    return {"candidate":f"Uniform Sampling (n={UNIFORM_N})","version":f"OpenCV {__import__('cv2').__version__}",
            "status":status,"elapsed_sec":t.elapsed,"keyframes_selected":len(frames),
            "frames":frames,"errors":errors}

def test_hybrid(psd_result: dict, uniform_result: dict, duration: float) -> dict:
    """Merge PySceneDetect cuts + uniform fallback keyframes, deduplicate within 2s."""
    from itertools import chain
    MIN_GAP = 2.0
    all_frames = list(chain(psd_result.get("frames",[]), uniform_result.get("frames",[])))
    all_frames.sort(key=lambda f: f.get("timestamp_sec",0))
    deduped = []
    for f in all_frames:
        if not deduped or (f["timestamp_sec"] - deduped[-1]["timestamp_sec"]) >= MIN_GAP:
            deduped.append(f)
    psd_ok = "PASS" in psd_result.get("status","")
    uni_ok = "PASS" in uniform_result.get("status","")
    status = STATUS_PASS if deduped else STATUS_FAIL
    return {"candidate":"Hybrid (PySceneDetect + Uniform)","version":"composite",
            "status":status,"elapsed_sec":0.0,
            "keyframes_selected":len(deduped),"frames":deduped,
            "psd_contributed":len(psd_result.get("frames",[])),
            "uniform_contributed":len(uniform_result.get("frames",[])),
            "errors":[]}

def main():
    print_header(ROW, NAME, OUT_DIR)
    env = env_fingerprint()
    all_results = []; csv_rows = []
    for vp in sorted(VIDEO_FILES):
        file_hash = sha256(vp)
        dur = get_duration(vp)
        print(f"\n  File: {vp.name}  duration={dur:.1f}s  SHA256:{file_hash[:16]}...")
        r_psd  = test_pyscenedetect(vp)
        r_uni  = test_uniform_sampling(vp, dur)
        r_hyb  = test_hybrid(r_psd, r_uni, dur)
        for r in [r_psd, r_uni, r_hyb]:
            all_results.append({"file":vp.name,"sha256_prefix":file_hash[:16],"duration_sec":dur,**r})
            csv_rows.append({"file":vp.name,"candidate":r["candidate"],"version":r.get("version","N/A"),
                "status":r["status"],"keyframes_selected":r.get("keyframes_selected","N/A"),
                "elapsed_sec":r.get("elapsed_sec","N/A"),"errors":"; ".join(r.get("errors",[]))})
            icon = "✓" if "PASS" in r["status"] else ("~" if "PARTIAL" in r["status"] else "✗")
            print(f"    [{icon}] {r['candidate']:40s} frames={r.get('keyframes_selected','N/A')} t={r.get('elapsed_sec','N/A')}s")
    save_json({"row":ROW,"name":NAME,"environment":env,"results":all_results}, OUT_DIR/"keyframe_selection_results.json")
    save_csv(csv_rows, OUT_DIR/"keyframe_selection_results.csv")

if __name__ == "__main__":
    main()
