import os
from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import uvicorn
import datetime

from app.routes import router  # We'll define this below

# Load environment variables
load_dotenv()
print(f"Loaded OPENAI_API_KEY: {os.getenv('OPENAI_API_KEY')[:4]}...{os.getenv('OPENAI_API_KEY')[-4:]}")

app = FastAPI(title="ChartAI Backend")

# CORS for dev (adjust origins as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware for logging (like your Express logger)
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = datetime.datetime.now()
    response = await call_next(request)
    duration = (datetime.datetime.now() - start_time).total_seconds() * 1000
    path = request.url.path
    if path.startswith("/api"):
        print(f"{request.method} {path} {response.status_code} in {duration:.2f}ms")
    return response

# Global exception handler (like your Express error handler)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"message": str(exc) or "Internal Server Error"},
    )

# Include routes
app.include_router(router)

# Serve static files (client) in prod/dev
client_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "client"))
if os.path.exists(client_path):
    app.mount("/", StaticFiles(directory=client_path, html=True), name="static")
else:
    print("Warning: Client directory not found for static serving.")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)