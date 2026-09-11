# Internal Document RAG Chatbot

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.x-red)
![ChromaDB](https://img.shields.io/badge/Vector_DB-ChromaDB-green)
![LangChain](https://img.shields.io/badge/LangChain-Enabled-success)
![License](https://img.shields.io/badge/License-Academic-lightgrey)

A Retrieval-Augmented Generation (RAG) prototype for question answering over internal PDF and TXT documents. The application combines semantic retrieval with large language models (LLMs) to generate answers from uploaded document content while providing source references. Built in Python, styled with a light glassmorphic Streamlit interface, it includes login and saved chat history as prototype features.

> [!IMPORTANT]
> **Data Processing Notice**: Text extraction, chunking, embedding generation, and ChromaDB vector database storage run entirely **locally on your machine**. The retrieved document text passages are then sent to external API providers (Google Gemini or Groq) for answer generation. No raw documents are stored externally.

---

## **Project Workflow**

```text
Upload Documents
↓
Validate Files (Size < 50MB, formats)
↓
Extract Text (PyMuPDF)
↓
Chunk Documents (Recursive Character Splitter)
↓
Generate Embeddings (Sentence Transformers)
↓
Store in ChromaDB (Vector Store)
↓
User Question
↓
Query Preprocessor (Text Standardization)
↓
Parallel Retrieval: Semantic Search (ChromaDB) + Keyword Search (BM25)
↓
Reciprocal Rank Fusion (RRF) Re-ranking
↓
Build Prompt Context (Top-K Chunks)
↓
LLM Provider (Gemini / Groq)
↓
Generate Context-Aware Answer
↓
Display Answer with Source References
```

---

## **Multimodal Image & Diagram Support**

The system processes embedded figures, system architecture charts, flowcharts, and technical diagrams from PDF documents:

1. **Extraction**: `ImageExtractor` uses PyMuPDF (`fitz`) to locate and extract embedded raster images ($\ge 80 \times 80\text{px}$) from PDF pages, computing SHA-256 hashes for deduplication and saving them to disk (`data/images/`).
2. **Vision Captioning Hierarchy**: `VisionService` generates rich text captions for extracted images using a 3-tier prioritized fallback pipeline:
   * **Tier 1 (Cloud Vision)**: Google Gemini 2.5 Flash (`gemini-2.5-flash` via Google GenAI SDK).
   * **Tier 2 (Local Vision)**: Ollama Vision (`llava:latest` or `qwen2.5-vl` via HTTP API).
   * **Tier 3 (Local Fallback)**: Visual OCR & pixel label analysis (`pytesseract` / `easyocr` pixel scanning + layout bounding box descriptions).
3. **Indexing & Vectorization**: Captioned images become `DocumentChunk` instances of `ChunkType.IMAGE`. They are embedded using Sentence Transformers (`BAAI/bge-m3`) and indexed simultaneously into **ChromaDB** and the **BM25 corpus** alongside textual chunks, with preserved `image_path` and `image_hash` metadata.

---

## **System Architecture**

The application uses a local Retrieval-Augmented Generation (RAG) flow. Document text is split, vectorized, and indexed in ChromaDB. During user queries, semantic similarity matches are retrieved to build a grounded context for answer generation. The architecture separates document ingestion, embedding generation, vector storage, retrieval, and answer generation into independent modules. For full sequence flowcharts, refer to the [System Architecture Section](docs/project_documentation.md#8-system-architecture).

---

## **Application Preview**

### Login & Registration Gateway
```text
+---------------------------------------------------------+
|                  DOCUMENT RAG PORTAL                    |
|                [Sign In]  |  [Register]                 |
|  +---------------------------------------------------+  |
|  |  Username: [ Enter username                      ] |  |
|  |  Password: [ Enter password                      ] |  |
|  |  [               Sign In / Register  →          ] |  |
|  +---------------------------------------------------+  |
+---------------------------------------------------------+
```

### RAG Chatbot & Management Dashboard
```text
+------------------------+----------------------------------------------------+
|  SIDEBAR               |  HEADER & TELEMETRY                                |
|  - Profile (User)      |  [Docs: 3] [Chunks: 10] [Provider: Groq]            |
|  - Drag & Drop Upload  |----------------------------------------------------|
|  - [📂 View Documents]  |  CHAT FEED                                         |
|  - [🗑️ Clear Workspace]|  [User]: Ask a question about your documents...    |
|  - Chat Sessions       |  [Assistant]: Grounded response + citations        |
|  - [🚪 Sign Out]       |  [Source References (5)]                           |
+------------------------+----------------------------------------------------+
```

### **Core RAG Scope**
* **Document Ingestion & Validation**: Upload PDFs and TXT files under a toggleable sidebar display. Files are validated (size limit <50MB) and indexed.
* **SHA-256 Duplicate Detection**: Checks file hashes before processing to identify duplicate document uploads.
* **Recursive Character Chunking**: Splits text into semantic segments with metadata tracking (source name, page number, document type, chunk ID).
* **Dense Vector Database Indexing**: Local storage using ChromaDB with idempotent upsert support (cosine metric).
* **Context-Grounded QA**: Generates responses using retrieved document context and returns an insufficient-information response when relevant context is unavailable.
* **Source References Citations**: Renders reference panels listing source names, page numbers, and snippet previews for all retrieved contexts.

### **Additional Enhancements (Outside Original Scope)**
* **FastAPI REST API Layer (`/api/v1`)**: Backend REST services powering authentication, telemetry, analytics, system health monitoring, provider circuit breaker controls, and enterprise reporting.
* **Enterprise Excel Report Generator**: Generates a 6-sheet `.xlsx` report using `openpyxl` (`/api/v1/export/report`) covering operational KPIs, provider analytics, system health status, user activity, error logs, and configuration snapshots.
* **Sign-In Authentication Endpoint**: `/api/v1/auth/login` validates credentials against server-side `USER_CREDENTIALS` (Sign-In Only for Admin Console).
* **Hybrid Search (BM25 + Semantic)**: Combines dense vector similarity search (ChromaDB) with sparse keyword matching (BM25) using Reciprocal Rank Fusion (RRF) to query both sparse and dense representations.
* **Incremental BM25 Index Rebuilding**: Manages a per-user BM25 index on disk, caching it in memory during retrieval and updating it incrementally strictly on ingestion mutations (adds/removes).
* **Query Preprocessing**: Standardizes input strings, handles whitespace/punctuation, and cleans up queries prior to execution.
* **Access Control & Session Management**: User authentication portal with session state caching and isolated user workspaces (supports both Sign-In and Sign-Up / registration).
* **Multilingual Retrieval with Japanese Support**: Supports queries and document ingestion in Japanese and English. Automatically detects query language (using `lingua-py`), constructs language-aware prompts, and displays localized user-facing responses.
* **Persistent Chat History**: Automatically writes and restores conversation logs to disk under `data/chats/{username}_history.json`, with loading and deletion controls.

---

## **Technology Stack**

| Technology | Purpose |
| :--- | :--- |
| **FastAPI** | REST API layer (`/api/v1`) for admin management, monitoring, and export services |
| **Streamlit** | Interactive web dashboard and user interface |
| **PyMuPDF (fitz)** | Selected for efficient page-level text extraction from PDF documents |
| **LangChain** | Recursive character text chunking |
| **Sentence Transformers** | Multilingual semantic embedding model (`BAAI/bge-m3` by default) |
| **ChromaDB** | Local vector database for persistent storage and semantic retrieval of document embeddings |
| **openpyxl** | Multi-sheet Enterprise Excel report generation (`.xlsx`) |
| **rank_bm25** | Keyword-based sparse retrieval matching algorithm for hybrid search |
| **Gemini 2.5 Flash / Groq / Ollama** | Context-grounded answer generation & LLM provider failover |
| **Tenacity** | Retry engine handling API quota rate-limiting |
| **lingua-py** | Lightweight language detector for routing queries and prompts |
| **Pytest** | Testing framework for unit and integration checks |

---

## **Folder Structure**

```text
internal-document-rag/
├── app/
│   ├── ingestion/          # PDF & TXT extraction, validation, chunking, and multimodal ingestion
│   │   ├── upload_pipeline.py
│   │   ├── pdf_loader.py
│   │   ├── text_loader.py
│   │   ├── chunker.py
│   │   ├── image_extractor.py
│   │   ├── image_ingestion.py
│   │   ├── table_extractor.py
│   │   ├── multimodal_pipeline.py
│   │   └── exceptions.py
│   ├── vision/             # Vision captioning connectors & SHA-256 caption cache
│   │   ├── vision_engine.py
│   │   └── caption_cache.py
│   ├── ocr/                # Scanned page OCR recognition engine
│   │   ├── ocr_engine.py
│   │   ├── ocr_cache.py
│   │   └── ocr_preprocessor.py
│   ├── embeddings/         # Embedding vector transformations
│   │   ├── embedding_engine.py
│   │   └── embedding_pipeline.py
│   ├── vectorstore/        # Vector index storage (ChromaDB)
│   │   └── chroma_manager.py
│   ├── retrieval/          # Hybrid search and query processing
│   │   ├── retrieval_engine.py
│   │   ├── retriever.py
│   │   ├── bm25_index_manager.py
│   │   └── query_preprocessor.py
│   ├── audio/              # Audio extraction, Whisper ASR, and timestamp alignment
│   │   ├── asr_engine.py
│   │   ├── audio_extractor.py
│   │   └── alignment.py
│   ├── video/              # Video ingestion and validation
│   │   ├── video_loader.py
│   │   └── exceptions.py
│   ├── services/           # Application orchestration services
│   │   ├── query_service.py
│   │   ├── upload_service.py
│   │   ├── workspace_service.py
│   │   ├── chat_history_service.py
│   │   └── index_maintenance_service.py
│   ├── llm/                # LLM connectors (Gemini, Groq, Ollama)
│   │   ├── base_provider.py
│   │   ├── gemini_provider.py
│   │   ├── groq_provider.py
│   │   ├── ollama_provider.py
│   │   ├── context_builder.py
│   │   ├── prompt_builder.py
│   │   └── exceptions.py
│   ├── ui/                 # Streamlit front-end layers
│   │   └── streamlit_ui.py
│   ├── models/             # Pydantic and dataclass state schemas
│   │   ├── schemas.py
│   │   └── workspace_state.py
│   ├── utils/              # Authentication, language detection, sample doc generator
│   │   ├── auth.py
│   │   ├── language_detector.py
│   │   └── sample_doc_generator.py
│   └── config.py           # Application configurations
├── data/
│   ├── uploads/            # Raw uploaded PDF and TXT files (partitioned per user)
│   ├── chats/              # Persistent JSON chat history files (partitioned per user)
│   └── chroma_db/          # Persistent Chroma DB indices
├── docs/                   # Full project documentation & slides
│   ├── project_documentation.md
│   └── user_manual.md
├── tests/                  # Pytest verification suites
├── requirements.txt        # Python package dependencies
└── main.py                 # Core application entrypoint
```

---

## **Local Setup & Installation**

### **Prerequisites**
* **Python Runtime**: Python 3.10+ is required.
* **Recommended Runtime**: Python 3.10 to 3.13 is recommended. Python 3.14 currently exposes third-party compatibility issues in `scikit-learn` / `transformers` stacks used by sentence-transformers.

1. **Clone & Initialize Virtual Environment**:
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

2. **Install Dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**:
   Create a `.env` file in the project root:
   ```text
   # Gemini & Vision Setup (Primary Cloud Vision)
   LLM_PROVIDER=gemini
   GOOGLE_API_KEY=your_actual_google_api_key_here
   GEMINI_MODEL_NAME=gemini-2.5-flash

   # Alternative Groq Setup
   # LLM_PROVIDER=groq
   # GROQ_API_KEY=your_actual_groq_api_key_here
   # GROQ_MODEL_NAME=llama-3.3-70b-versatile

   # Local Ollama Vision Setup (Secondary Vision Fallback)
   OLLAMA_URL=http://localhost:11434
   OLLAMA_VISION_MODEL=llava:latest
   OLLAMA_TIMEOUT=60.0

   # Multilingual Embeddings & Offline Mode
   EMBEDDING_MODEL_NAME=BAAI/bge-m3
   EMBEDDING_DIMENSION=1024
   EMBEDDING_OFFLINE_MODE=True
   HF_HUB_OFFLINE=0
   HF_HUB_DOWNLOAD_TIMEOUT=15.0

   # User Authentication Credentials
   USER_CREDENTIALS=admin:admin123,user:user123
   ```

> [!WARNING]
> **Vision Provider Requirement for Diagram Q&A**: To ask questions about embedded images, figures, or architecture diagrams, you **MUST** have either a valid `GOOGLE_API_KEY` configured or an active local Ollama server with the vision model pulled (`ollama pull llava`). Without one of these configured, image captioning degrades to local generic text-label fallbacks, causing diagram queries to return *"The uploaded documents do not contain sufficient information to answer this question."*

4. **Launch the Dashboard**:
   ```powershell
   streamlit run app/ui/streamlit_ui.py
   ```

   > [!NOTE]
   > The repository includes `.streamlit/config.toml` with `fileWatcherType = "none"` to avoid Streamlit hot-reload crashes triggered by `transformers` module inspection on some Windows/Python environments.

5. **Default Login Credentials**:
   Log in using the default credentials configured in your `.env` settings:
   * **Username**: `admin` | **Password**: `admin123`

   > [!NOTE]
   > The default login credentials are intended for local development only.

---

## **Testing & Verification**

Automated verification tests are run using `pytest`:

```powershell
pytest
```

### **Test Suite Metrics**
* **Total Tests Executed**: 306
* **Tests Passed**: 305
* **Tests Skipped**: 1 (a network-dependent integration test skipped under local environment checks)
* **Library Warnings**: Third-party library warnings (e.g., deprecation notices in `pydantic` or `chromadb` dependencies) originate from external packages and do not affect application stability.

---

## **Known Limitations**

* **Fallback Vision Limitations**: When both Google Gemini Vision and Ollama Vision are unconfigured or offline, image captioning silently falls back to local visual OCR label extraction. While this preserves extracted layout text labels, fallback captions are generic and are **not** a substitute for a true multimodal vision model.
* **Live Gemini API Test Requirement**: The multimodal test suite includes live Gemini Vision integration checks (such as `test_image_ingestion_service_process_image`) which require an active `GOOGLE_API_KEY` configured in the test environment to execute end-to-end vision model calls.
* **Local Vector Storage**: ChromaDB runs as a local database on the host filesystem.
* **Scanned Page Requirements**: Scanned PDF pages with sparse native text (< 300 characters) are automatically routed to OCR processing (`pytesseract` / `easyocr`). Extremely degraded physical scans may suffer lower OCR recognition accuracy.
* **Embedding Migration**: Documents indexed with older embedding models should be re-uploaded or re-indexed into the current multilingual collection.
* **Internet Dependency**: Cloud-based LLM providers (Gemini / Groq) require an active internet connection and valid API credentials.

---

## **Troubleshooting & Diagnostics**

### **1. Gemini Vision Key Errors (`VisionModelError`)**
* **Symptom**: Logs show `Google Gemini API key is not configured` or `VisionModelError`.
* **Fix**: Ensure `GOOGLE_API_KEY` in `.env` is set to a valid key from [Google AI Studio](https://aistudio.google.com/app/apikey) (not the placeholder string).

### **2. Ollama Vision 404 (`Ollama Vision response status 404`)**
* **Symptom**: Terminal logs show `Ollama Vision request failed: Ollama Vision response status 404`.
* **Fix**: The requested vision model (`OLLAMA_VISION_MODEL`, e.g. `llava:latest`) is not pulled on your Ollama server. Run:
  ```bash
  ollama pull llava
  ```
  Verify model readiness via: `curl http://localhost:11434/api/tags`.

### **3. Verifying Successful Image Captioning**
Inspect the application terminal logs during document upload. You should see log proof confirming active vision model generation:
```text
INFO - Successfully generated Gemini Vision caption for page_3_img_1_d53fd7b6.png: "Figure 1 shows a high-level system architecture..."
```
If you see `Running fallback visual OCR label analysis...`, it means both Gemini and Ollama Vision providers were unreachable and the pipeline used local fallback mode.

### **4. Embedding Generation Appears Stuck / No Log Output**
* **Symptom**: Process hangs after `Loading weights: 100%` with no further log output for minutes; terminal log ends with an `unauthenticated requests to the HF Hub` warning just before the hang.
* **Cause**: Unauthenticated Hugging Face Hub metadata network check hanging on a slow, proxied, or partially blocked network connection, even though model weights are already cached locally.
* **Fix**: Set `HF_HUB_OFFLINE=1` (or `EMBEDDING_OFFLINE_MODE=True`) in `.env` to skip Hugging Face Hub network checks entirely once model weights are cached locally. Alternatively, set `HF_TOKEN` in `.env` to avoid rate limits, set `HF_HUB_DOWNLOAD_TIMEOUT=15.0` to fail fast, or verify outbound network access to `huggingface.co`.

---

## **License**

This project was developed as part of an internship/academic software engineering project.

## **Author**

Varshini M

Internal Document RAG Chatbot
Python • Streamlit • LangChain • ChromaDB • Gemini API
