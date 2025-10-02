import os
from dotenv import load_dotenv
from app.ai.csv_parser import parse_csv_data, ParsedCSV
from app.ai.rag_pipeline import init_rag_pipeline, rag_pipeline



load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
print(api_key)