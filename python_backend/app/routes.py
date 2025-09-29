from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import datetime
import json

from app.ai.analyzer import (
    analyze_text_data,
    analyze_multiple_datasets_from_text,
    convert_to_chart_data,
    convert_multiple_datasets_to_configs,
    AnalyzedData,
    MultiChartAnalysis
)
from app.ai.csv_parser import parse_csv_data, ParsedCSV

router = APIRouter(prefix="/api")

class AnalyzeDataRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Text input is required")
    chart_type: Optional[str] = Field("auto", description="Chart type: auto, pie, bar, line")

class AnalyzeMultiRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Text input is required")
    max_charts: Optional[int] = Field(None, ge=3, le=10, description="Maximum number of charts")

class ParseCSVRequest(BaseModel):
    csv_content: str = Field(..., min_length=1, description="CSV content is required")

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

@router.get("/health")
def health():
    return {
        "status": "ok",
        "timestamp": datetime.datetime.now().isoformat()
    }