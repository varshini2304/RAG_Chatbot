# Evidence Directory Structure & Ground Truth Policy

This directory contains the canonical benchmark results, execution logs, and validation artifacts for all 18 R&D capability rows.

---

## Directory Organization

```
03_Evidence/
├── test_results_summary.csv        # Master auto-compiled summary table across all 18 rows
├── all_test_results/               # Canonical, re-audited test outputs (1 folder per row)
│   ├── 01_video_input/             # JSON, CSV, and full execution .log
│   ├── 02_video_validation/        # JSON, CSV, and full execution .log
│   ├── 03_audio_processing/        # JSON, CSV, and full execution .log
│   ├── 04_visual_processing/       # JSON, CSV, and full execution .log
│   ├── 05_speech_transcription/    # JSON, CSV, and full execution .log
│   ├── 06_transcript_alignment/    # JSON, CSV, and full execution .log
│   ├── 07_work_step/               # JSON, CSV, and full execution .log
│   ├── 08_keyframe_selection/      # JSON, CSV, and full execution .log
│   ├── 09_visual_information/      # JSON, CSV, and full execution .log
│   ├── 10_safety_detection/        # JSON, CSV, and full execution .log
│   ├── 11_ocr/                     # JSON, CSV, and full execution .log
│   ├── 12_document_ingestion/      # JSON, CSV, and full execution .log
│   ├── 13_embedding_retrieval/     # JSON, CSV, and full execution .log
│   ├── 14_hybrid_retrieval/        # JSON, CSV, and full execution .log
│   ├── 15_conflict_detection/      # JSON, CSV, and full execution .log
│   ├── 16_human_conflict_resolution/# JSON, CSV, and full execution .log
│   ├── 17_bilingual_generation/    # JSON, CSV, and full execution .log
│   └── 18_visual_sop/              # JSON, CSV, and full execution .log
└── screenshots/                    # UI & evaluation screenshots
```

---

## Execution Logs Included

All 18 capability evaluation rows include their full, unedited execution log files (`ROW_01_*.log` through `ROW_18_*.log`) alongside the structured `.json` and `.csv` benchmark outputs in their respective subdirectories under `all_test_results/`.

---

## YOLOv8n Evaluation Note (Row 09)

* **Execution Status:** YOLOv8n (v8.4.127) **was evaluated on CPU** across the 4 keyframes using general COCO 80-class pretrained weights.
* **Empirical Finding:** It detected 2 general COCO objects (`person` conf 0.82, `tie` conf 0.73) on `OpenCV_ts_10.0s.jpg` and 0 objects on the other 3 keyframes.
* **Domain Limitation:** Because standard COCO weights lack manufacturing annotations, it detected zero industrial tools, machine components, or PPE items.

---

## Ground Truth Immutability Rule

All JSON, CSV, and log files within `all_test_results/` are generated directly by benchmark execution. They are preserved as read-only historical records and compiled via `compile_master_results.py` into `test_results_summary.csv`.
