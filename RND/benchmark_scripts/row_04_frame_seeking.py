"""
row_04_frame_seeking.py — Row 4: Visual Processing / Frame Seeking
Candidates: PyAV | TorchCodec | OpenCV
Measures: seek accuracy (timestamp error), latency, success rate, memory.
"""
import sys, subprocess
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from bench_utils import *

ROW = 4
NAME = "Visual Processing / Frame Seeking"
OUT_DIR = RESULTS_BASE / "04_visual_processing"
VIDEO_FILES = sorted([v for v in VIDEOS_DIR.iterdir() if v.suffix.lower() in (".mp4",".webm",".ogv")])

# Seek to these fractions of video duration
SEEK_FRACTIONS = [0.0, 0.1, 0.25, 0.5, 0.75, 0.9]

def get_duration(vp: Path) -> float:
    r = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0", str(vp)],
                       capture_output=True, text=True, timeout=15)
    try: return float(r.stdout.strip())
    except: return 0.0

def test_pyav_seek(vp: Path, seek_times: list) -> dict:
    import av
    errors = []; seeks = []
    with Timer() as t_total:
        for ts in seek_times:
            t0 = time.perf_counter()
            try:
                container = av.open(str(vp))
                container.seek(int(ts * 1_000_000), any_frame=False)
                frame = None
                for f in container.decode(video=0):
                    frame = f; break
                container.close()
                if frame is None: raise RuntimeError("No frame decoded")
                actual_ts = float(frame.pts * frame.time_base) if frame.pts is not None else ts
                err = abs(actual_ts - ts)
                dt = round(time.perf_counter() - t0, 4)
                seeks.append({"target_sec":ts,"actual_sec":round(actual_ts,4),"error_sec":round(err,4),"ok":err<=1.0,"elapsed":dt})
            except Exception as e:
                dt = round(time.perf_counter() - t0, 4)
                errors.append(f"seek@{ts}s: {e}")
                seeks.append({"target_sec":ts,"actual_sec":None,"error_sec":None,"ok":False,"elapsed":dt})
    success = sum(1 for s in seeks if s["ok"]); total = len(seeks)
    errors_unique = list(set(errors))
    return {"candidate":"PyAV","version":av.__version__,
            "status":STATUS_PASS if success==total and not errors_unique else (STATUS_PARTIAL if success>0 else STATUS_FAIL),
            "seek_results":seeks,"success_rate":round(success/total*100,1) if total else 0,
            "total_elapsed_sec":round(t_total.elapsed,4),
            "avg_seek_sec":round(sum(s["elapsed"] for s in seeks)/total,4) if total else 0,
            "errors":errors_unique}

def test_torchcodec_seek(vp: Path, seek_times: list) -> dict:
    try:
        from torchcodec.decoders import VideoDecoder
        import torchcodec
        version = getattr(torchcodec, "__version__", "N/A")
    except Exception as e:
        return {"candidate":"TorchCodec","version":"N/A","status":"NOT TESTED — torchcodec native library unavailable",
                "errors":[str(e)]}
    errors = []; seeks = []
    with Timer() as t_total:
        for ts in seek_times:
            t0 = time.perf_counter()
            try:
                dec = VideoDecoder(str(vp))
                frame = dec.get_frame_played_at(ts)
                actual_ts = float(frame.pts_seconds)
                err = abs(actual_ts - ts)
                dt = round(time.perf_counter() - t0, 4)
                seeks.append({"target_sec":ts,"actual_sec":round(actual_ts,4),"error_sec":round(err,4),"ok":err<=1.0,"elapsed":dt})
            except Exception as e:
                dt = round(time.perf_counter() - t0, 4)
                errors.append(f"seek@{ts}s: {str(e)[:100]}")
                seeks.append({"target_sec":ts,"actual_sec":None,"error_sec":None,"ok":False,"elapsed":dt})
    success = sum(1 for s in seeks if s["ok"]); total = len(seeks)
    return {"candidate":"TorchCodec","version":version,
            "status":STATUS_PASS if success==total and not errors else (STATUS_PARTIAL if success>0 else STATUS_FAIL),
            "seek_results":seeks,"success_rate":round(success/total*100,1) if total else 0,
            "total_elapsed_sec":round(t_total.elapsed,4),
            "avg_seek_sec":round(sum(s["elapsed"] for s in seeks)/total,4) if total else 0,
            "errors":list(set(errors))}

def test_opencv_seek(vp: Path, seek_times: list) -> dict:
    import cv2
    errors = []; seeks = []
    with Timer() as t_total:
        for ts in seek_times:
            t0 = time.perf_counter()
            try:
                cap = cv2.VideoCapture(str(vp))
                if not cap.isOpened(): raise RuntimeError("Cannot open video")
                fps = cap.get(cv2.CAP_PROP_FPS)
                frame_idx = int(ts * fps)
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                cap.release()
                if not ret or frame is None: raise RuntimeError("Read failed")
                actual_ts = frame_idx / fps if fps > 0 else ts
                err = abs(actual_ts - ts)
                dt = round(time.perf_counter() - t0, 4)
                seeks.append({"target_sec":ts,"actual_sec":round(actual_ts,4),"error_sec":round(err,4),"ok":err<=1.0,"elapsed":dt})
            except Exception as e:
                dt = round(time.perf_counter() - t0, 4)
                errors.append(f"seek@{ts}s: {str(e)[:100]}")
                seeks.append({"target_sec":ts,"actual_sec":None,"error_sec":None,"ok":False,"elapsed":dt})
    success = sum(1 for s in seeks if s["ok"]); total = len(seeks)
    return {"candidate":"OpenCV","version":cv2.__version__,
            "status":STATUS_PASS if success==total and not errors else (STATUS_PARTIAL if success>0 else STATUS_FAIL),
            "seek_results":seeks,"success_rate":round(success/total*100,1) if total else 0,
            "total_elapsed_sec":round(t_total.elapsed,4),
            "avg_seek_sec":round(sum(s["elapsed"] for s in seeks)/total,4) if total else 0,
            "errors":list(set(errors))}

def main():
    print_header(ROW, NAME, OUT_DIR)
    env = env_fingerprint()
    all_results = []; csv_rows = []
    for vp in sorted(VIDEO_FILES):
        file_hash = sha256(vp)
        dur = get_duration(vp)
        seek_times = [round(dur * f, 2) for f in SEEK_FRACTIONS if dur > 0]
        print(f"\n  File: {vp.name}  duration={dur:.1f}s  seeks={seek_times}")
        for test_fn in [test_pyav_seek, test_torchcodec_seek, test_opencv_seek]:
            r = test_fn(vp, seek_times)
            all_results.append({"file":vp.name,"sha256_prefix":file_hash[:16],"duration_sec":dur,**r})
            csv_rows.append({"file":vp.name,"candidate":r["candidate"],"version":r.get("version","N/A"),
                "status":r["status"],"success_rate_pct":r.get("success_rate","N/A"),
                "avg_seek_sec":r.get("avg_seek_sec","N/A"),"total_elapsed_sec":r.get("total_elapsed_sec","N/A"),
                "errors":"; ".join(r.get("errors",[]))})
            icon = "✓" if "PASS" in r["status"] else ("~" if "PARTIAL" in r["status"] else ("?" if "NOT" in r["status"] else "✗"))
            print(f"    [{icon}] {r['candidate']:15s} {r['status']:30s} success={r.get('success_rate','N/A')}%")
    save_json({"row":ROW,"name":NAME,"environment":env,"results":all_results}, OUT_DIR/"frame_seeking_results.json")
    save_csv(csv_rows, OUT_DIR/"frame_seeking_results.csv")

if __name__ == "__main__":
    main()
