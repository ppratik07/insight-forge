# ChartAI

**ChartAI** is a web-based application that transforms raw data into stunning, AI-generated visualizations. Users can input data via text, CSV/TXT files, or PDF documents, and the AI automatically generates optimized charts or answers questions about the data using Retrieval-Augmented Generation (RAG). The application supports single or multiple chart generation, various chart types (bar, pie, line, etc.), and PDF data extraction with persistent session storage to avoid reprocessing.

## Features

- **Text Input**: Describe data in plain text (e.g., "Sales 2023: Q1 $2M, Q2 $3M...") to generate visualizations.
- **File Upload**: Upload CSV/TXT files for automatic data parsing and chart creation.
- **PDF Processing**: Upload PDFs to extract text, tables, and charts, with support for Q&A and visualization using RAG.
- **Chart Customization**: Choose specific chart types (bar, pie, line, doughnut, area) or let AI auto-select the best type.
- **Multi-Chart Support**: Extract multiple datasets from complex inputs for separate visualizations.
- **Session Persistence**: Save processed PDF data to disk to avoid reprocessing (stored as pickle files).
- **Responsive Frontend**: Built with HTML, CSS, and JavaScript, using Chart.js for visualizations and Lucide for icons.
- **Backend API**: FastAPI-based backend with endpoints for data analysis, CSV parsing, PDF upload, and querying.

## Architecture

ChartAI follows a client-server architecture with a frontend for user interaction and a backend for data processing and AI tasks. The backend uses FastAPI for APIs, LangChain for RAG, and OpenAI for embeddings and LLMs. Session data is persisted to disk for efficiency.

### Architecture Diagram
```
+-------------------+
|    Web Browser    |
| (HTML, CSS, JS)   |
|   Chart.js, Lucide|
+-------------------+
           |
           | HTTP (GET/POST)
           |
+-------------------+
|   FastAPI Server  |
| (Python, Uvicorn) |
|  /api endpoints   |
+-------------------+
           |
           | Internal Calls
           |
+-------------------+          +-------------------+
|  Data Processing  |<-------->|    RAG Pipeline   |
| (CSV, Text, JSON) |          | (LangChain, FAISS)|
|   OpenAI LLM      |          |  PyMuPDF, OpenAI  |
+-------------------+          +-------------------+
           |                           |
           |                           | File Storage
           |                           |
+-------------------+          +-------------------+
|    Session Data   |          |   PDF Embeddings  |
| (Pickle Files)    |          |  (FAISS Vectors)  |
+-------------------+          +-------------------+
```

### Components
- **Frontend**: Single-page app (`index.html`, `main.js`, `main.css`) with panels for text input, file upload, PDF upload, and chart display. Uses Chart.js for rendering charts and Lucide for icons.
- **Backend**: FastAPI server (`main.py`, `routes.py`) with endpoints:
  - `/api/analyze-data`: Processes text input for single chart generation.
  - `/api/analyze-data-multi`: Extracts multiple datasets for multiple charts.
  - `/api/parse-csv`: Parses CSV/TXT files for chart generation.
  - `/api/upload-pdf`: Extracts text and charts from PDFs, stores embeddings.
  - `/api/query`: Answers questions or generates charts from PDF data using RAG.
  - `/api/health`: Checks server status.
- **RAG Pipeline**: Uses LangChain (`UnstructuredPDFLoader`, `FAISS`, `OpenAIEmbeddings`, `ChatOpenAI`) and PyMuPDF for PDF processing, text splitting, and chart extraction. Stores sessions in memory and on disk (`sessions/` directory).
- **Session Persistence**: Saves FAISS vector stores and extracted images as pickle files to avoid reprocessing PDFs.

## Prerequisites

- **Python 3.11+**: For backend execution.
- **Node.js**: Optional, for local frontend development (not required for production).
- **System Dependencies** (macOS/Linux):
  - `tesseract`: For OCR in PDF processing.
  - `poppler`: For PDF rendering.
- **OpenAI API Key**: Required for AI-driven data analysis and RAG.

## Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/your-repo/chartai.git
   cd chartai
   ```

2. **Set Up Backend**:
   ```bash
   cd python_backend
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install --upgrade pip setuptools wheel
   pip install -r requirements.txt
   ```

3. **Install System Dependencies** (macOS):
   ```bash
   brew install tesseract poppler
   ```

4. **Configure Environment**:
   Create a `.env` file in `python_backend/`:
   ```plaintext
   OPENAI_API_KEY=your-openai-api-key
   PORT=5000
   ```

5. **Run the Server**:
   ```bash
   cd python_backend
   uvicorn main:app --reload --port 5000    or
   python main.py 
   ```
   The server runs on `http://localhost:5000`.

6. **Access the Frontend**:
   Open `http://localhost:5000` in a browser. The FastAPI server serves static files from the `client/` directory.

## Usage

1. **Text Input**:
   - Enter data (e.g., "Revenue 2023: Q1 $2M, Q2 $3M, Q3 $4M, Q4 $5M") in the text panel.
   - Select a chart type (or "AI Auto-Select") and mode (single or multi-chart).
   - Click "Generate Chart" to view results.

2. **File Upload**:
   - Upload a CSV/TXT file with structured data.
   - Select chart type/mode and click "Generate Chart".

3. **PDF Processing**:
   - Upload a PDF file to extract text and charts.
   - View extracted charts (as images) in the results page.
   - Ask questions (e.g., "What is the sales trend?") in the query section to get answers or generate new charts.
   - Session data is saved in `python_backend/app/ai/sessions/` as pickle files, reusable with the returned `session_id`.

4. **Chart Interaction**:
   - View generated charts in the results page.
   - Download charts as images or copy to clipboard (future feature).

## Development

- **Frontend**: Edit `client/index.html`, `client/src/scripts/main.js`, and `client/src/styles/main.css`. Uses Chart.js for charts and Lucide for icons.
- **Backend**: Modify `python_backend/app/` for API logic, AI processing (`analyzer.py`, `csv_parser.py`, `rag_pipeline.py`), or routes (`routes.py`).
- **Testing**:
  - Test APIs with `curl` or Postman (e.g., `curl -X POST -F "file=@sample.pdf" http://localhost:5000/api/upload-pdf`).
  - Use browser DevTools to debug frontend issues.

## Known Issues

- **PDF Processing Time**: Large PDFs (e.g., 32 pages) may take significant time (~468 seconds) due to text extraction and chart analysis. Optimize by reducing `chunk_size` in `rag_pipeline.py`.
- **Session Persistence**: Session files are not automatically cleaned. Implement a cleanup endpoint (`/clear-session`) for production.
- **PDF Parsing Warnings**: Harmless warnings like `Cannot set gray non-stroke color` may appear from `unstructured`/`pymupdf` when parsing complex PDFs.

## Future Improvements

- Add video export for animated charts.
- Implement session cleanup endpoint to manage disk usage.
- Optimize PDF processing with smaller chunk sizes or cloud-based processing.
- Add authentication for API access.
- Support more chart types and interactive features.

## License

MIT License. See [LICENSE](LICENSE) for details.