import logging
import sys


def configure_logging(level: str) -> None:
    logging.basicConfig(
        stream=sys.stdout,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logging.getLogger().setLevel(level)
