import logging
import time


def event_handler() -> None:
    logger = logging.getLogger(__name__)
    logger.info("Event handler")
    while True:
        logger.info("NOT IMPLEMENTED")
        time.sleep(60)  # Wait next event
