import logging

from dotenv import load_dotenv

from app.logging_config import configure_logging
from app.repositories.document_repository import get_document_repository
from app.settings import get_settings

logger = logging.getLogger(__name__)


def main() -> None:
    load_dotenv()
    configure_logging(get_settings().log_level)
    get_document_repository().ensure_indexes()
    logger.info("Admin task create_indexes finished")


if __name__ == "__main__":
    main()
