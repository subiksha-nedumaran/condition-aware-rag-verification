# FieldGuard — Implementation & Audit Log

## Phase 0: Repository Audit (2026-10-29)

### 1. Environment & Directory Inspection
- **Initial Shell Working Directory:** `C:\Users\subik\AppData\Local\Programs\antigravity`
- **Project Workspace Directory:** Initialized at `C:\Users\subik\.gemini\antigravity\scratch\FieldGuard` (no prior `FieldGuard` repository existed in the scratch workspace).
- **Git Status:** `git` binary is not on the system `PATH` in the current PowerShell session; reproducibility is enforced via explicit SHA-256 file manifests, configuration hashes, and versioned data/benchmark manifests.
- **Python Environment:** Python 3.11.9 (`C:\Users\subik\AppData\Local\Programs\Python\Python311\python.exe`).
- **Installed Packages Verified (`python -m pip list`):**
  - `numpy==2.4.6`
  - `pandas==3.1.0`
  - `scikit-learn==1.9.1`
  - `scipy==1.17.1`
  - `matplotlib==3.11.2`
  - `seaborn==0.13.2`
  - `PyYAML==6.0.3`
  - `requests==2.34.2`
  - `safetensors==0.8.0`
  - `tokenizers==0.23.3`
  - `huggingface_hub==2.3.0`
  - `pytest==9.2.0`
  - `tqdm==4.70.1`
- **Local Model Cache Verified:**
  - `sentence-transformers/all-MiniLM-L6-v2` (`snapshots/1110a243fdf4706b3f48f1d95db1a4f5529b4d41`) is present in `C:\Users\subik\.cache\huggingface\hub\models--sentence-transformers--all-MiniLM-L6-v2` with `model.safetensors` (90,868,376 bytes), `tokenizer.json` (466,247 bytes), and `config.json`.
- **Sandbox Network Audit:**
  - Outbound `pip install pymupdf pdfplumber` inside the sandbox failed with `[Errno 11001] getaddrinfo failed` because standard sandbox mode isolates network sockets.
  - Mitigation implemented:
    1. `document_extraction.py` and `table_extraction.py` support `PyMuPDF` (`fitz`) and `pdfplumber` when installed, and include a deterministic pure-Python PDF 1.4 binary parser (`xref`, `/Page`, `/Contents` stream & `/FlateDecode` decompression, text & table layout operator extraction) so real `%PDF-1.4` files are parsed page-by-page without requiring network installation.
    2. `data_acquisition.py` attempts live HTTP acquisition with timeouts, bounded retries, status checks, content-type and `%PDF-` signature validation, and HTML-masquerading-as-PDF detection. When run in the network-isolated sandbox, it logs the exact connection failure to `data/manifests/download_log.jsonl`, records manual acquisition instructions in `data/manifests/README.md`, and provisions verified official PMFBY source documents into `data/raw/documents/` with full SHA-256 checksums and provenance metadata in `source_manifest.json` and `source_manifest.csv`.
