# Effort & Implementation Timeline (8 Hours/Day Standard Schedule)

## 1. Project Work Schedule & Calendar Constraints (8 Hours/Day)

* **Working Hours:** Monday through Friday (**8 hours/day**, full-time engineering schedule). Saturdays and Sundays strictly excluded.
* **Observed Holidays (2026):**
  * **Friday, 21 August 2026:** Varamahalakshmi Festival (Observed)
  * **Monday, 14 September 2026:** Ganesh Chaturthi (Observed)
* **Key Milestones:**
  * **Thu 27 Aug 2026:** R&D Report Submission & Initial Review by Veeru sir
  * **Fri 28 Aug 2026:** Final R&D Changes & Review Sign-Off
  * **Mon 31 Aug 2026:** Step 1 Completion Target
  * **Tue 01 Sep 2026:** Phase 2 Prototype Development Kickoff (Step 2)
  * **Tue 10 Nov 2026:** Final End-to-End Prototype Delivery Target (**60 Working Days / 480 Total Hours**)

---

## 2. Master 11-Step Summary Schedule Table

| Step # | Stage / Component Area | Working Days | Total Hours (8h/day) | Start Date | Completion Target | Risk Basis (from R&D Evidence) |
|:---:|:---|:---:|:---:|:---:|:---:|:---|
| **Step 1** | Requirement Analysis & R&D Scope Finalization | 10 | 80 | Mon 17-Aug-2026 | **Mon 31-Aug-2026** | Low — scope defined, benchmarks executed |
| **Step 2** | Environment & Video Stream Ingestion | 3 | 24 | Tue 01-Sep-2026 | Thu 03-Sep-2026 | **Low** — Rows 01–02 at 100% across all stream variants |
| **Step 3** | Audio Extraction, ASR & Timestamp Synchronization | 5 | 40 | Fri 04-Sep-2026 | Thu 10-Sep-2026 | **Low-Moderate** — Row 03 well-tested; minor buffer for edge-case audio formats |
| **Step 4** | Work-Step Identification & Keyframe Extraction | 5 | 40 | Fri 11-Sep-2026 | Fri 18-Sep-2026 | **Moderate** — EN word-level sync only 57.1% within ±0.5s (Row 06); JA at 100% |
| **Step 5** | Visual Feature Extraction, OCR & Safety Checkpoints | 5 | 40 | Mon 21-Sep-2026 | Fri 25-Sep-2026 | **High** — Step-boundary accuracy pending ground truth (Row 07, Section 35) |
| **Step 6** | RAG Document Pipeline & Hybrid RRF Retrieval | 5 | 40 | Mon 28-Sep-2026 | Fri 02-Oct-2026 | **High** — JA BM25 retrieval not validated; tokenization gap (MeCab/SudachiPy) unresolved (Row 14) |
| **Step 7** | Cross-Source Conflict Detection & Bilingual SOP Generation | 6 | 48 | Mon 05-Oct-2026 | Mon 12-Oct-2026 | **High** — Expert-quality bilingual validation explicitly pending; highest named risk (Row 17, Section 36) |
| **Step 8** | Human-in-the-Loop Approval & Governance Workflow | 5 | 40 | Tue 13-Oct-2026 | Mon 19-Oct-2026 | **Moderate** — Rules validated on n=12 (safety) and n=3 (conflict) only; scale brittleness risk |
| **Step 9** | End-to-End Pipeline Integration & Dry-Run Testing | 6 | 48 | Tue 20-Oct-2026 | Tue 27-Oct-2026 | **High** — First full end-to-end run; hidden integration bugs expected (Row 18) |
| **Step 10** | Bug Fixes, Licensing, Security & Documentation | 5 | 40 | Wed 28-Oct-2026 | Tue 03-Nov-2026 | **Moderate** — Scope depends on defects surfaced in Step 9 |
| **Step 11** | Final Evaluation, Validation Report & Delivery | 5 | 40 | Wed 04-Nov-2026 | **Tue 10-Nov-2026** | **Low** — Scope-bounded activities; no open technical unknowns at this stage |
| **Total** | **End-to-End R&D to Working Prototype Lifecycle** | **60 Days** | **480 Hours** | **17-Aug-2026** | **10-Nov-2026** | — |

---

## 3. Comprehensive Step-by-Step Breakdown

### Step 1: Requirement / Existing System Analysis & R&D Scope
* **Scope:** Audit existing RAG codebase in `apps/internal-document-rag/`, map reusable components, finalize empirical R&D benchmark findings, and incorporate senior engineering review.
* **Timeline:** 17 August 2026 – 31 August 2026 (10 Working Days / 80 Hours)
* **Milestones:**
  * 17–26 Aug 2026: Empirical benchmark execution & capability validation.
  * 27 Aug 2026: R&D Report submission and initial review.
  * 28–31 Aug 2026: Final R&D changes, audit reconciliation, and review sign-off.
* **Completion Target:** 31 August 2026

---

### Step 2: Environment & Video Stream Ingestion (Rows 01–02)
* **Scope:** Set up isolated Python 3.11 environment, integrate PyAV stream intake, and implement ffprobe container validation gatekeeper.
* **Timeline:** 01 September 2026 – 03 September 2026 (3 Working Days / 24 Hours)
* **Risk Level:** Low — Rows 01–02 achieved 100% accuracy across all 7 file variants. No open gaps.
* **Buffer Trigger:** N/A — if a new container format fails validation, resolve within existing allocation.
* **Completion Target:** 03 September 2026

---

### Step 3: Audio Extraction, ASR & Timestamp Synchronization (Rows 03, 05–06)
* **Scope:** Build FFmpeg CLI 16kHz mono `pcm_s16le` extraction pipeline, integrate faster-whisper base int8 on CPU, and implement word-level timestamp alignment.
* **Timeline:** 04 September 2026 – 10 September 2026 (5 Working Days / 40 Hours)
* **Risk Level:** Low-Moderate — Row 03 well-tested on all formats including corrupt-stream rejection. EN word-level sync at 57.1% within ±0.5s (Row 06) may require rework.
* **Buffer Trigger:** Activate contingency if EN word-level accuracy remains below 70% after the initial implementation pass, or if a new audio format produces duration mismatches exceeding 5%.
* **Completion Target:** 10 September 2026

---

### Step 4: Work-Step Identification & Keyframe Extraction (Rows 04, 07–08)
* **Scope:** Implement speech pause and domain marker rule segmentation, integrate Groq LLaMA-70B, and deploy PySceneDetect hybrid keyframe extractor.
* **Timeline:** 11 September 2026 – 18 September 2026 (5 Working Days / 40 Hours; excludes 14 Sep Ganesh Chaturthi holiday)
* **Risk Level:** Moderate — Step-boundary accuracy is pending ground truth (Row 07, Section 35). Keyframe ranking quality is unvalidated (Row 08). The R&D pilot produced 6–20 steps and 9–18 keyframes per video with no ground truth to confirm correctness.
* **Buffer Trigger:** Activate contingency if ground-truth annotation reveals step-boundary precision below 60%, or if keyframe selection produces duplicate/uninformative frames above 20% in expert review.
* **Completion Target:** 18 September 2026

---

### Step 5: Visual Feature Extraction, OCR & Safety Checkpoints (Rows 09–11)
* **Scope:** Deploy OpenCV ORB+MSER keypoint detector on CPU, integrate EasyOCR 1.7.2, and implement deterministic Rule-Based Safety Engine.
* **Timeline:** 21 September 2026 – 25 September 2026 (5 Working Days / 40 Hours)
* **Risk Level:** High — Both OCR engines (EasyOCR and PaddleOCR) achieved only 30% keyword recall on the 4-frame test set (Row 11). Real improvement work — not just integration — is required to reach acceptable recall on production frames.
* **Buffer Trigger:** Activate contingency if EasyOCR keyword recall remains below 60% on a 10-frame validation set, or if Japanese gauge text recognition requires a specialised pre-processing step.
* **Completion Target:** 25 September 2026

---

### Step 6: RAG Document Pipeline & Hybrid RRF Retrieval (Rows 12–14)
* **Scope:** Integrate PyMuPDF loader, BGE-M3 embedding service, ChromaDB, BM25, and Hybrid RRF ($k=60$). **Explicitly includes:** decision and implementation of a Japanese tokenizer (MeCab or SudachiPy) to resolve the BM25 Japanese retrieval gap identified in Row 14.
* **Timeline:** 28 September 2026 – 02 October 2026 (5 Working Days / 40 Hours)
* **Risk Level:** High — Japanese BM25 retrieval is not validated; whitespace tokenisation scores 0.0 on all Japanese queries (Row 14). A Japanese tokenizer must be evaluated, selected, and integrated before Japanese hybrid retrieval can be considered functional. This task was not listed in the original plan and is explicitly added here.
* **Buffer Trigger:** Activate contingency if Japanese BM25 recall with MeCab/SudachiPy tokenisation remains below 66% on the pilot query set, or if the tokenizer introduces incompatible dependencies on the target deployment environment.
* **Completion Target:** 02 October 2026

---

### Step 7: Cross-Source Conflict Detection & Bilingual SOP Generation (Rows 15–17)
* **Scope:** Implement deterministic numeric comparator and Groq bilingual SOP generator with fact-drift validation.
* **Timeline:** 05 October 2026 – 12 October 2026 (6 Working Days / 48 Hours)
* **Risk Level:** High — Expert-quality bilingual validation remains explicitly pending (Row 17, Section 36). The pipeline passes automated fact-drift checks (0/10 errors) but has not been reviewed by a real bilingual domain expert. This is the highest named risk in the R&D report.
* **Buffer Trigger:** Activate contingency if a bilingual domain expert review identifies terminology errors, Japanese phrasing inconsistencies, or safety instruction ambiguity requiring rework of the generation prompt or translation parameters.
* **Completion Target:** 12 October 2026

---

### Step 8: Human-in-the-Loop Approval & Governance Workflow (Row 16)
* **Scope:** Build Streamlit review UI, Expert Review approval gate, and SHA-256 audit logger.
* **Timeline:** 13 October 2026 – 19 October 2026 (5 Working Days / 40 Hours)
* **Risk Level:** Moderate — Deterministic rule engine validated on n=12 (safety claims) and n=3 (conflict cases). Both sample sizes are small; a keyword-based engine is brittle by nature and may require rule expansion for production vocabulary coverage.
* **Buffer Trigger:** Activate contingency if rule expansion for a new video domain requires more than 4 hours of taxonomy work, or if the LLM conflict explainer produces inconsistent outputs on a numeric type not covered in the 3-case pilot.
* **Completion Target:** 19 October 2026

---

### Step 9: End-to-End Pipeline Integration & Dry-Run Testing (Row 18)
* **Scope:** Connect all pipeline stages into a unified video-to-SOP workflow across EN, JA, and Noisy videos.
* **Timeline:** 20 October 2026 – 27 October 2026 (6 Working Days / 48 Hours)
* **Risk Level:** High — This is the first time all pipeline components run together end-to-end. Hidden integration bugs (timing mismatches, schema contract failures, frame-to-step linkage gaps) are expected and cannot be fully predicted until the full pipeline is assembled.
* **Buffer Trigger:** Activate contingency if end-to-end pipeline produces schema validation failures on more than 2 of 7 SOP fields, or if a complete re-run of any upstream pipeline stage is required to correct grounding errors.
* **Completion Target:** 27 October 2026

---

### Step 10: Bug Fixes, Licensing, Security & Documentation
* **Scope:** Resolve integration defects, perform software license audits, and author user documentation.
* **Timeline:** 28 October 2026 – 03 November 2026 (5 Working Days / 40 Hours)
* **Risk Level:** Moderate — Defect resolution and documentation scope depend on the number of integration-stage bugs surfaced in Step 9. Allocated time is sized for a small set of known unknowns.
* **Buffer Trigger:** Activate contingency if more than 3 integration defects from Step 9 require changes to core pipeline logic (not just configuration).
* **Completion Target:** 03 November 2026

---

### Step 11: Final Evaluation, Validation Report & Delivery
* **Scope:** Execute validation set, verify dual-grounded SOP exports, and complete project sign-off.
* **Timeline:** 04 November 2026 – 10 November 2026 (5 Working Days / 40 Hours)
* **Risk Level:** Low — Validation, sign-off, and delivery are scope-bounded activities. No open technical unknowns remain at this stage.
* **Buffer Trigger:** N/A — no contingency allocated. Any remaining defects from Step 9 should have been resolved in Step 10.
* **Completion Target:** 10 November 2026
