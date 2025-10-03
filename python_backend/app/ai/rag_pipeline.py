# python_backend/app/ai/rag_pipeline.py
import uuid
import tempfile
import os
import base64
import json
import hashlib
from typing import Dict, List, Any, Optional
from langchain_community.document_loaders import UnstructuredPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.documents import Document
import fitz  # PyMuPDF
from pymongo import MongoClient
# from pymongo.errors import ConnectionError
import faiss  # Import faiss to set thread limit

# Limit FAISS to single-threaded execution to avoid OpenMP conflicts
faiss.omp_set_num_threads(1)

# Directories for FAISS indexes and JSON metadata (fallback)
INDEX_DIR = os.path.join(os.path.dirname(__file__), "indexes")
METADATA_DIR = os.path.join(os.path.dirname(__file__), "metadata")

# MongoDB Atlas connection
MONGO_URI = os.getenv("MONGO_URI")
mongo_client = None
mongo_collection = None

if MONGO_URI:
    try:
        mongo_client = MongoClient(
            MONGO_URI,
            serverSelectionTimeoutMS=5000,
            tls=True,
            tlsAllowInvalidCertificates=False,
        )
        mongo_client.admin.command('ping')
        mongo_db = mongo_client["chartai"]
        mongo_collection = mongo_db["sessions"]
        print("Connected to MongoDB Atlas")
    except Exception as e:
        print(f"MongoDB Atlas connection failed: {str(e)}")
        mongo_collection = None
else:
    print("MONGO_URI not set – falling back to JSON storage")
    mongo_collection = None

_sessions: Dict[str, Dict[str, Any]] = {}

class RAGPipeline:
    def __init__(self, openai_api_key: str):
        print(f"Starting RAGPipeline initialization with API key: {openai_api_key[:4]}...{openai_api_key[-4:]}")
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY is missing")
        try:
            print("Initializing OpenAI embeddings...")
            self.embeddings = OpenAIEmbeddings(api_key=openai_api_key)
            print("Initializing ChatOpenAI for text...")
            self.llm = ChatOpenAI(model="gpt-4-turbo", api_key=openai_api_key)
            print("Initializing ChatOpenAI for vision...")
            self.vision_llm = ChatOpenAI(model="gpt-4o", api_key=openai_api_key)
            print("Initializing text splitter...")
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000, chunk_overlap=200, separators=["\n\n", "\n", ".", "!"]
            )
            print("Setting up prompts...")
            self.viz_prompt = ChatPromptTemplate.from_template(
                """Analyze if this query requires data visualization: {query}
                If yes, classify as 'viz' and extract key data points as JSON: {{"data_points": [{{"label": "str", "value": float}}], "chart_type": "str"}}
                Else, 'qna'. Respond as JSON: {{"intent": "viz|qna", "extracted_data": {{...}}}}"""
            )
            self.image_desc_prompt = ChatPromptTemplate.from_messages([
                ("system", "Describe if this image is a chart/graph. If yes, extract data points as JSON: {{\"is_chart\": true, \"type\": \"bar/pie/etc\", \"title\": \"str\", \"data_points\": [{{\"label\": \"str\", \"value\": float}}], \"description\": \"str\"}}. Else: {{\"is_chart\": false, \"description\": \"str\"}}"),
                ("user", [{"type": "image_url", "image_url": {"url": "data:image/png;base64,{base64_image}"}}])
            ])
            print("RAGPipeline initialized")
        except Exception as e:
            print(f"RAGPipeline initialization failed: {str(e)}")
            raise ValueError(f"Failed to initialize RAGPipeline: {str(e)}")

    def get_file_hash(self, file_path: str) -> str:
        """Compute SHA-256 hash of a file."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def save_session_metadata(self, session_id: str, metadata: Dict[str, Any], file_hash: str):
        """Persist session metadata (images, file_hash, etc.)."""
        metadata["session_id"] = session_id
        metadata["file_hash"] = file_hash
        print(f"Saving metadata for session {session_id} with file hash {file_hash}")
        if mongo_collection is not None:
            try:
                mongo_collection.replace_one(
                    {"session_id": session_id},
                    metadata,
                    upsert=True
                )
                print(f"Saved session metadata {session_id} to MongoDB Atlas")
            except Exception as e:
                print(f"MongoDB save error: {str(e)}")
                raise ValueError(f"Failed to save metadata to MongoDB: {str(e)}")
        else:
            print("Falling back to JSON storage")
            try:
                os.makedirs(METADATA_DIR, exist_ok=True)
                meta_path = os.path.join(METADATA_DIR, f"{session_id}.json")
                with open(meta_path, "w") as f:
                    json.dump(metadata, f)
                print(f"Saved session metadata {session_id} to {meta_path}")
            except Exception as e:
                print(f"JSON save error: {str(e)}")
                raise ValueError(f"Failed to save metadata to JSON: {str(e)}")

    def load_session_metadata(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load metadata for a given session_id."""
        print(f"Loading metadata for session {session_id}")
        if mongo_collection is not None:
            try:
                doc = mongo_collection.find_one({"session_id": session_id})
                if doc:
                    print(f"Loaded metadata {session_id} from MongoDB Atlas")
                    return doc
                else:
                    print(f"No metadata found for session {session_id} in MongoDB")
                    return None
            except Exception as e:
                print(f"MongoDB load error: {str(e)}")
                return None
        print("Checking JSON storage for metadata")
        meta_path = os.path.join(METADATA_DIR, f"{session_id}.json")
        if os.path.exists(meta_path):
            try:
                with open(meta_path, "r") as f:
                    data = json.load(f)
                print(f"Loaded metadata {session_id} from {meta_path}")
                return data
            except Exception as e:
                print(f"JSON load error: {str(e)}")
                return None
        print(f"No metadata found for session {session_id} in JSON")
        return None

    def load_session_by_hash(self, file_hash: str) -> Optional[Dict[str, Any]]:
        """Find an existing session by file hash."""
        print(f"Looking up session by file hash {file_hash}")
        if mongo_collection is not None:
            try:
                doc = mongo_collection.find_one({"file_hash": file_hash})
                if doc:
                    print(f"Found existing session for hash {file_hash} in MongoDB")
                    return doc
                else:
                    print(f"No session found for hash {file_hash} in MongoDB")
            except Exception as e:
                print(f"MongoDB hash lookup error: {str(e)}")
        print("Checking JSON storage for hash")
        if os.path.exists(METADATA_DIR):
            for fn in os.listdir(METADATA_DIR):
                if fn.endswith(".json"):
                    try:
                        with open(os.path.join(METADATA_DIR, fn), "r") as f:
                            data = json.load(f)
                        if data.get("file_hash") == file_hash:
                            print(f"Found existing session for hash {file_hash} in {fn}")
                            return data
                    except Exception:
                        continue
        else:
            print(f"Metadata directory {METADATA_DIR} does not exist")
        print(f"No session found for hash {file_hash} in JSON")
        return None

    async def upload_and_index_pdf(self, file_path: str) -> Dict[str, Any]:
        # Check for duplicate PDF via hash
        file_hash = self.get_file_hash(file_path)
        existing = self.load_session_by_hash(file_hash)
        if existing:
            session_id = existing["session_id"]
            index_path = os.path.join(INDEX_DIR, session_id)
            if os.path.isdir(index_path):
                try:
                    vector_store = FAISS.load_local(
                        index_path, self.embeddings, allow_dangerous_deserialization=True
                    )
                    _sessions[session_id] = {
                        "vector_store": vector_store,
                        "images": existing.get("images", [])
                    }
                    print(f"Re-used existing session {session_id} for hash {file_hash}")
                    return {
                        "session_id": session_id,
                        "extracted_charts": [
                            img for img in existing.get("images", []) if img.get("is_chart")
                        ]
                    }
                except Exception as e:
                    print(f"Failed to load existing FAISS index: {str(e)}")

        # New processing
        session_id = str(uuid.uuid4())
        try:
            print(f"Loading PDF {file_path}")
            loader = UnstructuredPDFLoader(file_path, mode="elements")
            docs: List[Document] = loader.load()
            print(f"Extracted {len(docs)} raw elements")

            extracted_images: List[Dict[str, Any]] = []
            pdf_doc = fitz.open(file_path)
            for page_num in range(len(pdf_doc)):
                page = pdf_doc[page_num]
                img_list = page.get_images(full=True)
                for img_idx, img in enumerate(img_list):
                    xref = img[0]
                    base_img = pdf_doc.extract_image(xref)
                    img_bytes = base_img["image"]
                    img_ext = base_img["ext"]
                    if img_ext not in ("png", "jpeg"):
                        continue
                    base64_str = base64.b64encode(img_bytes).decode()
                    w, h = base_img["width"], base_img["height"]
                    if w <= 100 or h <= 100:
                        continue
                    print(f"Analyzing image on page {page_num + 1}, index {img_idx}")
                    desc_chain = self.image_desc_prompt | self.vision_llm | JsonOutputParser()
                    desc_res = await desc_chain.ainvoke({"base64_image": base64_str})
                    if desc_res.get("is_chart"):
                        chart_doc = Document(
                            page_content=(
                                desc_res["description"] +
                                "\nData: " + json.dumps(desc_res.get("data_points", []))
                            ),
                            metadata={"source": f"chart_p{page_num}_i{img_idx}", "type": "chart"}
                        )
                        docs.append(chart_doc)
                    extracted_images.append({
                        "base64": f"data:image/{img_ext};base64,{base64_str}",
                        "page": page_num + 1,
                        "description": desc_res.get("description", ""),
                        "is_chart": desc_res.get("is_chart", False)
                    })
            pdf_doc.close()

            print(f"Extracted {len(extracted_images)} images, {sum(i['is_chart'] for i in extracted_images)} charts")
            splits = self.text_splitter.split_documents(docs)
            print(f"Split into {len(splits)} chunks")

            vector_store = FAISS.from_documents(splits, self.embeddings)
            os.makedirs(INDEX_DIR, exist_ok=True)
            index_path = os.path.join(INDEX_DIR, session_id)
            vector_store.save_local(index_path)
            print(f"Saved FAISS index to {index_path}")

            _sessions[session_id] = {"vector_store": vector_store, "images": extracted_images}
            self.save_session_metadata(
                session_id,
                {"images": extracted_images},
                file_hash
            )

            if os.path.exists(file_path):
                os.unlink(file_path)

            return {
                "session_id": session_id,
                "extracted_charts": [img for img in extracted_images if img["is_chart"]]
            }
        except Exception as e:
            if os.path.exists(file_path):
                os.unlink(file_path)
            print(f"PDF processing error: {str(e)}")
            raise ValueError(f"Failed to process PDF: {str(e)}")

    async def query(self, query: str, session_id: str) -> Dict[str, Any]:
        print(f"Querying session {session_id}: {query}")
        if session_id not in _sessions:
            meta = self.load_session_metadata(session_id)
            if not meta:
                raise ValueError("Invalid session_id – no metadata found")
            index_path = os.path.join(INDEX_DIR, session_id)
            if not os.path.isdir(index_path):
                raise ValueError("FAISS index missing for this session")
            try:
                vector_store = FAISS.load_local(
                    index_path, self.embeddings, allow_dangerous_deserialization=True
                )
                _sessions[session_id] = {
                    "vector_store": vector_store,
                    "images": meta.get("images", [])
                }
                print(f"Loaded session {session_id} from disk")
            except Exception as e:
                raise ValueError(f"Failed to load FAISS index: {str(e)}")
        sess = _sessions[session_id]
        try:
            retriever = sess["vector_store"].as_retriever(search_kwargs={"k": 4})
            docs = retriever.invoke(query)
            context = "\n\n".join([d.page_content for d in docs])
        except Exception as e:
            print(f"FAISS retrieval error: {str(e)}")
            raise ValueError(f"Failed to retrieve documents: {str(e)}")
        viz_chain = self.viz_prompt | self.llm | JsonOutputParser()
        intent = await viz_chain.ainvoke({"query": query})
        if intent["intent"] == "viz":
            extracted = intent.get("extracted_data", {})
            data_json = json.dumps(extracted.get("data_points", []))
            from .analyzer import analyze_text_data, convert_to_chart_data
            analyzed = await analyze_text_data(data_json)
            chart_cfg = convert_to_chart_data(analyzed)
            answer_prompt = ChatPromptTemplate.from_template(
                "Based on context: {context}\nAnswer the query: {query}\nIf a chart is generated, mention it."
            )
            answer_chain = answer_prompt | self.llm
            answer = await answer_chain.ainvoke({"context": context, "query": query})
            result = {
                "answer": answer.content,
                "intent": "viz",
                "chart_config": chart_cfg,
                "confidence": analyzed.confidence
            }
        else:
            qa_prompt = ChatPromptTemplate.from_template(
                "Context: {context}\nQuestion: {query}\nAnswer concisely."
            )
            qa_chain = qa_prompt | self.llm
            answer = await qa_chain.ainvoke({"context": context, "query": query})
            result = {
                "answer": answer.content,
                "intent": "qna",
                "sources": [d.metadata for d in docs]
            }
        if "chart" in query.lower() or "graph" in query.lower():
            result["existing_charts"] = sess["images"]
        return result

def init_rag_pipeline(api_key: str):
    global rag_pipeline
    try:
        print(f"Initializing RAG pipeline with key {api_key[:4]}...{api_key[-4:]}")
        rag_pipeline = RAGPipeline(api_key)
        print("RAG pipeline ready")
    except Exception as e:
        print(f"RAG init failed: {str(e)}")
        rag_pipeline = None
        raise

rag_pipeline = None