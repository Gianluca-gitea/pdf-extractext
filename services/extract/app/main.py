from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from app import __version__
from app.logging_config import configure_logging
from app.settings import get_settings

load_dotenv()
from app.routes import extract, health

settings = get_settings()
configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        yield
    finally:
        extract.shutdown_extraction_pool()


app = FastAPI(title=settings.app_name, version=__version__, lifespan=lifespan)
app.include_router(health.router)
app.include_router(extract.router)
