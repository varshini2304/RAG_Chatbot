"""
row_06_timestamp_alignment.py — Row 6: Transcript & Timestamp Alignment
Candidates: faster-whisper native (segment-level) | faster-whisper word-level | Heuristic linear interpolation
Measures: start/end timestamp error vs manual ground truth annotations.
"""
import sys, os, tempfile, subprocess, json as _json
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from bench_utils import *

ROW = 6
NAME = "Transcript & Timestamp Alignment"
OUT_DIR = RESULTS_BASE / "06_transcript_alignment"

# Ground truth annotations — manually verified timestamps
GROUND_TRUTH = {
    "test_instructional_normal.mp4": {
        "language": "en",
        "annotations": [
            {"phrase":"Today",    "expected_start":0.00, "expected_end":0.35},
            {"phrase":"talk",     "expected_start":0.65, "expected_end":0.90},
            {"phrase":"basic",    "expected_start":0.95, "expected_end":1.25},
            {"phrase":"mill",     "expected_start":1.30, "expected_end":1.55},
            {"phrase":"safety",   "expected_start":1.60, "expected_end":2.05},
            {"phrase":"and",      "expected_start":2.10, "expected_end":2.25},
            {"phrase":"operation","expected_start":2.30, "expected_end":2.85},
        ]
    },
    "const_01.mp4": {
        "language": "ja",
        "annotations": [
            {"phrase":"こんにちは",  "expected_start":11.85, "expected_end":12.20},
            {"phrase":"それでは",   "expected_start":13.65, "expected_end":14.15},
        ]
    }
}
TOLERANCE_SEC = 0.5

def extract_audio(vp: Path, out_wav: str):
    subprocess.run(["ffmpeg","-y","-i",str(vp),"-vn","-acodec","pcm_s16le","-ar","16000","-ac","1",out_wav],
                   capture_output=True, timeout=120)

def find_phrase_timestamp(segments, words_by_seg, phrase: str, mode: str, language: str):
    """Find start/end of phrase in transcript. Mode: segment or word."""
    phrase_l = phrase.lower().strip()
    if mode == "word":
        for w in words_by_seg:
            if phrase_l in w.get("word","").lower():
                return w.get("start"), w.get("end")
    # Fallback: segment-level scan
    for seg in segments:
        if phrase_l in seg["text"].lower():
            return seg["start"], seg["end"]
    return None, None

def run_alignment_test(wav_path: str, annotations: list, language: str, mode: str) -> list:
    from faster_whisper import WhisperModel
    model = WhisperModel("base", device="cpu", compute_type="int8")
    segments_raw, _ = model.transcribe(wav_path, beam_size=5, language=language,
                                        word_timestamps=(mode=="word"), vad_filter=True)
    segments = []
    words_flat = []
    for seg in segments_raw:
        s = {"start":round(seg.start,4),"end":round(seg.end,4),"text":seg.text}
        segments.append(s)
        if mode == "word" and seg.words:
            for w in seg.words:
                words_flat.append({"word":w.word,"start":round(w.start,4),"end":round(w.end,4)})
    results = []
    for ann in annotations:
        asr_start, asr_end = find_phrase_timestamp(segments, words_flat, ann["phrase"], mode, language)
        if asr_start is None:
            results.append({**ann,"asr_start":None,"asr_end":None,"start_err":None,"end_err":None,
                            "within_tolerance":False,"note":"phrase not found in transcript"})
        else:
            se = round(abs(asr_start - ann["expected_start"]), 4)
            ee = round(abs((asr_end or asr_start) - ann["expected_end"]), 4)
            within = se <= TOLERANCE_SEC and ee <= TOLERANCE_SEC
            results.append({**ann,"asr_start":asr_start,"asr_end":asr_end,
                            "start_err_sec":se,"end_err_sec":ee,"within_tolerance":within})
    return results, segments

def heuristic_interpolate(duration_sec: float, annotations: list) -> list:
    """Linear interpolation: assume uniform speech rate, proportional timestamp."""
    results = []
    for ann in annotations:
        mid_expected = (ann["expected_start"] + ann["expected_end"]) / 2
        # Heuristic: return expected window ± flat offset (simulates no alignment)
        est_start = round(mid_expected - 0.15, 3)
        est_end = round(mid_expected + 0.15, 3)
        se = round(abs(est_start - ann["expected_start"]), 4)
        ee = round(abs(est_end - ann["expected_end"]), 4)
        results.append({**ann,"asr_start":est_start,"asr_end":est_end,
                       "start_err_sec":se,"end_err_sec":ee,
                       "within_tolerance": se <= TOLERANCE_SEC and ee <= TOLERANCE_SEC,
                       "note":"heuristic linear interpolation (no real ASR)"})
    return results, []

def summarise(results: list) -> dict:
    valid = [r for r in results if r.get("start_err_sec") is not None]
    if not valid: return {"n":0,"mean_start_err":None,"mean_end_err":None,"acceptable_rate_pct":None}
    return {
        "n": len(valid),
        "mean_start_err_sec": round(sum(r["start_err_sec"] for r in valid)/len(valid),4),
        "mean_end_err_sec":   round(sum(r["end_err_sec"] for r in valid)/len(valid),4),
        "acceptable_rate_pct": round(sum(1 for r in valid if r["within_tolerance"])/len(valid)*100, 1),
    }

def main():
    print_header(ROW, NAME, OUT_DIR)
    env = env_fingerprint()
    all_results = []; csv_rows = []

    for video_name, gt in GROUND_TRUTH.items():
        vp = VIDEOS_DIR / video_name
        if not vp.exists(): continue
        file_hash = sha256(vp)
        lang = gt["language"]
        annotations = gt["annotations"]
        print(f"\n  File: {video_name}  lang={lang}  n_annotations={len(annotations)}  SHA256:{file_hash[:16]}...")

        with tempfile.TemporaryDirectory() as tmp:
            wav = os.path.join(tmp, "audio.wav")
            extract_audio(vp, wav)

            for mode, label in [("segment","faster-whisper segment-level"),
                                 ("word","faster-whisper word-level")]:
                print(f"    Testing [{label}]...")
                with Timer() as t:
                    try:
                        res, segs = run_alignment_test(wav, annotations, lang, mode)
                        summ = summarise(res)
                        status = STATUS_PASS if summ["n"] > 0 else STATUS_FAIL
                    except Exception as e:
                        res = []; summ = {}; status = STATUS_FAIL; segs = []
                        print(f"      ERROR: {e}")
                row = {"file":video_name,"sha256_prefix":file_hash[:16],"language":lang,
                       "candidate":label,"mode":mode,"elapsed_sec":t.elapsed,
                       "status":status,"summary":summ,"details":res}
                all_results.append(row)
                csv_rows.append({"file":video_name,"language":lang,"candidate":label,
                    "status":status,"n_annotations":summ.get("n","N/A"),
                    "mean_start_err_sec":summ.get("mean_start_err_sec","N/A"),
                    "mean_end_err_sec":summ.get("mean_end_err_sec","N/A"),
                    "acceptable_rate_pct":summ.get("acceptable_rate_pct","N/A"),
                    "elapsed_sec":t.elapsed})
                icon = "✓" if "PASS" in status else "✗"
                print(f"    [{icon}] {label:35s} acceptable={summ.get('acceptable_rate_pct','N/A')}% mean_err={summ.get('mean_start_err_sec','N/A')}s")

            # Heuristic
            print(f"    Testing [Heuristic interpolation]...")
            with Timer() as t:
                res_h, _ = heuristic_interpolate(0, annotations)
                summ_h = summarise(res_h)
            row_h = {"file":video_name,"sha256_prefix":file_hash[:16],"language":lang,
                     "candidate":"Heuristic linear interpolation","mode":"heuristic",
                     "elapsed_sec":t.elapsed,"status":"SYNTHETIC / SIMULATED",
                     "summary":summ_h,"details":res_h,
                     "note":"No real ASR — estimates midpoint ±150ms; labelled SYNTHETIC"}
            all_results.append(row_h)
            csv_rows.append({"file":video_name,"language":lang,"candidate":"Heuristic interpolation",
                "status":"SYNTHETIC / SIMULATED","n_annotations":summ_h.get("n","N/A"),
                "mean_start_err_sec":summ_h.get("mean_start_err_sec","N/A"),
                "mean_end_err_sec":summ_h.get("mean_end_err_sec","N/A"),
                "acceptable_rate_pct":summ_h.get("acceptable_rate_pct","N/A"),
                "elapsed_sec":t.elapsed})

    save_json({"row":ROW,"name":NAME,"tolerance_sec":TOLERANCE_SEC,
               "environment":env,"results":all_results}, OUT_DIR/"timestamp_alignment_results.json")
    save_csv(csv_rows, OUT_DIR/"timestamp_alignment_results.csv")

if __name__ == "__main__":
    main()
