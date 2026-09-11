# RND/03_Evidence/all_test_results — 18-Row Benchmark Results

All JSON and log evidence files are **real executed outputs** from the benchmark scripts in `RND/benchmark_scripts/`.  
Zero hallucination policy enforced: no evidence file was hand-written or synthesized.

---

## Directory Map

| Folder | Row | Capability | Key Script | Evidence Status |
|:---|:---:|:---|:---|:---:|
| `01_video_input/` | Row 01 | Video Input & Ingestion | `row_01_video_input.py` | ✅ PASS — REAL TESTED (PyAV 7/7) |
| `02_video_validation/` | Row 02 | Video Validation & Metadata | `row_02_video_validation.py` | ✅ PASS — REAL TESTED (8/8 matched) |
| `03_audio_processing/` | Row 03 | Audio Extraction & Resampling | `row_03_audio_extraction.py` | ✅ PASS — REAL TESTED (FFmpeg CLI) |
| `04_visual_processing/` | Row 04 | Visual Processing & Frame Seeking | `row_04_frame_seeking.py` | ✅ PASS — REAL TESTED (OpenCV 36/36) |
| `05_speech_transcription/` | Row 05 | Speech Transcription (ASR) | `row_05_speech_transcription.py` | ✅ PASS — REAL TESTED (faster-whisper base) |
| `06_transcript_alignment/` | Row 06 | Timestamp Alignment | `row_06_timestamp_alignment.py` | ✅ PASS — REAL TESTED (Word-level sync) |
| `07_work_step/` | Row 07 | Work-Step Identification | `row_07_work_step.py` | ✅ PASS — REAL TESTED (Rule + Groq LLaMA-70B) |
| `08_keyframe_selection/` | Row 08 | Candidate Keyframe Selection | `row_08_keyframe_selection.py` | ✅ PASS — REAL TESTED (PySceneDetect + Uniform) |
| `09_visual_information/` | Row 09 | Visual Information & Object ID | `row_09_visual_information.py` | ⚠️ PARTIAL — VLM task failure (0/15 keywords) |
| `10_safety_detection/` | Row 10 | Safety & Checkpoint Detection | `row_10_safety_detection.py` | ✅ PASS — Rule verified (12/12 claims); VLM failed |
| `11_ocr/` | Row 11 | OCR Text Extraction | `row_11_ocr.py` | ✅ PASS — REAL TESTED (EasyOCR 4/4) |
| `12_document_ingestion/` | Row 12 | Document Ingestion Pipeline | `rows_12_to_18.py` | ✅ PASS — REAL TESTED (PyMuPDF 3/3) |
| `13_embedding_retrieval/` | Row 13 | Chunking & Vector Retrieval | `rows_12_to_18.py` | ⚠️ PARTIAL — EN verified; JA not validated |
| `14_hybrid_retrieval/` | Row 14 | Hybrid Retrieval & RRF Fusion | `rows_12_to_18.py` | ⚠️ PARTIAL — EN verified; JA not validated |
| `15_conflict_detection/` | Row 15 | Cross-Source Conflict Detection | `rows_12_to_18.py` | ✅ PASS — REAL TESTED (3/3 cases) |
| `16_human_conflict_resolution/` | Row 16 | Human Conflict Confirmation (HITL) | `rows_12_to_18.py` | ✅ PASS — REAL TESTED (SHA-256 audit) |
| `17_bilingual_generation/` | Row 17 | Bilingual Work Instruction Generation | `rows_12_to_18.py` | ✅ PASS — REAL TESTED (EN-first + Groq 4.60s) |
| `18_visual_sop/` | Row 18 | Visual SOP Generation & Traceability | `rows_12_to_18.py` | ✅ PASS — REAL TESTED (Groq 7/7 fields) |

---

## Test Asset Reference

All benchmarks run against these verified assets:

### Video Files (in `RND/docs_and_video/videos/`)
| File | Language | Purpose |
|:---|:---:|:---|
| `test_instructional_normal.mp4` | 🇬🇧 English | Normal instructional (milling machine) |
| `const_01.mp4` | 🇯🇵 Japanese | Japanese construction safety lecture |
| `Working on machine.mp4` | 🇯🇵 Japanese | Byte-identical duplicate of const_01.mp4 |
| `Working_on_machine_noisy.mp4` | 🇯🇵 Japanese | Noisy audio benchmark asset |
| `controlled_synthetic_corrupt.mp4` | 🇬🇧 English | Synthetic corrupt audio stream (test error handling) |
| `controlled_vfr_test.mp4` | 🇬🇧 English | Variable frame rate test |
| `...vp9.webm` | Mixed | VP9 WebM industrial video |

### PDF Documents (in `RND/docs_and_video/documents/`)
| File | Purpose |
|:---|:---|
| `milling_machine_operating_manual.pdf` | Primary SOP document (conflict detection source) |
| `aetheris_diagrams_and_infrastructure.pdf` | Infrastructure reference PDF |
| `alpha_asset_and_visitors.pdf` | Asset management policy PDF |

---

## Key Findings Summary

| Topic | Finding |
|:---|:---|
| **Row 07 Groq LLM** | Ran on all 3 transcripts (12.3s–15.0s per transcript). Model: `llama-3.3-70b-versatile` |
| **Row 09 Gemini VLM** | Genuine task failure (0/15 keywords found across 4 frames); API responded normally |
| **Row 09 YOLOv8n** | Evaluated on CPU with COCO weights; detected person & tie on 10.0s frame (0 industrial tools) |
| **Row 13/14 Japanese** | NOT validated — BM25 cannot tokenize Japanese; corpus has no matching JA content |
| **Row 17 Bilingual** | EN-first + Groq `openai/gpt-oss-120b` passed in 4.6034s; Direct Gemini truncated (10.23s PARTIAL) |
| **Row 18 Groq SOP** | `openai/gpt-oss-120b` generated 7/7 schema fields; frame grounding is `PARTIAL_TEXT_ONLY` |
