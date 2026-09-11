import sys, os, tempfile, subprocess
from pathlib import Path

# Ensure bench_utils is discoverable
sys.path.insert(0, str(Path(__file__).parent))
from bench_utils import *

ROW = 5
NAME = "Speech Transcription"
OUT_DIR = RESULTS_BASE / "05_speech_transcription"

# Test videos covering English and Japanese
TEST_VIDEOS = {
    "test_instructional_normal.mp4": {"expected_lang": "en", "label": "English instructional"},
    "const_01.mp4": {"expected_lang": "ja", "label": "Japanese construction (Clean)"},
    "Working_on_machine_noisy.mp4": {"expected_lang": "ja", "label": "Noisy Japanese construction (Pink Noise Injected)"},
}

MODELS = [
    {"name": "faster-whisper tiny",  "engine": "faster-whisper", "model_size": "tiny",  "compute": "int8", "device": "cpu"},
    {"name": "faster-whisper base",  "engine": "faster-whisper", "model_size": "base",  "compute": "int8", "device": "cpu"},
    {"name": "WhisperX base",        "engine": "whisperx",       "model_size": "base",  "compute": "int8", "device": "cpu"},
]

def extract_audio_ffmpeg(vp: Path, out_wav: str) -> bool:
    r = subprocess.run(
        ["ffmpeg", "-y", "-i", str(vp), "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", out_wav],
        capture_output=True, timeout=120)
    return r.returncode == 0

def test_faster_whisper(wav_path: str, model_size: str, compute: str, device: str,
                        expected_lang: str) -> dict:
    from faster_whisper import WhisperModel
    errors = []
    mem_before = mem_mb()
    with Timer() as t_load:
        try:
            model = WhisperModel(model_size, device=device, compute_type=compute)
        except Exception as e:
            return {"model_size": model_size, "status": STATUS_FAIL, "errors": [str(e)]}
            
    with Timer() as t_trans:
        try:
            segments, info = model.transcribe(wav_path, beam_size=5, word_timestamps=True, vad_filter=True)
            seg_list = []
            for seg in segments:
                seg_list.append({
                    "start": round(seg.start, 3),
                    "end": round(seg.end, 3),
                    "text": seg.text,
                    "words": len(getattr(seg, "words", []) or [])
                })
            detected_lang = info.language
            lang_prob = round(info.language_probability, 4)
            audio_dur = info.duration
        except Exception as e:
            errors.append(str(e))
            seg_list = []; detected_lang = ""; lang_prob = 0.0; audio_dur = 0.0
            
    mem_after = mem_mb()
    rtf = round(t_trans.elapsed / audio_dur, 4) if audio_dur > 0 else None
    lang_correct = (detected_lang == expected_lang)
    total_words = sum(s["words"] for s in seg_list)
    status = STATUS_PASS if (lang_correct and len(seg_list) > 0 and not errors) else (STATUS_PARTIAL if len(seg_list) > 0 else STATUS_FAIL)
    
    return {
        "engine": "faster-whisper",
        "model_size": model_size, "compute_type": compute, "device": device,
        "load_time_sec": round(t_load.elapsed, 4),
        "transcription_time_sec": round(t_trans.elapsed, 4),
        "audio_duration_sec": round(audio_dur, 3),
        "rtf": rtf,
        "throughput_x": round(1.0/rtf, 2) if rtf and rtf > 0 else None,
        "detected_language": detected_lang,
        "language_probability": lang_prob,
        "expected_language": expected_lang,
        "language_correct": lang_correct,
        "segment_count": len(seg_list),
        "total_word_count": total_words,
        "transcript_excerpt": seg_list[:3] if seg_list else [],
        "mem_delta_mb": round(mem_after - mem_before, 1),
        "status": status,
        "errors": errors,
    }

def test_whisperx(wav_path: str, model_size: str, compute: str, device: str,
                  expected_lang: str) -> dict:
    try:
        whisperx = __import__("whisperx")
    except Exception as e:
        return {
            "engine": "whisperx",
            "model_size": model_size, "compute_type": compute, "device": device,
            "status": "NOT TESTED — whisperx not installed in active python environment",
            "errors": [str(e)]
        }
        
    errors = []
    mem_before = mem_mb()
    with Timer() as t_load:
        try:
            model = whisperx.load_model(model_size, device=device, compute_type=compute)
        except Exception as e:
            return {"engine": "whisperx", "model_size": model_size, "status": STATUS_FAIL, "errors": [str(e)]}
            
    with Timer() as t_trans:
        try:
            import soundfile as sf
            audio_np, sr = sf.read(wav_path, dtype="float32")
            if audio_np.ndim > 1:
                audio_np = audio_np.mean(axis=1)
            audio_dur = len(audio_np) / float(sr)
            audio = audio_np
            
            result = model.transcribe(audio, batch_size=4)
            detected_lang = result.get("language", "")
            raw_segments = result.get("segments", [])
            
            aligned_ok = False
            try:
                model_a, metadata = whisperx.load_align_model(language_code=detected_lang, device=device)
                aligned_res = whisperx.align(raw_segments, model_a, metadata, audio, device=device, return_char_alignments=False)
                raw_segments = aligned_res.get("segments", raw_segments)
                aligned_ok = True
            except Exception as e_align:
                errors.append(f"alignment_note: {e_align}")
                
            seg_list = []
            total_words = 0
            for seg in raw_segments:
                w_count = len(seg.get("words", []))
                total_words += w_count
                seg_list.append({
                    "start": round(seg.get("start", 0.0), 3),
                    "end": round(seg.get("end", 0.0), 3),
                    "text": seg.get("text", "").strip(),
                    "words": w_count
                })
        except Exception as e:
            errors.append(str(e))
            seg_list = []; detected_lang = ""; audio_dur = 0.0; aligned_ok = False
            
    mem_after = mem_mb()
    rtf = round(t_trans.elapsed / audio_dur, 4) if audio_dur > 0 else None
    lang_correct = (detected_lang == expected_lang)
    status = STATUS_PASS if (lang_correct and len(seg_list) > 0) else (STATUS_PARTIAL if len(seg_list) > 0 else STATUS_FAIL)
    
    return {
        "engine": "whisperx",
        "model_size": model_size, "compute_type": compute, "device": device,
        "load_time_sec": round(t_load.elapsed, 4),
        "transcription_time_sec": round(t_trans.elapsed, 4),
        "audio_duration_sec": round(audio_dur, 3),
        "rtf": rtf,
        "throughput_x": round(1.0/rtf, 2) if rtf and rtf > 0 else None,
        "detected_language": detected_lang,
        "language_probability": 1.0 if detected_lang else 0.0,
        "expected_language": expected_lang,
        "language_correct": lang_correct,
        "segment_count": len(seg_list),
        "total_word_count": total_words,
        "aligned_with_phonemes": aligned_ok,
        "transcript_excerpt": seg_list[:3] if seg_list else [],
        "mem_delta_mb": round(mem_after - mem_before, 1),
        "status": status,
        "errors": errors,
    }

def main():
    print_header(ROW, NAME, OUT_DIR)
    env = env_fingerprint()
    all_results = []
    csv_rows = []

    for video_name, meta in TEST_VIDEOS.items():
        vp = VIDEOS_DIR / video_name
        if not vp.exists():
            print(f"  [SKIP] {video_name} — file not found")
            continue
        file_hash = sha256(vp)
        print(f"\n  File: {video_name}  expected_lang={meta['expected_lang']}  SHA256:{file_hash[:16]}...")
        with tempfile.TemporaryDirectory() as tmp:
            wav_path = os.path.join(tmp, "audio.wav")
            ok = extract_audio_ffmpeg(vp, wav_path)
            if not ok:
                print(f"    [!] FFmpeg audio extraction failed for {video_name}")
                continue
                
            for m in MODELS:
                print(f"    Testing {m['name']}...")
                if m["engine"] == "faster-whisper":
                    r = test_faster_whisper(wav_path, m["model_size"], m["compute"], m["device"], meta["expected_lang"])
                elif m["engine"] == "whisperx":
                    r = test_whisperx(wav_path, m["model_size"], m["compute"], m["device"], meta["expected_lang"])
                else:
                    r = {"status": STATUS_NOT_TESTED, "errors": ["Unknown engine"]}
                    
                r["candidate"] = m["name"]
                all_results.append({
                    "file": video_name,
                    "sha256_prefix": file_hash[:16],
                    "label": meta["label"],
                    **r
                })
                csv_rows.append({
                    "file": video_name,
                    "label": meta["label"],
                    "candidate": r["candidate"],
                    "engine": r.get("engine", m["engine"]),
                    "model_size": m["model_size"],
                    "status": r["status"],
                    "rtf": r.get("rtf", "N/A"),
                    "throughput_x": r.get("throughput_x", "N/A"),
                    "detected_lang": r.get("detected_language", "N/A"),
                    "expected_lang": meta["expected_lang"],
                    "lang_correct": r.get("language_correct", "N/A"),
                    "segment_count": r.get("segment_count", "N/A"),
                    "transcription_time_sec": r.get("transcription_time_sec", "N/A"),
                    "errors": "; ".join(r.get("errors", []))
                })
                icon = "✓" if "PASS" in r["status"] else ("~" if "PARTIAL" in r["status"] else "✗")
                print(f"    [{icon}] {r['candidate']:25s} RTF={r.get('rtf','N/A')} lang={r.get('detected_language','?')} segs={r.get('segment_count','?')}")

    save_json({"row": ROW, "name": NAME, "environment": env, "results": all_results}, OUT_DIR / "speech_transcription_results.json")
    save_csv(csv_rows, OUT_DIR / "speech_transcription_results.csv")

if __name__ == "__main__":
    main()
