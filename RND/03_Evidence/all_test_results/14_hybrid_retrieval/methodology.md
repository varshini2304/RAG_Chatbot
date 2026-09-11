# Row 14 Benchmark Methodology — Hybrid Retrieval

**Project:** Video-to-Bilingual Work Instruction Agent  

## Workload & Evaluation Protocol
1. **Workload:** Compare Vector-Only (ChromaDB), BM25-Only (rank-bm25), and Hybrid Retrieval (Vector + BM25 RRF score fusion in `retrieval_service.py`) across video transcript, keyframe OCR, and reference manual evidence sources.
2. **Metrics:** Exact Technical Term Recall (%), Semantic Query Accuracy (%), Multi-Evidence Source Coverage, Latency (sec).