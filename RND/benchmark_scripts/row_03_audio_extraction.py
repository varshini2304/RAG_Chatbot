"""
row_03_audio_extraction.py — Row 3: Audio Extraction & Resampling
Candidates: FFmpeg CLI | PyAV AudioResampler | SoundFile (read-only, needs pre-extracted WAV)
CORRECTED: Duration MUST match container duration within ±2s — this was the bug in previous run.
"""
import os, sys, subprocess, wave, tempfile
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from bench_utils import *

ROW = 3
NAME = "Audio Extraction & Resampling"
OUT_DIR = RESULTS_BASE / "03_audio_processing"
TARGET_SR = 16000; TARGET_CH = 1; TARGET_SW = 2  # 16kHz mono 16-bit PCM

VIDEO_FILES = sorted([v for v in VIDEOS_DIR.iterdir() if v.suffix.lower() in (".mp4",".webm",".ogv")])

def get_container_duration(vp: Path) -> float:
    """Ground truth duration via ffprobe."""
    r = subprocess.run(
        ["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0", str(vp)],
        capture_output=True, text=True, timeout=15)
    try: return round(float(r.stdout.strip()), 3)
    except: return 0.0

def inspect_wav(wav_path: str) -> dict:
    with wave.open(wav_path, "rb") as wf:
        ch = wf.getnchannels(); sr = wf.getframerate()
        sw = wf.getsampwidth(); nf = wf.getnframes()
        dur = round(nf / float(sr), 3) if sr else 0.0
        return {"channels":ch,"sample_rate":sr,"sample_width_bytes":sw,
                "num_frames":nf,"duration_sec":dur,
                "file_size_bytes":os.path.getsize(wav_path),
                "asr_compatible_16k_mono": ch==1 and sr==TARGET_SR and sw==TARGET_SW}

def test_ffmpeg_cli(vp: Path, tmp_dir: str, container_dur: float) -> dict:
    out_wav = os.path.join(tmp_dir, "ffmpeg_out.wav")
    errors = []; runs = 3; timings = []
    for _ in range(runs):
        if os.path.exists(out_wav): os.remove(out_wav)
        with Timer() as t:
            try:
                r = subprocess.run(
                    ["ffmpeg","-y","-i",str(vp),"-vn","-acodec","pcm_s16le",
                     "-ar",str(TARGET_SR),"-ac",str(TARGET_CH), out_wav],
                    capture_output=True, timeout=120)
                if r.returncode != 0: raise RuntimeError(r.stderr.decode()[-300:])
            except Exception as e:
                errors.append(str(e))
        timings.append(t.elapsed)
    if os.path.exists(out_wav) and not errors:
        props = inspect_wav(out_wav)
        dur_ok = abs(props["duration_sec"] - container_dur) <= 2.0
        status = STATUS_PASS if (props["asr_compatible_16k_mono"] and dur_ok) else STATUS_FAIL
        if not dur_ok:
            errors.append(f"Duration mismatch: extracted {props['duration_sec']}s vs container {container_dur}s")
    else:
        props = {}; status = STATUS_FAIL
    r_ver = subprocess.run(["ffmpeg","-version"],capture_output=True,text=True,timeout=5)
    version = r_ver.stdout.splitlines()[0] if r_ver.returncode==0 else "unknown"
    return {"candidate":"FFmpeg CLI","version":version,"status":status,
            "avg_sec":round(sum(timings)/len(timings),4),"timings":timings,
            "wav_props":props,"container_duration_sec":container_dur,
            "duration_match_within_2s": abs(props.get("duration_sec",0)-container_dur)<=2.0 if props else False,
            "errors":errors}

def test_pyav(vp: Path, tmp_dir: str, container_dur: float) -> dict:
    import av
    out_wav = os.path.join(tmp_dir, "pyav_out.wav")
    errors = []; runs = 3; timings = []
    for _ in range(runs):
        if os.path.exists(out_wav): os.remove(out_wav)
        with Timer() as t:
            try:
                container = av.open(str(vp))
                audio_streams = container.streams.audio
                if not audio_streams:
                    raise RuntimeError("No audio stream found")
                audio_stream = audio_streams[0]
                resampler = av.AudioResampler(format='s16', layout='mono', rate=TARGET_SR)
                out_frames = []
                for packet in container.demux(audio_stream):
                    for frame in packet.decode():
                        for rf in resampler.resample(frame):
                            out_frames.append(rf.to_ndarray().tobytes())
                for rf in (resampler.resample(None) or []):
                    out_frames.append(rf.to_ndarray().tobytes())
                container.close()
                raw_pcm = b"".join(out_frames)
                with wave.open(out_wav, "wb") as wf:
                    wf.setnchannels(1); wf.setsampwidth(2)
                    wf.setframerate(TARGET_SR); wf.writeframes(raw_pcm)
            except Exception as e:
                errors.append(str(e))
        timings.append(t.elapsed)
    if os.path.exists(out_wav) and not errors:
        props = inspect_wav(out_wav)
        dur_ok = abs(props["duration_sec"] - container_dur) <= 2.0
        status = STATUS_PASS if (props["asr_compatible_16k_mono"] and dur_ok) else STATUS_FAIL
        if not dur_ok:
            errors.append(f"Duration mismatch: PyAV decoded {props['duration_sec']}s vs container {container_dur}s (+{props['duration_sec']-container_dur:.1f}s)")
    else:
        props = {}; status = STATUS_FAIL
    return {"candidate":"PyAV","version":av.__version__,"status":status,
            "avg_sec":round(sum(timings)/len(timings),4),"timings":timings,
            "wav_props":props,"container_duration_sec":container_dur,
            "duration_match_within_2s": abs(props.get("duration_sec",0)-container_dur)<=2.0 if props else False,
            "errors":errors}

def test_soundfile(vp: Path, tmp_dir: str, container_dur: float) -> dict:
    """
    SoundFile cannot directly read MP4/WebM. Strategy:
    1. Extract WAV via FFmpeg first (already done)
    2. Read back via SoundFile and measure read performance + resample check
    """
    try:
        import soundfile as sf
        sf_version = getattr(sf, "__version__", "N/A")
    except Exception as e:
        return {"candidate": "SoundFile", "version": "N/A",
                "status": "NOT TESTED — soundfile not installed",
                "avg_sec": "N/A", "timings": [], "errors": [str(e)]}
    wav_ref = os.path.join(tmp_dir, "sf_ref.wav")
    errors = []; timings = []
    # Pre-extract via ffmpeg
    r = subprocess.run(
        ["ffmpeg","-y","-i",str(vp),"-vn","-acodec","pcm_s16le",
         "-ar",str(TARGET_SR),"-ac",str(TARGET_CH), wav_ref],
        capture_output=True, timeout=120)
    if r.returncode != 0:
        return {"candidate":"SoundFile","version":sf_version,
                "status":"NOT TESTED — ffmpeg pre-extract failed",
                "errors":[r.stderr.decode()[-200:]]}
    runs = 3
    for _ in range(runs):
        with Timer() as t:
            try:
                data, sr = sf.read(wav_ref, dtype="int16")
                dur_sf = round(len(data) / sr, 3)
            except Exception as e:
                errors.append(str(e)); break
        timings.append(t.elapsed)
    if not timings:
        return {"candidate":"SoundFile","version":sf.__version__,
                "status":STATUS_FAIL,"errors":errors}
    dur_ok = abs(dur_sf - container_dur) <= 2.0
    # SoundFile READS the WAV that ffmpeg produced — duration match will be same as ffmpeg
    props = {"channels":1 if data.ndim==1 else data.shape[1],
             "sample_rate":sr,"duration_sec":dur_sf,
             "num_frames":len(data),"asr_compatible_16k_mono": sr==TARGET_SR}
    status = STATUS_PASS if (props["asr_compatible_16k_mono"] and dur_ok) else STATUS_FAIL
    return {"candidate":"SoundFile","version":sf.__version__,"status":status,
            "avg_sec":round(sum(timings)/len(timings),4),"timings":timings,
            "wav_props":props,"container_duration_sec":container_dur,
            "duration_match_within_2s": dur_ok,
            "note":"SoundFile reads pre-extracted WAV (FFmpeg); measures read+parse latency only",
            "errors":errors}

def main():
    print_header(ROW, NAME, OUT_DIR)
    env = env_fingerprint()
    all_results = []; csv_rows = []
    for vp in sorted(VIDEO_FILES):
        file_hash = sha256(vp)
        container_dur = get_container_duration(vp)
        print(f"\n  File: {vp.name}  container_dur={container_dur}s  SHA256:{file_hash[:16]}...")
        with tempfile.TemporaryDirectory() as tmp:
            res_ff = test_ffmpeg_cli(vp, tmp, container_dur)
            res_av = test_pyav(vp, tmp, container_dur)
            res_sf = test_soundfile(vp, tmp, container_dur)
        for r in [res_ff, res_av, res_sf]:
            all_results.append({"file":vp.name,"sha256_prefix":file_hash[:16],"container_duration_sec":container_dur,**r})
            csv_rows.append({"file":vp.name,"candidate":r["candidate"],"version":r.get("version","N/A"),
                "status":r["status"],"avg_sec":r.get("avg_sec","N/A"),
                "wav_duration_sec":r.get("wav_props",{}).get("duration_sec","N/A"),
                "container_duration_sec":container_dur,
                "duration_match_within_2s":r.get("duration_match_within_2s","N/A"),
                "asr_compatible":r.get("wav_props",{}).get("asr_compatible_16k_mono","N/A"),
                "errors":"; ".join(r.get("errors",[]))})
            icon = "✓" if "PASS" in r["status"] else ("?" if "NOT" in r["status"] else "✗")
            print(f"    [{icon}] {r['candidate']:20s} {r['status']:30s} dur={r.get('wav_props',{}).get('duration_sec','N/A')}s")
    save_json({"row":ROW,"name":NAME,"environment":env,"results":all_results}, OUT_DIR/"audio_extraction_results.json")
    save_csv(csv_rows, OUT_DIR/"audio_extraction_results.csv")

if __name__ == "__main__":
    main()
