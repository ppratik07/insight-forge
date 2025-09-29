import json
import os
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class DataPoint:
    def __init__(self, label: str, value: float, unit: Optional[str] = None):
        self.label = label
        self.value = value
        self.unit = unit

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "value": self.value,
            "unit": self.unit
        }


class AnalyzedData:
    def __init__(self, title: str, data_points: List[DataPoint], chart_type: str, confidence: float, description: str):
        self.title = title
        self.data_points = data_points
        self.chart_type = chart_type
        self.confidence = confidence
        self.description = description

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "dataPoints": [dp.to_dict() for dp in self.data_points],
            "chartType": self.chart_type,
            "confidence": self.confidence,
            "description": self.description
        }


class ChartVariation:
    def __init__(self, chart_type: str, confidence: float, reason: str, config: Optional[Dict[str, Any]] = None):
        self.chart_type = chart_type
        self.confidence = confidence
        self.reason = reason
        self.config = config

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chartType": self.chart_type,
            "confidence": self.confidence,
            "reason": self.reason,
            "config": self.config
        }


class MultiChartAnalysis:
    def __init__(self, title: str, data_points: List[DataPoint], description: str, chart_variations: List[ChartVariation]):
        self.title = title
        self.data_points = data_points
        self.description = description
        self.chart_variations = chart_variations

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "dataPoints": [dp.to_dict() for dp in self.data_points],
            "description": self.description,
            "chartVariations": [cv.to_dict() for cv in self.chart_variations]
        }


async def analyze_text_data(input_text: str) -> AnalyzedData:
    try:
        response = await client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {
                    "role": "system",
                    "content": """You are a data analysis expert. Analyze the given text and extract structured data for visualization. 

Rules:
1. Extract numerical data points with their labels
2. Determine the most appropriate chart type (pie, bar, or line)
3. Provide a confidence score (0-1) for your chart type recommendation
4. Generate a descriptive title
5. For percentages, ensure they add up to 100%% if they represent parts of a whole
6. For pie charts, use when data represents parts of a whole
7. For bar charts, use when comparing different categories
8. For line charts, use when showing trends over time

Respond with JSON in this exact format:
{
  "title": "Chart Title",
  "dataPoints": [
    {"label": "Category 1", "value": 25, "unit": "%"},
    {"label": "Category 2", "value": 50, "unit": "%"}
  ],
  "chartType": "pie",
  "confidence": 0.95,
  "description": "Brief description of what the data shows"
}"""
                },
                {
                    "role": "user",
                    "content": input_text
                }
            ],
            response_format={"type": "json_object"}
        )

        result_content = response.choices[0].message.content
        if not result_content:
            raise ValueError("Empty response from AI")

        result = json.loads(result_content)

        # Validate the response structure
        required_keys = ["title", "dataPoints", "chartType", "confidence", "description"]
        if not all(key in result for key in required_keys):
            raise ValueError("Invalid response format from AI")

        # Ensure confidence is between 0 and 1
        result["confidence"] = max(0.0, min(1.0, float(result["confidence"])))

        # Create DataPoint objects
        data_points = []
        for dp in result["dataPoints"]:
            data_points.append(DataPoint(
                label=dp["label"],
                value=float(dp["value"]),
                unit=dp.get("unit")
            ))

        return AnalyzedData(
            title=result["title"],
            data_points=data_points,
            chart_type=result["chartType"],
            confidence=result["confidence"],
            description=result["description"]
        )
    except Exception as e:
        print(f"Error analyzing data: {e}")
        raise ValueError(f"Failed to analyze data: {str(e)}")


async def analyze_text_data_multi_chart(input_text: str) -> MultiChartAnalysis:
    try:
        response = await client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {
                    "role": "system",
                    "content": """You are a data visualization expert. Analyze the given text and suggest multiple appropriate chart types for the same dataset.

Rules:
1. Extract numerical data points with their labels
2. Suggest 3-5 different chart types that could effectively visualize this data
3. For each chart type, provide a confidence score (0-1) and reasoning
4. Generate a descriptive title and description
5. Consider: pie, bar, line, doughnut, area, scatter charts
6. Rank suggestions by effectiveness for the specific data

Respond with JSON in this exact format:
{
  "title": "Dataset Title",
  "dataPoints": [
    {"label": "Category 1", "value": 25, "unit": "%"},
    {"label": "Category 2", "value": 50, "unit": "%"}
  ],
  "description": "Brief description of the dataset",
  "chartVariations": [
    {
      "chartType": "pie",
      "confidence": 0.95,
      "reason": "Perfect for showing proportions of a whole"
    },
    {
      "chartType": "bar", 
      "confidence": 0.85,
      "reason": "Good for comparing categories side-by-side"
    },
    {
      "chartType": "doughnut",
      "confidence": 0.80,
      "reason": "Modern alternative to pie chart with better readability"
    }
  ]
}"""
                },
                {
                    "role": "user",
                    "content": input_text
                }
            ],
            response_format={"type": "json_object"}
        )

        result_content = response.choices[0].message.content
        if not result_content:
            raise ValueError("Empty response from AI")

        result = json.loads(result_content)

        # Validate the response structure
        required_keys = ["title", "dataPoints", "description", "chartVariations"]
        if not all(key in result for key in required_keys) or not isinstance(result["chartVariations"], list):
            raise ValueError("Invalid response format from AI")

        # Create DataPoint objects
        data_points = []
        for dp in result["dataPoints"]:
            data_points.append(DataPoint(
                label=dp["label"],
                value=float(dp["value"]),
                unit=dp.get("unit")
            ))

        # Create ChartVariation objects
        chart_variations = []
        for variation in result["chartVariations"]:
            variation["confidence"] = max(0.0, min(1.0, float(variation["confidence"])))
            chart_variations.append(ChartVariation(
                chart_type=variation["chartType"],
                confidence=variation["confidence"],
                reason=variation["reason"]
            ))

        return MultiChartAnalysis(
            title=result["title"],
            data_points=data_points,
            description=result["description"],
            chart_variations=chart_variations
        )
    except Exception as e:
        print(f"Error analyzing data for multiple charts: {e}")
        raise ValueError(f"Failed to analyze data for multiple charts: {str(e)}")


# def convert_to_chart_data(analyzed_data: AnalyzedData) -> Dict[str, Any]:
#     labels = [point.label for point in analyzed_data.data_points]
#     values = [point.value for point in analyzed_data.data_points]

#     colors = [
#         '#3b82f6',  # blue
#         '#22c55e',  # green
#         '#f59e0b',  # amber
#         '#a855f7',  # purple
#         '#ef4444',  # red
#         '#06b6d4',  # cyan
#         '#f97316',  # orange
#         '#8b5cf6',  # violet
#     ]

#     background_color = colors[:len(values)]

#     base_config = {
#         "type": analyzed_data.chart_type,
#         "data": {
#             "labels": labels,
#             "datasets": [{
#                 "label": analyzed_data.title,
#                 "data": values,
#                 "backgroundColor": background_color,
#                 "borderWidth": 2,
#                 "borderColor": '#ffffff',
#             }]
#         },
#         "options": {
#             "responsive": True,
#             "maintainAspectRatio": False,
#             "plugins": {
#                 "title": {
#                     "display": True,
#                     "text": analyzed_data.title,
#                     "font": {
#                         "size": 16,
#                         "weight": 'bold'
#                     }
#                 },
#                 "legend": {
#                     "position": 'bottom',
#                 }
#             },
#             "animation": {
#                 "duration": 2000,
#                 "easing": 'easeInOutQuart'
#             }
#         }
#     }

#     # Chart type specific configurations
#     if analyzed_data.chart_type == 'bar':
#         base_config["options"]["scales"] = {
#             "y": {
#                 "beginAtZero": True,
#                 "grid": {
#                     "color": 'rgba(0, 0, 0, 0.1)'
#                 }
#             },
#             "x": {
#                 "grid": {
#                     "display": False
#                 }
#             }
#         }

#     if analyzed_data.chart_type == 'line':
#         base_config["data"]["datasets"][0].update({
#             "fill": False,
#             "borderColor": colors[0],
#             "backgroundColor": colors[0],
#             "tension": 0.4
#         })
#         base_config["options"]["scales"] = {
#             "y": {
#                 "beginAtZero": True,
#                 "grid": {
#                     "color": 'rgba(0, 0, 0, 0.1)'
#                 }
#             },
#             "x": {
#                 "grid": {
#                     "display": False
#                 }
#             }
#         }

#     return base_config



# ... (keep existing imports and classes unchanged)

def convert_to_chart_data(analyzed_data: AnalyzedData) -> Dict[str, Any]:
    labels = [point.label for point in analyzed_data.data_points]
    values = [point.value for point in analyzed_data.data_points]

    colors = [
        '#3b82f6',  # blue
        '#22c55e',  # green
        '#f59e0b',  # amber
        '#a855f7',  # purple
        '#ef4444',  # red
        '#06b6d4',  # cyan
        '#f97316',  # orange
        '#8b5cf6',  # violet
    ]

    background_color = colors[:len(values)]

    base_config = {
        "type": analyzed_data.chart_type,
        "data": {
            "labels": labels,
            "datasets": [{
                "label": analyzed_data.title,
                "data": values,
                "backgroundColor": background_color,
                "borderWidth": 2,
                "borderColor": '#ffffff',
            }]
        },
        "options": {
            "responsive": True,
            "maintainAspectRatio": False,
            "plugins": {
                "title": {
                    "display": True,
                    "text": analyzed_data.title,
                    "font": {
                        "size": 16,
                        "weight": 'bold'
                    }
                },
                "legend": {
                    "position": 'bottom',
                    "labels": {
                        "color": '#4B5563',  # Default dark gray, suitable for light theme
                        "font": {
                            "size": 14
                        }
                    }
                }
            },
            "animation": {
                "duration": 2000,
                "easing": 'easeInOutQuart'
            }
        }
    }

    # Chart type specific configurations
    if analyzed_data.chart_type == 'bar':
        base_config["options"]["scales"] = {
            "y": {
                "beginAtZero": True,
                "grid": {
                    "color": 'rgba(0, 0, 0, 0.1)'
                }
            },
            "x": {
                "grid": {
                    "display": False
                }
            }
        }

    if analyzed_data.chart_type == 'line':
        base_config["data"]["datasets"][0].update({
            "fill": False,
            "borderColor": colors[0],
            "backgroundColor": colors[0],
            "tension": 0.4
        })
        base_config["options"]["scales"] = {
            "y": {
                "beginAtZero": True,
                "grid": {
                    "color": 'rgba(0, 0, 0, 0.1)'
                }
            },
            "x": {
                "grid": {
                    "display": False
                }
            }
        }

    return base_config



# ... (keep other functions like convert_multi_chart_to_configs unchanged)


async def analyze_multiple_datasets_from_text(input_text: str) -> Dict[str, Any]:
    try:
        response = await client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {
                    "role": "system",
                    "content": """You are a data visualization expert. Analyze the given text and identify ALL DISTINCT datasets that can be visualized separately.

CRITICAL RULES:
1. Look for MULTIPLE DIFFERENT data categories/topics in the input text
2. Each dataset should represent a DIFFERENT concept (e.g., work preferences, revenue growth, device usage, etc.)
3. Extract each dataset as a separate chart with its own title, data points, and best chart type
4. DO NOT create variations of the same dataset - create separate datasets
5. Automatically select the BEST chart type for each dataset:
   - Pie/Doughnut: For parts of a whole (percentages that sum to 100%)
   - Bar: For comparing different categories 
   - Line: For trends over time or sequential data
6. Provide confidence score and reasoning for each chart type selection

Example input: "50% prefer A, 30% prefer B, 20% prefer C. Sales grew from $1M to $3M over 3 years."
Expected output: 2 datasets (preferences pie chart, revenue growth line chart)

Respond with JSON in this exact format:
{
  "datasets": [
    {
      "title": "Work Preference Distribution",
      "dataPoints": [
        {"label": "Remote Work", "value": 65, "unit": "%"},
        {"label": "Office Work", "value": 35, "unit": "%"}
      ],
      "chartType": "pie",
      "confidence": 0.95,
      "description": "Employee work location preferences"
    },
    {
      "title": "Revenue Growth Over Time", 
      "dataPoints": [
        {"label": "2021", "value": 2, "unit": "M"},
        {"label": "2023", "value": 5, "unit": "M"}
      ],
      "chartType": "line",
      "confidence": 0.90,
      "description": "Company revenue growth from 2021 to 2023"
    }
  ],
  "totalAnalyzedDatasets": 2,
  "description": "Analysis found 2 distinct datasets for visualization"
}"""
                },
                {
                    "role": "user",
                    "content": input_text
                }
            ],
            response_format={"type": "json_object"}
        )

        result_content = response.choices[0].message.content
        if not result_content:
            raise ValueError("Empty response from AI")

        result = json.loads(result_content)

        # Validate the response structure
        if "datasets" not in result or not isinstance(result["datasets"], list) or len(result["datasets"]) == 0:
            raise ValueError("Invalid response format from AI - no datasets found")

        datasets = []
        for dataset_data in result["datasets"]:
            # Validate each dataset
            required_keys = ["title", "dataPoints", "chartType", "confidence", "description"]
            if not all(key in dataset_data for key in required_keys):
                raise ValueError("Invalid dataset structure")

            dataset_data["confidence"] = max(0.0, min(1.0, float(dataset_data["confidence"])))

            data_points = []
            for dp in dataset_data["dataPoints"]:
                data_points.append(DataPoint(
                    label=dp["label"],
                    value=float(dp["value"]),
                    unit=dp.get("unit")
                ))

            datasets.append(AnalyzedData(
                title=dataset_data["title"],
                data_points=data_points,
                chart_type=dataset_data["chartType"],
                confidence=dataset_data["confidence"],
                description=dataset_data["description"]
            ))

        result["datasets"] = datasets
        result["totalAnalyzedDatasets"] = len(datasets)

        return result
    except Exception as e:
        print(f"Error analyzing multiple datasets: {e}")
        raise ValueError(f"Failed to analyze multiple datasets: {str(e)}")


def convert_multi_chart_to_configs(multi_chart_data: MultiChartAnalysis) -> List[Dict[str, Any]]:
    labels = [point.label for point in multi_chart_data.data_points]
    values = [point.value for point in multi_chart_data.data_points]

    colors = [
        '#3b82f6', '#22c55e', '#f59e0b', '#ef4444',
        '#8b5cf6', '#06b6d4', '#f97316', '#84cc16'
    ]

    configs = []
    for index, variation in enumerate(multi_chart_data.chart_variations):
        base_config = {
            "type": variation.chart_type,
            "data": {
                "labels": labels,
                "datasets": [{
                    "label": f"{multi_chart_data.title} ({variation.chart_type})",
                    "data": values,
                    "backgroundColor": colors[:len(values)],
                    "borderWidth": 2,
                    "borderColor": '#ffffff',
                }]
            },
            "options": {
                "responsive": True,
                "maintainAspectRatio": False,
                "plugins": {
                    "title": {
                        "display": True,
                        "text": f"{multi_chart_data.title} ({variation.chart_type.capitalize()})",
                        "font": {
                            "size": 16,
                            "weight": 'bold'
                        }
                    },
                    "legend": {
                        "position": 'bottom'
                    }
                },
                "animation": {
                    "duration": 2000,
                    "easing": 'easeInOutQuart',
                    "delay": index * 200  # Stagger animations
                }
            },
            "metadata": {
                "confidence": variation.confidence,
                "reason": variation.reason,
                "rank": index + 1
            }
        }

        # Chart-specific configurations
        if variation.chart_type in ['bar', 'line', 'area', 'scatter']:
            base_config["options"]["scales"] = {
                "y": {
                    "beginAtZero": True,
                    "grid": {"color": 'rgba(0, 0, 0, 0.1)'}
                },
                "x": {
                    "grid": {"display": False}
                }
            }

        if variation.chart_type in ['line', 'area']:
            base_config["data"]["datasets"][0].update({
                "fill": variation.chart_type == 'area',
                "borderColor": '#3b82f6',
                "backgroundColor": 'rgba(59, 130, 246, 0.2)' if variation.chart_type == 'area' else 'transparent',
                "tension": 0.4
            })

        if variation.chart_type == 'scatter':
            base_config["data"]["datasets"][0].update({
                "pointRadius": 8,
                "pointHoverRadius": 12,
                "backgroundColor": '#3b82f6',
                "borderColor": '#1d4ed8'
            })

        configs.append(base_config)

    return configs


def convert_multiple_datasets_to_configs(datasets: List[AnalyzedData]) -> List[Dict[str, Any]]:
    configs = []
    for index, dataset in enumerate(datasets):
        chart_config = convert_to_chart_data(dataset)
        chart_config["metadata"] = {
            "confidence": dataset.confidence,
            "reason": dataset.description,
            "rank": index + 1,
            "datasetIndex": index
        }
        configs.append(chart_config)
    return configs

