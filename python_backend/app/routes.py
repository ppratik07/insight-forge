# # python_backend/app/routes.py
# from fastapi import APIRouter, Body, HTTPException, UploadFile, File, Form
# from pydantic import BaseModel, Field
# from typing import Optional, List, Dict, Any
# import datetime
# import json
# import tempfile
# import os
# import uuid

# from app.ai.analyzer import (
#     analyze_text_data,
#     analyze_multiple_datasets_from_text,
#     convert_to_chart_data,
#     convert_multiple_datasets_to_configs,
#     AnalyzedData,
#     MultiChartAnalysis
# )
# from app.ai.csv_parser import parse_csv_data, ParsedCSV
# import app.ai.rag_pipeline as rag_mod  # Import as module

# # Initialize RAG
# api_key = os.getenv("OPENAI_API_KEY")
# if not api_key:
#     print("Error: OPENAI_API_KEY not found in environment")
#     raise Exception("RAG initialization error: OPENAI_API_KEY not found")
# try:
#     print("Attempting to initialize RAG pipeline...")
#     rag_mod.init_rag_pipeline(api_key)
#     if rag_mod.rag_pipeline is None:
#         print("Error: RAG pipeline initialization returned None")
#         raise ValueError("Failed to initialize RAG pipeline: rag_pipeline is None")
#     print("RAG pipeline loaded successfully")
# except Exception as e:
#     print(f"Failed to initialize RAG pipeline: {str(e)}")
#     raise Exception(f"RAG initialization error: {str(e)}")

# router = APIRouter(prefix="/api")


# python_backend/app/routes.py
from fastapi import APIRouter, Body, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import datetime
import json
import tempfile
import os
import uuid

from app.ai.analyzer import (
    analyze_text_data,
    analyze_multiple_datasets_from_text,
    convert_to_chart_data,
    convert_multiple_datasets_to_configs,
    AnalyzedData,
    MultiChartAnalysis
)
from app.ai.csv_parser import parse_csv_data, ParsedCSV
import app.ai.rag_pipeline as rag_mod

# Initialize RAG
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("Error: OPENAI_API_KEY not found in environment")
    raise Exception("RAG initialization error: OPENAI_API_KEY not found")
try:
    print("Attempting to initialize RAG pipeline...")
    rag_mod.init_rag_pipeline(api_key)
    if rag_mod.rag_pipeline is None:
        print("Error: RAG pipeline initialization returned None")
        raise ValueError("Failed to initialize RAG pipeline: rag_pipeline is None")
    print("RAG pipeline loaded successfully")
except Exception as e:
    print(f"Failed to initialize RAG pipeline: {str(e)}")
    raise Exception(f"RAG initialization error: {str(e)}")

router = APIRouter(prefix="/api")

# ... (rest of the routes unchanged, as previously provided)

class AnalyzeDataRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Text input is required")
    chart_type: Optional[str] = Field("auto", description="Chart type: auto, pie, bar, line")

class AnalyzeMultiRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Text input is required")
    max_charts: Optional[int] = Field(None, ge=3, le=10, description="Maximum number of charts")

class ParseCSVRequest(BaseModel):
    csv_content: str = Field(..., min_length=1, description="CSV content is required")

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Question about the PDF")
    session_id: str = Field(..., description="Session ID from PDF upload")

@router.post("/analyze-data")
async def analyze_data(req: AnalyzeDataRequest = Body(...)):
    try:
        analyzed: AnalyzedData = await analyze_text_data(req.text)
        
        # Override chart type if specified and not auto
        if req.chart_type != "auto":
            analyzed.chart_type = req.chart_type
        
        chart_config: Dict[str, Any] = convert_to_chart_data(analyzed)
        
        return {
            "success": True,
            "data": {
                "analyzedData": analyzed.to_dict(),
                "chartConfig": chart_config,
                "confidence": {
                    analyzed.chart_type: analyzed.confidence,
                    "auto": 1.0
                }
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze data: {str(e)}")

@router.post("/parse-csv")
async def parse_csv(req: ParseCSVRequest = Body(...)):
    try:
        parsed: ParsedCSV = parse_csv_data(req.csv_content)
        
        # Convert parsed data to text format for analysis
        text_data = ", ".join([f"{point.label}: {point.value}" for point in parsed.data_points])
        
        if not text_data:
            raise ValueError("No valid data points found in CSV")
        
        analyzed: AnalyzedData = await analyze_text_data(text_data)
        chart_config: Dict[str, Any] = convert_to_chart_data(analyzed)
        
        return {
            "success": True,
            "data": {
                "parsedCSV": parsed.to_dict(),
                "analyzedData": analyzed.to_dict(),
                "chartConfig": chart_config,
                "confidence": {
                    analyzed.chart_type: analyzed.confidence,
                    "auto": 1.0
                }
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse CSV data: {str(e)}")

@router.post("/analyze-data-multi")
async def analyze_data_multi(req: AnalyzeMultiRequest = Body(...)):
    try:
        # Use the function that identifies multiple different datasets
        multi_dataset_analysis: Dict[str, Any] = await analyze_multiple_datasets_from_text(req.text)
        
        datasets: List[AnalyzedData] = multi_dataset_analysis["datasets"]
        
        # Limit the number of datasets if specified
        if req.max_charts and len(datasets) > req.max_charts:
            datasets = datasets[:req.max_charts]
        
        chart_configs: List[Dict[str, Any]] = convert_multiple_datasets_to_configs(datasets)
        
        # Create a compatible structure for the frontend (mimicking MultiChartAnalysis)
        multi_chart_analysis = {
            "title": "Multi-Dataset Analysis",
            "description": multi_dataset_analysis.get("description", ""),
            "chartVariations": [
                {
                    "chartType": dataset.chart_type,
                    "confidence": dataset.confidence,
                    "reason": dataset.description,
                    "title": dataset.title
                } for dataset in datasets
            ]
        }
        
        return {
            "success": True,
            "data": {
                "multiChartAnalysis": multi_chart_analysis,
                "chartConfigs": chart_configs,
                "totalCharts": len(chart_configs)
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze data for multiple charts: {str(e)}")

@router.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(..., media_type="application/pdf")):
    try:
        if rag_mod.rag_pipeline is None:
            raise ValueError("RAG pipeline not initialized")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        # Index and extract
        upload_result = await rag_mod.rag_pipeline.upload_and_index_pdf(tmp_path)
        
        return {
            "success": True,
            "session_id": upload_result["session_id"],
            "extracted_charts": upload_result["extracted_charts"],
            "message": "PDF uploaded, indexed, and charts extracted successfully."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload PDF: {str(e)}")

@router.post("/query")
async def query_pdf(req: QueryRequest = Body(...)):
    try:
        if rag_mod.rag_pipeline is None:
            raise ValueError("RAG pipeline not initialized")
        result = await rag_mod.rag_pipeline.query(req.query, req.session_id)
        return {
            "success": True,
            "data": result
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query PDF: {str(e)}")


@router.delete("/clear-session/{session_id}")
async def clear_session(session_id: str):
    try:
        session_file = os.path.join(SESSION_DIR, f"{session_id}.pkl")
        if os.path.exists(session_file):
            os.unlink(session_file)
            _sessions.pop(session_id, None)
            return {"success": True, "message": f"Session {session_id} cleared"}
        return {"success": True, "message": f"Session {session_id} not found"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear session: {str(e)}")

@router.get("/health")
def health():
    return {
        "status": "ok",
        "timestamp": datetime.datetime.now().isoformat()
    }