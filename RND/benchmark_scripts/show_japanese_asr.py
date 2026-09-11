"""Display Japanese Video Speech Transcription Benchmark (SS-08 / TEST-02)."""
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

root = Path(r"d:\company_projects\RAG_Chatbot")
res_file = root / "RND" / "03_Evidence" / "all_test_results" / "05_speech_transcription" / "speech_transcription_results.json"

with open(res_file, "r", encoding="utf-8") as f:
    d = json.load(f)

# Dynamically extract Japanese ASR base model entry directly from speech_transcription_results.json
ja = next((r for r in d.get("results", []) if r.get("detected_language") == "ja" and r.get("model_size") == "base"), None)

if not ja:
    raise FileNotFoundError("Japanese ASR results for base model not found in speech_transcription_results.json")

raw_snippet = ja.get("transcript_excerpt", [])
snippet = " ".join([s["text"].strip() for s in raw_snippet]) if isinstance(raw_snippet, list) else str(raw_snippet)

audio_duration = ja["audio_duration_sec"]
transcribe_time = ja["transcription_time_sec"]
throughput = round(float(audio_duration) / float(transcribe_time), 2)

print("=" * 75)
print("  JAPANESE VIDEO SPEECH TRANSCRIPTION BENCHMARK (TEST-02 / SS-08)")
print("=" * 75)
print(f"Video Asset        : {ja['file']} ({audio_duration}s / {round(audio_duration/60, 2)} min)")
print(f"Audio Track        : 16kHz mono PCM (Resampled via PyAV)")
print(f"Model / Quant      : {ja['candidate']} ({ja['compute_type']}, CPU)")
print(f"Detected Language  : {ja['detected_language'].upper()} (Japanese, Probability: {ja['language_probability']})")
print(f"Segments Count     : {ja['segment_count']} aligned segments")
print(f"Transcription Time : {transcribe_time} seconds")
print(f"Real-Time Factor   : {ja['rtf']} (RTF < 1.0 = Faster than real-time)")
print(f"Throughput Speed   : {throughput}x real-time")
print("-" * 75)
print("JAPANESE TRANSCRIPT EXCERPT :")
print(f'"{snippet}"')
print("=" * 75)
