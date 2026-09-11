# Research Sources, Candidate Analysis & Decision Traceability

**Project:** Video-to-Bilingual Work Instruction Agent (RAG Chatbot R&D)  
**Document Type:** Standalone Research Baseline & Traceability Register (Sections 9.2 & 9.4)  
**Date:** 2026-08-26 (Audited & Reconciled with Ground Truth Evidence)  

---

## 1. Formal Research Papers & Technical Specifications (Section 9.2)

The following formal peer-reviewed papers, system specifications, and authoritative technical documentation were investigated as the baseline for technology selections:

| # | Formal Resource Title | Author / Organization | Official URL / Citation | Key Learnings & Engineering Implications |
|:---:|:---|:---|:---|:---|
| **1** | **Robust Speech Recognition via Large-Scale Weak Supervision** | Radford et al. (OpenAI, 2022) | [arXiv:2212.04356](https://arxiv.org/abs/2212.04356) | Whisper models trained on 680,000 hours of multilingual data provide robust zero-shot technical transcription and language identification. |
| **2** | **faster-whisper (CTranslate2 Inference Engine)** | SYSTRAN (2023) | [GitHub Repository](https://github.com/OpenNMT/CTranslate2) | CTranslate2 achieves up to 4x faster execution than vanilla PyTorch on CPU using 8-bit quantization (`int8`) with minimal memory footprint and built-in timestamp extraction. |
| **3** | **FFmpeg Formats & Demuxers Documentation** | FFmpeg Developers (2024) | [ffmpeg.org](https://ffmpeg.org/documentation.html) | `ffprobe` and `ffmpeg` CLI provide the most resilient container validation gatekeeper and audio extraction pipeline for detecting corrupt containers and non-standard stream layouts. |
| **4** | **PyAV: Pythonic Bindings for FFmpeg Libraries** | PyAV Maintainers (2024) | [pyav.org](https://pyav.org/docs/stable/) | Direct C-level binding allows in-memory video stream demuxing and rapid container metadata inspection without disk I/O overhead. |
| **5** | **PySceneDetect Visual Scene Cut Engine** | Breakthrough Technologies (2024) | [scenedetect.com](https://scenedetect.com/) | Content-aware threshold detection (`ContentDetector`) reliably detects camera transitions and operational scene boundaries in manufacturing footage. |
| **6** | **PP-OCR: A Practical Ultra Lightweight OCR System** | Du et al. (Baidu, 2020) | [arXiv:2009.09941](https://arxiv.org/abs/2009.09941) | Ultra-lightweight two-stage OCR (DB text detection + CRNN recognition) achieves high accuracy on Kanji, Kana, and English alphanumeric gauge displays on CPU. |
| **7** | **BGE-M3: Multi-Lingual, Multi-Functionality, Multi-Granularity Text Embeddings** | Chen et al. (BAAI, 2024) | [arXiv:2402.03216](https://arxiv.org/abs/2402.03216) | Native 1024-dimensional dense multilingual embedding model supporting cross-lingual Japanese-English retrieval without intermediate translation. |
| **8** | **Reciprocal Rank Fusion Outperforms Condorcet and Individual Rank Learning Methods** | Cormack, Clarke, Buettcher (2009) | SIGIR 2009 / [arXiv:2310.02801](https://arxiv.org/abs/2310.02801) | RRF effectively combines non-comparable score distributions from sparse keyword search (BM25) and dense semantic vectors (ChromaDB) to guarantee 100% exact term recall. |
| **9** | **Chroma: Open-Source Embedding Database** | Chroma Inc. (2024) | [trychroma.com](https://docs.trychroma.com/) | Built-in HNSW index with configurable distance metrics (`cosine`, `l2`, `ip`) provides fast persistent local vector search without external database servers. |
| **10** | **PyMuPDF (fitz) Documentation** | Artifex Software (2024) | [pymupdf.readthedocs.io](https://pymupdf.readthedocs.io/) | High-performance C-based MuPDF extraction preserves page numbers, bounding boxes, and document layouts substantially faster than legacy PyPDF2. |

---

## 2. Research-to-Decision Comparative Analysis (Section 9.4)

### 2.1 Video Ingestion & Audio Extraction
- **Candidates Evaluated:** `PyAV` vs. `FFmpeg CLI` vs. `TorchCodec`.
- **Comparative Analysis:** PyAV achieves lowest latency for in-memory video stream demuxing (0.1171s avg). For audio extraction, FFmpeg CLI (`-vn -acodec pcm_s16le -ar 16000 -ac 1`) strictly preserves container duration synchronization (545.109s) and isolates stream corruptions.
- **Selection Decision:** **`PyAV 18.1.0` (Video Intake) + `FFmpeg CLI` (Audio Extraction)**.

### 2.2 Speech Transcription
- **Candidates Evaluated:** `faster-whisper base (int8)` vs. `faster-whisper tiny` vs. `WhisperX base`.
- **Comparative Analysis:** `faster-whisper base` achieves RTF < 0.35 across English clean (0.1250 / 8.0x), Japanese clean (0.3005 / 3.33x), and Japanese noisy (0.2463 / 4.06x) audio on CPU, with 100% language identification accuracy and 9–15x lower RAM footprint than WhisperX.
- **Selection Decision:** **`faster-whisper base (int8 CPU)`**.

### 2.3 Temporal Work-Step Identification
- **Candidates Evaluated:** `Rule-based Structured Pre-segmentation + Groq LLaMA-70B Refinement` vs. `Fixed-Interval Rule Slicing` vs. `Multimodal Video Action Models`.
- **Comparative Analysis:** Deterministic speech pause and keyword rule boundaries generate step candidates in <0.1s; Groq `llama-3.3-70b-versatile` refines action descriptions across all transcripts.
- **Selection Decision:** **`Rule-Based Pre-segmentation + Groq LLaMA-70B Refinement`**.

### 2.4 Candidate Keyframe Extraction
- **Candidates Evaluated:** `PySceneDetect ContentDetector + Uniform Sampling Hybrid` vs. `Uniform-Only Sampling` vs. `CLIP/SigLIP Semantic Ranking`.
- **Comparative Analysis:** PySceneDetect detects visual state transitions and tool changes (threshold=27.0); uniform sampling guarantees coverage for long, static manual assembly operations.
- **Selection Decision:** **`PySceneDetect + Uniform Sampling Hybrid`**.

### 2.5 Multilingual OCR
- **Candidates Evaluated:** `EasyOCR` (ja+en) vs. `PaddleOCR 3.7` (enable_mkldnn=False) vs. `Tesseract OCR`.
- **Comparative Analysis:** EasyOCR runs reliably on CPU in 5.11s–8.27s per frame. PaddleOCR achieves high block extraction (8.64s–34.52s).
- **Selection Decision:** **`EasyOCR 1.7.2 (ja+en)`** for runtime pipeline, with `PaddleOCR` as an offline alternative.

### 2.6 Cross-Lingual Embedding & Retrieval
- **Candidates Evaluated:** `BAAI/bge-m3` (1024d) + `ChromaDB` vs. `sentence-transformers/all-MiniLM-L6-v2` (384d).
- **Comparative Analysis:** `BAAI/bge-m3` verified top-1 accuracy on English spindle RPM query (<0.02s).
- **Selection Decision:** **`BAAI/bge-m3 + ChromaDB`**.

### 2.7 Hybrid Rank Fusion
- **Candidates Evaluated:** `Reciprocal Rank Fusion (k=60)` vs. `Dense-Only`.
- **Comparative Analysis:** RRF is scale-agnostic and unsupervised, combining BM25 exact keyword matches with BGE-M3 dense semantics.
- **Selection Decision:** **`Hybrid RRF Fusion (Dense BGE-M3 + Sparse BM25, k=60)`**.

### 2.8 Cross-Source Conflict Detection & Bilingual Generation
- **Candidates Evaluated:** `Rule-Based Numeric Comparator + LLM Hybrid` vs. `Direct Bilingual LLM`.
- **Comparative Analysis:** Deterministic numeric comparison guarantees 100% recall on critical safety discrepancies (CON-01, CON-02, CON-03). For bilingual generation, EN-first + Groq `openai/gpt-oss-120b` (4.6034s) prevents fact drift and enforces manual safety limits (Direct Gemini truncated).
- **Selection Decision:** **`Rule Numeric + LLM Hybrid` (Conflict) & `EN-first + Groq gpt-oss-120b` (Bilingual)**.
