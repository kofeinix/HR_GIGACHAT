import logging
from logging.handlers import RotatingFileHandler
import os

def set_logger(logger):
    """
    Create logger
    """
    logger.setLevel('DEBUG')
    handler = RotatingFileHandler("logs/neural.log", maxBytes=5000000, backupCount=5)
    handler.setLevel('DEBUG')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger
