import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database.session import check_database_connection, initialize_database
from routers.auth_router import router as auth_router
from routers.chat_router import router as chat_router
from routers.reset_router import router as reset_router
from routers.upload_router import router as upload_router


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    try:
        check_database_connection()
        logger.info("Database connection established successfully.")
    except Exception as exc:
        logger.exception("Database connectivity check failed: %s", exc)
        raise
    yield


app = FastAPI(title="My Finance Buddy API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_origin_regex=r"^http://(10(?:\.\d{1,3}){3}|192\.168(?:\.\d{1,3}){2}|172\.(1[6-9]|2\d|3[0-1])(?:\.\d{1,3}){2})(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router)
app.include_router(chat_router)
app.include_router(reset_router)
app.include_router(auth_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
