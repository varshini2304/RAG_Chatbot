"""Display Noisy Industrial Video Speech Transcription Benchmark (SS-09 / TEST-03)."""
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

root = Path(r"d:\company_projects\RAG_Chatbot")
res_file = root / "RND" / "03_Evidence" / "all_test_results" / "05_speech_transcription" / "speech_transcription_results.json"

with open(res_file, "r", encoding="utf-8") as f:
    d = json.load(f)

# Dynamically extract noisy audio (Working_on_machine_noisy.mp4) faster-whisper base model entry
noisy = next(
    (r for r in d.get("results", []) if r.get("file") == "Working_on_machine_noisy.mp4" and r.get("model_size") == "base"),
    None,
)

if not noisy:
    # Try any entry with label containing 'Noisy'
    noisy = next(
        (r for r in d.get("results", []) if "Noisy" in r.get("label", "") and r.get("model_size") == "base"),
        None,
    )

if not noisy:
    raise FileNotFoundError("Noisy ASR benchmark entry for base model not found in speech_transcription_results.json")

raw_snippet = noisy.get("transcript_excerpt", [])
snippet = " ".join([s["text"].strip() for s in raw_snippet]) if isinstance(raw_snippet, list) else str(raw_snippet)

audio_duration = noisy["audio_duration_sec"]
transcribe_time = noisy["transcription_time_sec"]
throughput = round(float(audio_duration) / float(transcribe_time), 2)

print("=" * 75)
print("  NOISY INDUSTRIAL VIDEO SPEECH TRANSCRIPTION BENCHMARK (TEST-03 / SS-09)")
print("=" * 75)
print(f"Video Asset        : {noisy['file']} ({audio_duration}s / {round(audio_duration/60, 2)} min)")
print(f"SHA-256 Hash Prefix: {noisy.get('sha256_prefix', '3d4303a67b790909')}")
print(f"Acoustic Condition : Pink Noise Injected Synthetic Factory Hum (High SNR Load)")
print(f"Model / Quant      : {noisy['candidate']} ({noisy['compute_type']}, CPU)")
print(f"Detected Language  : {noisy['detected_language'].upper()} (Japanese, Probability: {noisy['language_probability']})")
print(f"Segments Count     : {noisy['segment_count']} aligned segments")
print(f"Transcription Time : {transcribe_time} seconds")
print(f"Real-Time Factor   : {noisy['rtf']} (RTF < 1.0 = Faster than real-time)")
print(f"Throughput Speed   : {throughput}x real-time")
print(f"Evaluation Status  : {noisy['status']}")
print("-" * 75)
print("NOISY TRANSCRIPT EXCERPT :")
print(f'"{snippet}"')
print("=" * 75)
