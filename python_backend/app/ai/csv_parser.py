import csv
from io import StringIO
from typing import List, Dict, Optional, Any
from fastapi import HTTPException

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

class ParsedCSV:
    def __init__(self, headers: List[str], rows: List[List[Any]], data_points: List[DataPoint], detected_columns: Dict[str, Optional[str]]):
        self.headers = headers
        self.rows = rows
        self.data_points = data_points
        self.detected_columns = detected_columns

    def to_dict(self) -> Dict[str, Any]:
        return {
            "headers": self.headers,
            "rows": self.rows,
            "dataPoints": [dp.to_dict() for dp in self.data_points],
            "detectedColumns": self.detected_columns
        }

def parse_csv_data(csv_content: str) -> ParsedCSV:
    """
    Parse CSV content into structured data for visualization.
    
    Args:
        csv_content (str): Raw CSV content as a string.
        
    Returns:
        ParsedCSV: Object containing headers, rows, data points, and detected columns.
        
    Raises:
        HTTPException: If CSV parsing fails or no valid data is found.
    """
    try:
        # Use StringIO to treat string as file-like object for csv.DictReader
        reader = csv.DictReader(StringIO(csv_content), skipinitialspace=True)
        data = list(reader)
        
        # Get headers (fieldnames) or default to empty list
        headers = reader.fieldnames or []
        if not headers:
            raise ValueError("No headers found in CSV")

        # Validate that we have data
        if not data:
            raise ValueError("No data rows found in CSV")

        # Detect label and value columns
        detected_columns = detect_columns(headers, data)

        # Convert rows to data points
        data_points = []
        for index, row in enumerate(data):
            label = row.get(detected_columns['label'] or '', f"Row {index + 1}")
            try:
                value_str = row.get(detected_columns['value'] or '', '0')
                value = float(value_str)
            except (ValueError, TypeError):
                value = 0.0  # Default to 0 for non-numeric values
            
            # Only include valid data points (non-zero values)
            if value != 0:
                data_points.append(DataPoint(
                    label=str(label),
                    value=value,
                    unit=None  # Unit detection can be added if needed
                ))

        # Convert data to rows (list of lists) for consistency with TS version
        rows = [list(row.values()) for row in data]

        # Ensure we have valid data points
        if not data_points:
            raise ValueError("No valid data points found in CSV")

        return ParsedCSV(
            headers=headers,
            rows=rows,
            data_points=data_points,
            detected_columns=detected_columns
        )

    except Exception as e:
        print(f"Error parsing CSV: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV file: {str(e)}")

def detect_columns(headers: List[str], data: List[Dict[str, Any]]) -> Dict[str, Optional[str]]:
    """
    Detect label and value columns in CSV data based on header names and content.
    
    Args:
        headers (List[str]): List of CSV headers.
        data (List[Dict[str, Any]]): Parsed CSV rows as dictionaries.
        
    Returns:
        Dict[str, Optional[str]]: Dictionary with 'label' and 'value' column names.
    """
    label_keywords = ['label', 'name', 'category', 'item', 'product', 'brand', 'type']
    value_keywords = ['value', 'amount', 'count', 'number', 'percentage', 'percent', 'quantity', 'total']

    label_column: Optional[str] = None
    value_column: Optional[str] = None

    # Find label column
    for header in headers:
        lower_header = header.lower()
        if any(keyword in lower_header for keyword in label_keywords):
            label_column = header
            break

    # Fallback: Use first non-numeric column as label
    if not label_column and data:
        for header in headers:
            first_value = data[0].get(header, '')
            if isinstance(first_value, str) and not first_value.replace('.', '', 1).isdigit():
                label_column = header
                break

    # Find value column
    for header in headers:
        lower_header = header.lower()
        if any(keyword in lower_header for keyword in value_keywords):
            value_column = header
            break

    # Fallback: Use first numeric column as value
    if not value_column and data:
        for header in headers:
            first_value = data[0].get(header, '')
            if isinstance(first_value, (int, float)) or (isinstance(first_value, str) and first_value.replace('.', '', 1).isdigit()):
                value_column = header
                break

    return {
        'label': label_column,
        'value': value_column
    }