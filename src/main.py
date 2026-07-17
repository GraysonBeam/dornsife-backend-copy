import logging
import os

from dotenv import load_dotenv

load_dotenv()


def _configure_logging() -> None:
    raw = os.getenv("LOG_LEVEL", "DEBUG").upper()
    level = getattr(logging, raw, logging.INFO)
    if not isinstance(level, int):
        level = logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True,
    )


_configure_logging()

from fastapi import FastAPI

from src.Controllers.AccountsController import accounts_router
from src.Controllers.AttendanceController import attendance_router
from src.Controllers.EventsController import events_router
from src.Controllers.GetDataController import data_router
from src.Controllers.UserRegisterController import user_register_router

app = FastAPI(
    title="Dornsife Backend API",
    description="Backend API for Dornsife project",
    version="0.1.0",
)

app.include_router(user_register_router, prefix="/userRegistration")
app.include_router(accounts_router, prefix="/accounts")
app.include_router(events_router, prefix="/events")
app.include_router(attendance_router, prefix="/attendance")
app.include_router(data_router, prefix="/data")


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "Dornsife Backend API is running"}


@app.get("/health")
async def health():
    """Health check endpoint for monitoring."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.main:app", host="127.0.0.1", port=8000, reload=True)
