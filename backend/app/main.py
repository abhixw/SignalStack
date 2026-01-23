from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.config.database import engine
import app.models as models
# from app.routes import api

# Create tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="SignalLayer API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def debug_exception_handler(request, exc):
    import traceback
    print(f"Global Exception: {exc}")
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"message": str(exc)},
    )

from app.routes import outcome, task_decomposer, signal_extractor, evaluator, feedback

# Pipeline Routers
app.include_router(outcome.router)
app.include_router(task_decomposer.router)
app.include_router(signal_extractor.router)
app.include_router(evaluator.router)
app.include_router(feedback.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
