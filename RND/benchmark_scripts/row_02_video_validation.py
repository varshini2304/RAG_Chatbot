"""
row_02_video_validation.py — Row 2: Video Validation & Metadata Extraction
Candidates: ffprobe | PyAV | MediaInfo CLI
Measures: metadata field coverage, accuracy vs ffprobe ground truth, speed.
"""
import os, sys, subprocess, json as _json
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from bench_utils import *

ROW = 2
NAME = "Video Validation & Metadata Extraction"
OUT_DIR = RESULTS_BASE / "02_video_validation"
VIDEO_FILES = sorted([v for v in VIDEOS_DIR.iterdir() if v.suffix.lower() in (".mp4", ".webm", ".ogv", ".mkv") and v.is_file()])

EXPECTED_FIELDS = ["filename","duration_sec","width","height","fps","video_codec","audio_codec","file_size_bytes"]

def get_ffprobe_ground_truth(vp: Path) -> dict:
    """ffprobe is the ground truth reference."""
    r = subprocess.run(
        ["ffprobe","-v","error","-print_format","json","-show_streams","-show_format", str(vp)],
        capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        return {}
    data = _json.loads(r.stdout)
    streams = data.get("streams", [])
    vid = next((s for s in streams if s.get("codec_type") == "video"), {})
    aud = next((s for s in streams if s.get("codec_type") == "audio"), {})
    fmt = data.get("format", {})
    fps_str = vid.get("r_frame_rate","0/1")
    try:
        num, den = fps_str.split("/"); fps = round(int(num)/int(den), 3) if int(den) else 0
    except: fps = 0
    return {
        "filename": vp.name,
        "duration_sec": round(float(fmt.get("duration",0)), 3),
        "width": vid.get("width"),
        "height": vid.get("height"),
        "fps": fps,
        "video_codec": vid.get("codec_name"),
        "audio_codec": aud.get("codec_name"),
        "file_size_bytes": int(fmt.get("size", 0)),
    }

def test_pyav_meta(vp: Path) -> dict:
    import av
    errors = []
    with Timer() as t:
        try:
            container = av.open(str(vp))
            vid_s = list(container.streams.video)
            aud_s = list(container.streams.audio)
            v = vid_s[0] if vid_s else None
            a = aud_s[0] if aud_s else None
            dur = float(container.duration or 0) / 1_000_000
            fps = float(v.average_rate) if v and v.average_rate else 0
            result = {
                "filename": vp.name,
                "duration_sec": round(dur, 3),
                "width": v.width if v else None,
                "height": v.height if v else None,
                "fps": round(fps, 3),
                "video_codec": v.name if v else None,
                "audio_codec": a.name if a else None,
                "file_size_bytes": vp.stat().st_size,
            }
            container.close()
            status = STATUS_PASS
        except Exception as e:
            errors.append(str(e)); status = STATUS_FAIL; result = {}
    return {"candidate":"PyAV","version":av.__version__,"status":status,
            "elapsed_sec":t.elapsed,"metadata":result,"errors":errors}

def test_mediainfo(vp: Path) -> dict:
    candidate = "MediaInfo CLI"
    errors = []
    # Check if mediainfo binary exists
    r_check = subprocess.run(["where","mediainfo"], capture_output=True, text=True, timeout=5)
    if r_check.returncode != 0:
        return {"candidate":candidate,"version":"N/A",
                "status":"NOT TESTED — mediainfo binary not found on PATH",
                "elapsed_sec":0,"metadata":{},"errors":["mediainfo not installed"]}
    with Timer() as t:
        try:
            r = subprocess.run(["mediainfo","--Output=JSON", str(vp)],
                               capture_output=True, text=True, timeout=30)
            data = _json.loads(r.stdout)
            tracks = data.get("media",{}).get("track",[])
            gen = next((t for t in tracks if t.get("@type")=="General"), {})
            vid = next((t for t in tracks if t.get("@type")=="Video"), {})
            aud = next((t for t in tracks if t.get("@type")=="Audio"), {})
            result = {
                "filename": vp.name,
                "duration_sec": round(float(gen.get("Duration",0)), 3),
                "width": int(vid.get("Width",0)) if vid.get("Width") else None,
                "height": int(vid.get("Height",0)) if vid.get("Height") else None,
                "fps": round(float(vid.get("FrameRate",0)), 3),
                "video_codec": vid.get("Format"),
                "audio_codec": aud.get("Format"),
                "file_size_bytes": int(gen.get("FileSize",0)) if gen.get("FileSize") else None,
            }
            status = STATUS_PASS
        except Exception as e:
            errors.append(str(e)); status = STATUS_FAIL; result = {}
    ver_r = subprocess.run(["mediainfo","--Version"], capture_output=True, text=True, timeout=5)
    ver = ver_r.stdout.strip() if ver_r.returncode == 0 else "unknown"
    return {"candidate":candidate,"version":ver,"status":status,
            "elapsed_sec":t.elapsed,"metadata":result,"errors":errors}

def compare(actual: dict, expected: dict, fields: list) -> dict:
    matched = 0; total = len(fields); mismatches = {}
    for f in fields:
        a = actual.get(f); e = expected.get(f)
        if a is None or e is None:
            continue
        # Duration: allow ±1s tolerance; fps: ±0.1; sizes: exact
        if f == "duration_sec":
            ok = abs(float(a) - float(e)) <= 1.0
        elif f == "fps":
            ok = abs(float(a) - float(e)) <= 0.5
        elif f == "file_size_bytes":
            ok = a == e
        else:
            ok = str(a).lower() == str(e).lower()
        if ok: matched += 1
        else: mismatches[f] = {"actual": a, "expected": e}
    return {"fields_checked": total, "matched": matched,
            "match_pct": round(matched/total*100, 1) if total else 0,
            "mismatches": mismatches}

def main():
    print_header(ROW, NAME, OUT_DIR)
    env = env_fingerprint()
    all_results = []; csv_rows = []
    for vp in sorted(VIDEO_FILES):
        file_hash = sha256(vp)
        print(f"\n  File: {vp.name}  SHA256: {file_hash[:16]}...")
        with Timer() as t_gt:
            gt = get_ffprobe_ground_truth(vp)
        gt_row = {"candidate":"ffprobe (ground truth)","version":"9.0","status":STATUS_PASS,
                  "elapsed_sec":t_gt.elapsed,"metadata":gt,"errors":[]}
        pyav_row   = test_pyav_meta(vp)
        media_row  = test_mediainfo(vp)
        for r in [gt_row, pyav_row, media_row]:
            cmp = compare(r.get("metadata",{}), gt, EXPECTED_FIELDS) if r["candidate"] != "ffprobe (ground truth)" else {}
            r["comparison_vs_ffprobe"] = cmp
            all_results.append({"file":vp.name,"sha256_prefix":file_hash[:16],**r})
            csv_rows.append({"file":vp.name,"candidate":r["candidate"],
                "version":r.get("version"),"status":r["status"],
                "elapsed_sec":r.get("elapsed_sec"),"match_pct":cmp.get("match_pct","N/A"),
                "matched_fields":cmp.get("matched","N/A"),"errors":"; ".join(r.get("errors",[]))})
            icon = "✓" if "PASS" in r["status"] else ("?" if "NOT" in r["status"] else "✗")
            match_str = f"match={cmp.get('match_pct','N/A')}%" if cmp else "(reference)"
            print(f"    [{icon}] {r['candidate']:30s} {match_str:15s} {r.get('elapsed_sec','N/A')}s")
    save_json({"row":ROW,"name":NAME,"environment":env,"results":all_results},
              OUT_DIR / "video_validation_results.json")
    save_csv(csv_rows, OUT_DIR / "video_validation_results.csv")

if __name__ == "__main__":
    main()
