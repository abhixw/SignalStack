import logging
import traceback
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config.config import config
from app.config import database as db_module

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("recruvoskill")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db_module.connect_to_mongo()
    yield
    await db_module.close_mongo_connection()


app = FastAPI(title="Recruvoskill API", lifespan=lifespan)

# CORS — explicit allowlist from CORS_ORIGINS (never "*" together with credentials).
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    connected = await db_module.ping()
    return {"status": "ok" if connected else "degraded", "database": "connected" if connected else "unavailable"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = str(uuid.uuid4())
    # Full detail always goes to server-side logs, never to the client.
    logger.error("Unhandled exception [request_id=%s] on %s %s", request_id, request.method, request.url.path)
    logger.error(traceback.format_exc())

    if config.IS_PRODUCTION:
        content = {"detail": "Internal server error", "request_id": request_id}
    else:
        # Development only: surface the exception message to speed up debugging.
        content = {"detail": str(exc), "request_id": request_id}

    return JSONResponse(status_code=500, content=content)


from app.routes import outcome, task_decomposer, signal_extractor, evaluator, feedback, candidate, auth, public

app.include_router(auth.router)
app.include_router(public.router)
app.include_router(outcome.router)
app.include_router(task_decomposer.router)
app.include_router(signal_extractor.router)
app.include_router(evaluator.router)
app.include_router(feedback.router)
app.include_router(candidate.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
