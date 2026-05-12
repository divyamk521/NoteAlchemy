from src.utils.logger import setup_logger, get_logger

# setup logging system
setup_logger()

# create logger for this file
logger = get_logger(__name__)

logger.debug("This is a DEBUG log")
logger.info("This is an INFO log")
logger.warning("This is a WARNING log")
logger.error("This is an ERROR log")
logger.critical("This is a CRITICAL log")

print("Logger test completed")