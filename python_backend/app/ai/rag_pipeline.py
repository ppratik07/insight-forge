# # # Modified rag_pipeline.py with image extraction for charts/graphs
# # # Added PyMuPDF (fitz) for image extraction; assume pip install pymupdf
# # # During upload: Extract images, filter potential charts (by size/type), describe with vision if chart-like, include descriptions in RAG docs
# # # Return base64 images in upload response for UI display
# # # In query: If intent involves existing charts, reference descriptions; still generate new charts if needed

# # import uuid
# # import tempfile
# # import os
# # import base64
# # from typing import Dict, List, Any, Optional
# # from langchain_community.document_loaders import UnstructuredPDFLoader
# # from langchain.text_splitter import RecursiveCharacterTextSplitter
# # from langchain_openai import OpenAIEmbeddings, ChatOpenAI
# # # from langchain.vectorstores import FAISS
# # from langchain_community.vectorstores import FAISS
# # from langchain_core.prompts import ChatPromptTemplate
# # from langchain_core.output_parsers import JsonOutputParser
# # from langchain_core.documents import Document
# # import json
# # import fitz  # PyMuPDF for image extraction

# # # In-memory store for sessions (vector stores and extracted images)
# # _sessions: Dict[str, Dict[str, Any]] = {}  # Now stores {'vector_store': FAISS, 'images': list of {'base64': str, 'description': str}}

# # class RAGPipeline:
# #     def __init__(self, openai_api_key: str):
# #         self.embeddings = OpenAIEmbeddings(api_key=openai_api_key)
# #         self.llm = ChatOpenAI(model="gpt-4-turbo", api_key=openai_api_key)
# #         self.vision_llm = ChatOpenAI(model="gpt-4o", api_key=openai_api_key)  # Use vision model for image description
# #         self.text_splitter = RecursiveCharacterTextSplitter(
# #             chunk_size=1000, chunk_overlap=200, separators=["\n\n", "\n", ".", "!"]
# #         )
# #         self.viz_prompt = ChatPromptTemplate.from_template(
# #             """Analyze if this query requires data visualization: {query}
# #             If yes, classify as 'viz' and extract key data points as JSON: {{"data_points": [{{"label": "str", "value": float}}], "chart_type": "str"}}
# #             Else, 'qna'. Respond as JSON: {{"intent": "viz|qna", "extracted_data": {{...}}}}"""
# #         )
# #         self.image_desc_prompt = ChatPromptTemplate.from_messages([
# #             ("system", "Describe if this image is a chart/graph. If yes, extract data points as JSON: {{\"is_chart\": true, \"type\": \"bar/pie/etc\", \"title\": \"str\", \"data_points\": [{{\"label\": \"str\", \"value\": float}}], \"description\": \"str\"}}. Else: {{\"is_chart\": false, \"description\": \"str\"}}"),
# #             ("user", [{"type": "image_url", "image_url": {"url": "data:image/png;base64,{base64_image}"}}])
# #         ])

# #     async def upload_and_index_pdf(self, file_path: str) -> Dict[str, Any]:
# #         """Load PDF, extract text/tables, images; describe charts; index all. Returns session_id and extracted charts."""
# #         session_id = str(uuid.uuid4())
        
# #         # 1. Extract text/tables with Unstructured
# #         loader = UnstructuredPDFLoader(file_path, mode="elements")
# #         docs: List[Document] = loader.load()
        
# #         # 2. Extract images with PyMuPDF and describe potential charts
# #         extracted_images = []
# #         pdf_doc = fitz.open(file_path)
# #         for page_num in range(len(pdf_doc)):
# #             page = pdf_doc[page_num]
# #             image_list = page.get_images(full=True)
# #             for img_index, img in enumerate(image_list):
# #                 xref = img[0]
# #                 base_image = pdf_doc.extract_image(xref)
# #                 image_bytes = base_image["image"]
# #                 image_ext = base_image["ext"]
# #                 if image_ext in ["png", "jpeg"]:  # Filter image types
# #                     base64_image = base64.b64encode(image_bytes).decode('utf-8')
                    
# #                     # Check size to filter small icons (e.g., >100x100)
# #                     width, height = base_image["width"], base_image["height"]
# #                     if width > 100 and height > 100:  # Likely chart/graph
# #                         # Describe with vision
# #                         desc_chain = self.image_desc_prompt | self.vision_llm | JsonOutputParser()
# #                         desc_result = await desc_chain.ainvoke({"base64_image": base64_image})
                        
# #                         # If it's a chart, add description to docs
# #                         if desc_result.get("is_chart", False):
# #                             chart_doc = Document(
# #                                 page_content=desc_result["description"] + "\nData: " + json.dumps(desc_result.get("data_points", [])),
# #                                 metadata={"source": f"chart_page_{page_num}_img_{img_index}", "type": "chart"}
# #                             )
# #                             docs.append(chart_doc)
                        
# #                         # Store for UI (all potential charts)
# #                         extracted_images.append({
# #                             "base64": f"data:image/{image_ext};base64,{base64_image}",
# #                             "page": page_num + 1,
# #                             "description": desc_result["description"],
# #                             "is_chart": desc_result.get("is_chart", False)
# #                         })
        
# #         pdf_doc.close()
        
# #         # Split text/docs (including chart descriptions)
# #         splits = self.text_splitter.split_documents(docs)
        
# #         # Embed and index
# #         vector_store = FAISS.from_documents(splits, self.embeddings)
        
# #         # Store in session
# #         _sessions[session_id] = {
# #             "vector_store": vector_store,
# #             "images": extracted_images  # For UI display
# #         }
        
# #         # Cleanup temp file
# #         os.unlink(file_path)
        
# #         return {
# #             "session_id": session_id,
# #             "extracted_charts": [img for img in extracted_images if img["is_chart"]]  # Only charts for UI
# #         }

# #     async def query(self, query: str, session_id: str) -> Dict[str, Any]:
# #         """Query RAG: Retrieve, classify intent, generate answer/chart. Existing charts via session."""
# #         if session_id not in _sessions:
# #             raise ValueError("Invalid session_id. Upload PDF first.")
        
# #         session_data = _sessions[session_id]
# #         vector_store = session_data["vector_store"]
# #         retriever = vector_store.as_retriever(search_kwargs={"k": 4})
# #         relevant_docs = retriever.invoke(query)
# #         context = "\n\n".join([doc.page_content for doc in relevant_docs])
        
# #         # Classify intent
# #         viz_chain = self.viz_prompt | self.llm | JsonOutputParser()
# #         intent_result = await viz_chain.ainvoke({"query": query})
        
# #         result = {}
        
# #         if intent_result["intent"] == "viz":
# #             # Extract data and generate new chart
# #             extracted_data = intent_result["extracted_data"]
# #             data_points_text = json.dumps(extracted_data["data_points"])
# #             from .analyzer import analyze_text_data
# #             analyzed = await analyze_text_data(data_points_text)
# #             from .analyzer import convert_to_chart_data
# #             chart_config = convert_to_chart_data(analyzed)
            
# #             # Generate answer
# #             answer_prompt = ChatPromptTemplate.from_template(
# #                 """Based on context: {context}
# #                 Answer: {query}
# #                 If viz, mention the generated chart."""
# #             )
# #             answer_chain = answer_prompt | self.llm
# #             answer = await answer_chain.ainvoke({"context": context, "query": query})
            
# #             result = {
# #                 "answer": answer.content,
# #                 "intent": "viz",
# #                 "chart_config": chart_config,
# #                 "confidence": analyzed.confidence
# #             }
# #         else:
# #             # Standard Q&A
# #             qa_prompt = ChatPromptTemplate.from_template(
# #                 """Context: {context}
# #                 Question: {query}
# #                 Answer concisely."""
# #             )
# #             qa_chain = qa_prompt | self.llm
# #             answer = await qa_chain.ainvoke({"context": context, "query": query})
            
# #             result = {
# #                 "answer": answer.content,
# #                 "intent": "qna",
# #                 "sources": [doc.metadata for doc in relevant_docs]
# #             }
        
# #         # Always include existing extracted charts if query mentions "charts" or "graphs"
# #         if "chart" in query.lower() or "graph" in query.lower():
# #             result["existing_charts"] = session_data["images"]
        
# #         return result

# # # Global instance
# # rag_pipeline = None

# # def init_rag_pipeline(api_key: str):
# #     global rag_pipeline
# #     rag_pipeline = RAGPipeline(api_key)

# # python_backend/app/ai/rag_pipeline.py
# import uuid
# import tempfile
# import os
# import base64
# from typing import Dict, List, Any, Optional
# from langchain_community.document_loaders import UnstructuredPDFLoader
# from langchain.text_splitter import RecursiveCharacterTextSplitter
# from langchain_openai import OpenAIEmbeddings, ChatOpenAI
# from langchain.vectorstores import FAISS
# from langchain_core.prompts import ChatPromptTemplate
# from langchain_core.output_parsers import JsonOutputParser
# from langchain_core.documents import Document
# import json
# import fitz  # PyMuPDF

# _sessions: Dict[str, Dict[str, Any]] = {}
# rag_pipeline = None  # Global variable declared at module level

# class RAGPipeline:
#     def __init__(self, openai_api_key: str):
#         print(f"Starting RAGPipeline initialization with API key: {openai_api_key[:4]}...{openai_api_key[-4:]}")
#         if not openai_api_key:
#             raise ValueError("OPENAI_API_KEY is not provided or empty")
#         try:
#             print("Initializing OpenAI embeddings...")
#             self.embeddings = OpenAIEmbeddings(api_key=openai_api_key)
#             print("Initializing ChatOpenAI for text...")
#             self.llm = ChatOpenAI(model="gpt-4-turbo", api_key=openai_api_key)
#             print("Initializing ChatOpenAI for vision...")
#             self.vision_llm = ChatOpenAI(model="gpt-4o", api_key=openai_api_key)
#             print("Initializing text splitter...")
#             self.text_splitter = RecursiveCharacterTextSplitter(
#                 chunk_size=1000, chunk_overlap=200, separators=["\n\n", "\n", ".", "!"]
#             )
#             print("Setting up prompts...")
#             self.viz_prompt = ChatPromptTemplate.from_template(
#                 """Analyze if this query requires data visualization: {query}
#                 If yes, classify as 'viz' and extract key data points as JSON: {{"data_points": [{{"label": "str", "value": float}}], "chart_type": "str"}}
#                 Else, 'qna'. Respond as JSON: {{"intent": "viz|qna", "extracted_data": {{...}}}}"""
#             )
#             self.image_desc_prompt = ChatPromptTemplate.from_messages([
#                 ("system", "Describe if this image is a chart/graph. If yes, extract data points as JSON: {{\"is_chart\": true, \"type\": \"bar/pie/etc\", \"title\": \"str\", \"data_points\": [{{\"label\": \"str\", \"value\": float}}], \"description\": \"str\"}}. Else: {{\"is_chart\": false, \"description\": \"str\"}}"),
#                 ("user", [{"type": "image_url", "image_url": {"url": "data:image/png;base64,{base64_image}"}}])
#             ])
#             print("RAGPipeline initialized successfully")
#         except Exception as e:
#             print(f"RAGPipeline initialization failed: {str(e)}")
#             raise ValueError(f"Failed to initialize RAGPipeline: {str(e)}")

#     async def upload_and_index_pdf(self, file_path: str) -> Dict[str, Any]:
#         session_id = str(uuid.uuid4())
#         try:
#             print(f"Loading PDF: {file_path}")
#             loader = UnstructuredPDFLoader(file_path, mode="elements")
#             docs: List[Document] = loader.load()
#             print(f"Extracted {len(docs)} documents from PDF")
#             extracted_images = []
#             pdf_doc = fitz.open(file_path)
#             for page_num in range(len(pdf_doc)):
#                 page = pdf_doc[page_num]
#                 image_list = page.get_images(full=True)
#                 for img_index, img in enumerate(image_list):
#                     xref = img[0]
#                     base_image = pdf_doc.extract_image(xref)
#                     image_bytes = base_image["image"]
#                     image_ext = base_image["ext"]
#                     if image_ext in ["png", "jpeg"]:
#                         base64_image = base64.b64encode(image_bytes).decode('utf-8')
#                         width, height = base_image["width"], base_image["height"]
#                         if width > 100 and height > 100:
#                             print(f"Analyzing image on page {page_num + 1}, index {img_index}")
#                             desc_chain = self.image_desc_prompt | self.vision_llm | JsonOutputParser()
#                             desc_result = await desc_chain.ainvoke({"base64_image": base64_image})
#                             if desc_result.get("is_chart", False):
#                                 chart_doc = Document(
#                                     page_content=desc_result["description"] + "\nData: " + json.dumps(desc_result.get("data_points", [])),
#                                     metadata={"source": f"chart_page_{page_num}_img_{img_index}", "type": "chart"}
#                                 )
#                                 docs.append(chart_doc)
#                             extracted_images.append({
#                                 "base64": f"data:image/{image_ext};base64,{base64_image}",
#                                 "page": page_num + 1,
#                                 "description": desc_result["description"],
#                                 "is_chart": desc_result.get("is_chart", False)
#                             })
#             pdf_doc.close()
#             print(f"Extracted {len(extracted_images)} images, {sum(1 for img in extracted_images if img['is_chart'])} charts")
#             splits = self.text_splitter.split_documents(docs)
#             print(f"Split into {len(splits)} chunks")
#             vector_store = FAISS.from_documents(splits, self.embeddings)
#             _sessions[session_id] = {
#                 "vector_store": vector_store,
#                 "images": extracted_images
#             }
#             os.unlink(file_path)
#             return {
#                 "session_id": session_id,
#                 "extracted_charts": [img for img in extracted_images if img["is_chart"]]
#             }
#         except Exception as e:
#             if os.path.exists(file_path):
#                 os.unlink(file_path)
#             print(f"PDF processing failed: {str(e)}")
#             raise ValueError(f"Failed to process PDF: {str(e)}")

#     async def query(self, query: str, session_id: str) -> Dict[str, Any]:
#         if session_id not in _sessions:
#             raise ValueError("Invalid session_id. Upload PDF first.")
#         session_data = _sessions[session_id]
#         vector_store = session_data["vector_store"]
#         retriever = vector_store.as_retriever(search_kwargs={"k": 4})
#         relevant_docs = retriever.invoke(query)
#         context = "\n\n".join([doc.page_content for doc in relevant_docs])
#         viz_chain = self.viz_prompt | self.llm | JsonOutputParser()
#         intent_result = await viz_chain.ainvoke({"query": query})
#         result = {}
#         if intent_result["intent"] == "viz":
#             extracted_data = intent_result["extracted_data"]
#             data_points_text = json.dumps(extracted_data["data_points"])
#             from .analyzer import analyze_text_data
#             analyzed = await analyze_text_data(data_points_text)
#             from .analyzer import convert_to_chart_data
#             chart_config = convert_to_chart_data(analyzed)
#             answer_prompt = ChatPromptTemplate.from_template(
#                 """Based on context: {context}
#                 Answer: {query}
#                 If viz, mention the generated chart."""
#             )
#             answer_chain = answer_prompt | self.llm
#             answer = await answer_chain.ainvoke({"context": context, "query": query})
#             result = {
#                 "answer": answer.content,
#                 "intent": "viz",
#                 "chart_config": chart_config,
#                 "confidence": analyzed.confidence
#             }
#         else:
#             qa_prompt = ChatPromptTemplate.from_template(
#                 """Context: {context}
#                 Question: {query}
#                 Answer concisely."""
#             )
#             qa_chain = qa_prompt | self.llm
#             answer = await qa_chain.ainvoke({"context": context, "query": query})
#             result = {
#                 "answer": answer.content,
#                 "intent": "qna",
#                 "sources": [doc.metadata for doc in relevant_docs]
#             }
#         if "chart" in query.lower() or "graph" in query.lower():
#             result["existing_charts"] = session_data["images"]
#         return result

# def init_rag_pipeline(api_key: str):
#     global rag_pipeline
#     try:
#         print(f"Initializing RAG pipeline with API key: {api_key[:4]}...{api_key[-4:]}")
#         rag_pipeline = RAGPipeline(api_key)
#         if rag_pipeline is None:
#             raise ValueError("RAGPipeline constructor returned None")
#         print("RAG pipeline initialized successfully")
#     except Exception as e:
#         print(f"Initialization failed: {str(e)}")
#         rag_pipeline = None
#         raise  # Re-raise to ensure error propagates



# python_backend/app/ai/rag_pipeline.py
import uuid
import tempfile
import os
import base64
import pickle  # Added for session persistence
from typing import Dict, List, Any, Optional
from langchain_community.document_loaders import UnstructuredPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.documents import Document
import json
import fitz

_sessions: Dict[str, Dict[str, Any]] = {}
SESSION_DIR = os.path.join(os.path.dirname(__file__), "sessions")  # Directory for session files

class RAGPipeline:
    def __init__(self, openai_api_key: str):
        print(f"Starting RAGPipeline initialization with API key: {openai_api_key[:4]}...{openai_api_key[-4:]}")
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY is not provided or empty")
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
            print("RAGPipeline initialized successfully")
        except Exception as e:
            print(f"RAGPipeline initialization failed: {str(e)}")
            raise ValueError(f"Failed to initialize RAGPipeline: {str(e)}")

    def save_session(self, session_id: str, session_data: Dict[str, Any]):
        """Save session data to disk."""
        try:
            os.makedirs(SESSION_DIR, exist_ok=True)
            session_file = os.path.join(SESSION_DIR, f"{session_id}.pkl")
            with open(session_file, 'wb') as f:
                pickle.dump(session_data, f)
            print(f"Saved session {session_id} to {session_file}")
        except Exception as e:
            print(f"Failed to save session {session_id}: {str(e)}")

    def load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load session data from disk."""
        session_file = os.path.join(SESSION_DIR, f"{session_id}.pkl")
        if os.path.exists(session_file):
            try:
                with open(session_file, 'rb') as f:
                    session_data = pickle.load(f)
                print(f"Loaded session {session_id} from {session_file}")
                return session_data
            except Exception as e:
                print(f"Failed to load session {session_id}: {str(e)}")
                return None
        return None

    async def upload_and_index_pdf(self, file_path: str) -> Dict[str, Any]:
        session_id = str(uuid.uuid4())
        # Check if session already exists (e.g., from previous upload)
        existing_session = self.load_session(session_id)
        if existing_session:
            print(f"Reusing existing session {session_id}")
            _sessions[session_id] = existing_session
            return {
                "session_id": session_id,
                "extracted_charts": existing_session.get("images", [])
            }
        
        try:
            print(f"Loading PDF: {file_path}")
            loader = UnstructuredPDFLoader(file_path, mode="elements")
            docs: List[Document] = loader.load()
            print(f"Extracted {len(docs)} documents from PDF")
            extracted_images = []
            pdf_doc = fitz.open(file_path)
            for page_num in range(len(pdf_doc)):
                page = pdf_doc[page_num]
                image_list = page.get_images(full=True)
                for img_index, img in enumerate(image_list):
                    xref = img[0]
                    base_image = pdf_doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]
                    if image_ext in ["png", "jpeg"]:
                        base64_image = base64.b64encode(image_bytes).decode('utf-8')
                        width, height = base_image["width"], base_image["height"]
                        if width > 100 and height > 100:
                            print(f"Analyzing image on page {page_num + 1}, index {img_index}")
                            desc_chain = self.image_desc_prompt | self.vision_llm | JsonOutputParser()
                            desc_result = await desc_chain.ainvoke({"base64_image": base64_image})
                            if desc_result.get("is_chart", False):
                                chart_doc = Document(
                                    page_content=desc_result["description"] + "\nData: " + json.dumps(desc_result.get("data_points", [])),
                                    metadata={"source": f"chart_page_{page_num}_img_{img_index}", "type": "chart"}
                                )
                                docs.append(chart_doc)
                            extracted_images.append({
                                "base64": f"data:image/{image_ext};base64,{base64_image}",
                                "page": page_num + 1,
                                "description": desc_result["description"],
                                "is_chart": desc_result.get("is_chart", False)
                            })
            pdf_doc.close()
            print(f"Extracted {len(extracted_images)} images, {sum(1 for img in extracted_images if img['is_chart'])} charts")
            splits = self.text_splitter.split_documents(docs)
            print(f"Split into {len(splits)} chunks")
            vector_store = FAISS.from_documents(splits, self.embeddings)
            session_data = {
                "vector_store": vector_store,
                "images": extracted_images
            }
            _sessions[session_id] = session_data
            self.save_session(session_id, session_data)
            if os.path.exists(file_path):
                os.unlink(file_path)
            return {
                "session_id": session_id,
                "extracted_charts": [img for img in extracted_images if img["is_chart"]]
            }
        except Exception as e:
            if os.path.exists(file_path):
                os.unlink(file_path)
            print(f"PDF processing failed: {str(e)}")
            raise ValueError(f"Failed to process PDF: {str(e)}")

    async def query(self, query: str, session_id: str) -> Dict[str, Any]:
        if session_id not in _sessions:
            # Try to load from disk
            session_data = self.load_session(session_id)
            if session_data:
                _sessions[session_id] = session_data
            else:
                raise ValueError("Invalid session_id. Upload PDF first or session expired.")
        session_data = _sessions[session_id]
        vector_store = session_data["vector_store"]
        retriever = vector_store.as_retriever(search_kwargs={"k": 4})
        relevant_docs = retriever.invoke(query)
        context = "\n\n".join([doc.page_content for doc in relevant_docs])
        viz_chain = self.viz_prompt | self.llm | JsonOutputParser()
        intent_result = await viz_chain.ainvoke({"query": query})
        result = {}
        if intent_result["intent"] == "viz":
            extracted_data = intent_result["extracted_data"]
            data_points_text = json.dumps(extracted_data["data_points"])
            from .analyzer import analyze_text_data
            analyzed = await analyze_text_data(data_points_text)
            from .analyzer import convert_to_chart_data
            chart_config = convert_to_chart_data(analyzed)
            answer_prompt = ChatPromptTemplate.from_template(
                """Based on context: {context}
                Answer: {query}
                If viz, mention the generated chart."""
            )
            answer_chain = answer_prompt | self.llm
            answer = await answer_chain.ainvoke({"context": context, "query": query})
            result = {
                "answer": answer.content,
                "intent": "viz",
                "chart_config": chart_config,
                "confidence": analyzed.confidence
            }
        else:
            qa_prompt = ChatPromptTemplate.from_template(
                """Context: {context}
                Question: {query}
                Answer concisely."""
            )
            qa_chain = qa_prompt | self.llm
            answer = await qa_chain.ainvoke({"context": context, "query": query})
            result = {
                "answer": answer.content,
                "intent": "qna",
                "sources": [doc.metadata for doc in relevant_docs]
            }
        if "chart" in query.lower() or "graph" in query.lower():
            result["existing_charts"] = session_data["images"]
        return result

def init_rag_pipeline(api_key: str):
    global rag_pipeline
    try:
        print(f"Initializing RAG pipeline with API key: {api_key[:4]}...{api_key[-4:]}")
        rag_pipeline = RAGPipeline(api_key)
        if rag_pipeline is None:
            raise ValueError("RAGPipeline constructor returned None")
        print("RAG pipeline initialized successfully")
    except Exception as e:
        print(f"Initialization failed: {str(e)}")
        rag_pipeline = None
        raise

# rag_pipeline = None