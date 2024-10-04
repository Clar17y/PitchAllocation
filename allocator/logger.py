import logging
import sys

def setup_logger(name):
    """Set up and return a logger with the given name."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        file_handler = logging.FileHandler("output/allocator.log", mode='a')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger