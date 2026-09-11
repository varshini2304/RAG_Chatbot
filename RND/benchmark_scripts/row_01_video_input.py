"""
row_01_video_input.py — Row 1: Video Evidence / Video Input
Candidates: PyAV | TorchCodec | FFmpeg CLI
Measures: open success, stream detection, metadata read, frame decode,
          wall-clock time, memory delta, errors.
"""
import os, sys, subprocess, time
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from bench_utils import *

ROW = 1
NAME = "Video Input & Ingestion"
OUT_DIR = RESULTS_BASE / "01_video_input"

VIDEO_FILES = list(VIDEOS_DIR.glob("*.mp4")) + list(VIDEOS_DIR.glob("*.webm")) + list(VIDEOS_DIR.glob("*.ogv"))
VIDEO_FILES = [v for v in VIDEO_FILES if v.is_file()]

def test_pyav(video_path: Path) -> dict:
    import av
    candidate = "PyAV"
    version = av.__version__
    mem_before = mem_mb()
    errors = []
    with Timer() as t:
        try:
            container = av.open(str(video_path))
            streams = list(container.streams)
            video_streams = list(container.streams.video)
            audio_streams = list(container.streams.audio)
            duration = float(container.duration or 0) / 1_000_000
            # Decode first video frame
            frame_decoded = False
            if video_streams:
                for frame in container.decode(video=0):
                    frame_decoded = True
                    break
            container.close()
            status = STATUS_PASS
        except Exception as e:
            errors.append(str(e))
            status = STATUS_FAIL
            streams = video_streams = audio_streams = []
            duration = 0.0
            frame_decoded = False
    mem_after = mem_mb()
    return {
        "candidate": candidate, "version": version,
        "status": status, "elapsed_sec": t.elapsed,
        "mem_delta_mb": round(mem_after - mem_before, 1),
        "video_streams": len(video_streams), "audio_streams": len(audio_streams),
        "duration_sec": round(duration, 3), "frame_decoded": frame_decoded,
        "errors": errors,
    }

def test_torchcodec(video_path: Path) -> dict:
    candidate = "TorchCodec"
    errors = []
    try:
        import torchcodec
        version = getattr(torchcodec, "__version__", "N/A")
    except Exception as e:
        return {"candidate": candidate, "version": "N/A",
                "status": "NOT TESTED — torchcodec native library unavailable", "errors": [str(e)],
                "elapsed_sec": 0, "mem_delta_mb": 0}
    mem_before = mem_mb()
    with Timer() as t:
        try:
            from torchcodec.decoders import VideoDecoder
            dec = VideoDecoder(str(video_path))
            meta = dec.metadata
            n_frames = meta.num_frames_from_content if hasattr(meta, "num_frames_from_content") else None
            frame = dec[0]  # decode first frame
            duration = float(meta.duration_seconds_from_header or 0)
            status = STATUS_PASS
        except Exception as e:
            errors.append(str(e))
            status = STATUS_FAIL
            n_frames = duration = None
            frame = None
    mem_after = mem_mb()
    return {
        "candidate": candidate, "version": version,
        "status": status, "elapsed_sec": t.elapsed,
        "mem_delta_mb": round(mem_after - mem_before, 1),
        "num_frames_reported": n_frames,
        "duration_sec": duration,
        "frame_shape": list(frame.data.shape) if frame is not None else None,
        "errors": errors,
    }

def test_ffmpeg_cli(video_path: Path) -> dict:
    candidate = "FFmpeg CLI (subprocess)"
    errors = []
    mem_before = mem_mb()
    with Timer() as t:
        try:
            r = subprocess.run(
                ["ffprobe", "-v", "error", "-print_format", "json",
                 "-show_streams", "-show_format", str(video_path)],
                capture_output=True, text=True, timeout=30
            )
            if r.returncode != 0:
                raise RuntimeError(r.stderr[:300])
            import json as _json
            data = _json.loads(r.stdout)
            streams = data.get("streams", [])
            vid = [s for s in streams if s.get("codec_type") == "video"]
            aud = [s for s in streams if s.get("codec_type") == "audio"]
            dur = float(data.get("format", {}).get("duration", 0))
            status = STATUS_PASS
        except Exception as e:
            errors.append(str(e))
            status = STATUS_FAIL
            vid = aud = []
            dur = 0.0
    mem_after = mem_mb()
    r_ver = subprocess.run(["ffprobe", "-version"], capture_output=True, text=True, timeout=10)
    version = r_ver.stdout.splitlines()[0] if r_ver.returncode == 0 else "unknown"
    return {
        "candidate": candidate, "version": version,
        "status": status, "elapsed_sec": t.elapsed,
        "mem_delta_mb": round(mem_after - mem_before, 1),
        "video_streams": len(vid), "audio_streams": len(aud),
        "duration_sec": round(dur, 3),
        "errors": errors,
    }

def main():
    print_header(ROW, NAME, OUT_DIR)
    env = env_fingerprint()
    all_results = []
    csv_rows = []
    for vp in sorted(VIDEO_FILES):
        file_hash = sha256(vp)
        print(f"\n  File: {vp.name}  SHA256: {file_hash[:16]}...")
        res_pyav     = test_pyav(vp)
        res_torch    = test_torchcodec(vp)
        res_ffmpeg   = test_ffmpeg_cli(vp)
        for r in [res_pyav, res_torch, res_ffmpeg]:
            row_dict = {
                "file": vp.name, "sha256_prefix": file_hash[:16],
                **r,
            }
            all_results.append(row_dict)
            csv_rows.append({
                "file": vp.name, "candidate": r["candidate"],
                "version": r.get("version", "N/A"),
                "status": r["status"], "elapsed_sec": r.get("elapsed_sec", "N/A"),
                "mem_delta_mb": r.get("mem_delta_mb", "N/A"),
                "video_streams": r.get("video_streams", "N/A"),
                "audio_streams": r.get("audio_streams", "N/A"),
                "duration_sec": r.get("duration_sec", "N/A"),
                "errors": "; ".join(r.get("errors", [])),
            })
            icon = "✓" if "PASS" in r["status"] else "✗"
            print(f"    [{icon}] {r['candidate']:20s} {r['status']:30s} {r.get('elapsed_sec','N/A')}s")
    output = {"row": ROW, "name": NAME, "environment": env, "results": all_results}
    save_json(output, OUT_DIR / "video_input_results.json")
    save_csv(csv_rows, OUT_DIR / "video_input_results.csv")
    print(f"\n  Done. {len(all_results)} evaluations across {len(VIDEO_FILES)} files.")

if __name__ == "__main__":
    main()
