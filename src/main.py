from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from src.api_routes import router
from src.ui import get_ui_html

app = FastAPI(title="Personal Knowledge Graph", version="1.0.0")

app.include_router(router, prefix="/api")

@app.get("/", response_class=HTMLResponse)
async def root():
    return get_ui_html()

@app.get("/health")
async def health():
    return {"status": "healthy"}
