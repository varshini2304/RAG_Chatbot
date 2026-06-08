# Internal Document RAG Chatbot

An internal document question-answering chatbot built with Python, Streamlit,
LangChain, PyMuPDF, ChromaDB, Gemini, and Sentence Transformers.

This repository is currently at **Step 2 - Environment Setup & Project
Initialization**. The codebase contains only the production-style project
structure, configuration loading, Streamlit application shell, and connectivity
test scaffolding. Document ingestion, chunking, embeddings, retrieval, vector
storage, prompt engineering, and chatbot logic are intentionally not implemented
yet.

## Architecture Summary

The project is organized around clean, replaceable application layers:

- `app/ingestion`: future document loading and text extraction components.
- `app/embeddings`: future embedding model integration.
- `app/vectorstore`: future ChromaDB persistence and collection management.
- `app/retrieval`: future retrieval orchestration.
- `app/llm`: future Gemini service and prompt construction components.
- `app/ui`: future Streamlit UI composition.
- `app/models`: future shared schemas and typed data contracts.
- `app/config.py`: centralized environment and path configuration.
- `data/uploads`: local document upload storage.
- `data/chroma_db`: local ChromaDB persistence directory.
- `tests`: project tests and external service connectivity checks.

## Technology Stack

- Python
- Streamlit
- LangChain
- PyMuPDF
- ChromaDB
- Gemini API
- Sentence Transformers using `multi-qa-MiniLM-L6-cos-v1`
- python-dotenv
- pytest

## Setup Instructions

1. Create and activate a virtual environment:

   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

2. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

3. Create a local environment file:

   ```powershell
   Copy-Item .env.example .env
   ```

4. Add your Gemini API key to `.env`:

   ```text
   GOOGLE_API_KEY=your_google_api_key_here
   GEMINI_MODEL_NAME=gemini-2.5-flash
   ```

## Run Instructions

Start the Streamlit application from the project root:

```powershell
streamlit run main.py
```

Run the Gemini connectivity test after configuring `GOOGLE_API_KEY`:

```powershell
pytest tests/test_gemini.py -s
```
