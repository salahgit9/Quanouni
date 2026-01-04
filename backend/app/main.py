from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import router as api_router

app = FastAPI(title="NIBRASSE")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import os
from fastapi.responses import FileResponse

# Include API Router
app.include_router(api_router, prefix="/api")

# Include Legal Router
from app.api.legal import router as legal_router
app.include_router(legal_router, prefix="/api")

# Mount static files (Frontend)
# Try to find the frontend directory (assuming it's in ../frontend_new relative to backend/)
frontend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend_new"))

if os.path.exists(frontend_path):
    # Mount the entire frontend directory at the root
    # html=True allows serving index.html automatically at /
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
else:
    print(f"⚠️ Warning: Frontend directory not found at {frontend_path}. API will work, but static files won't be served.")

