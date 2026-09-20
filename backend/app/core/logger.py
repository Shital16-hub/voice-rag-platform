import logging
import sys

def get_logger(name: str) -> logging.Logger:
    """
    Creates a simple logger for any file that needs it.
    
    Usage in any file:
        from app.core.logger import get_logger
        logger = get_logger(__name__)
        logger.info("Something happened")
        logger.error("Something failed")
    """
    
    logger = logging.getLogger(name)
    
    # avoid adding duplicate handlers if logger already exists
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.DEBUG)
    
    # create handler that prints to terminal
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    
    # define the format of each log line
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger