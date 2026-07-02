import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi import HTTPException

from dotenv import load_dotenv
load_dotenv()

from core.db import engine, Base
from core.auth_routes import router as auth_router
from core.documents_routes import router as docs_router

app = FastAPI(
    title="Compliance Sentinel API",
    description="Backend API for PII detection, risk classification, and RAG-based QA",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(docs_router)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


dist_dir = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.exists(dist_dir):
    app.mount("/assets", StaticFiles(directory=os.path.join(dist_dir, "assets")), name="assets")

    @app.get("/{catchall:path}")
    async def serve_vue_app(catchall: str):
        if catchall.startswith("api/"):
            raise HTTPException(status_code=404, detail="API endpoint not found")
        index_path = os.path.join(dist_dir, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"message": "Frontend assets found, but index.html was missing."}
else:
    @app.get("/{catchall:path}")
    async def no_frontend(catchall: str):
        if catchall.startswith("api/"):
            raise HTTPException(status_code=404, detail="API endpoint not found")
        return {"message": "Frontend dev environment active. Run npm run dev in frontend/ or compile using npm run build."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
