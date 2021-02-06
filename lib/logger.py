# encoding: utf-8
import logging

logging.basicConfig()

def new(mod_name):
    logger = logging.getLogger(mod_name)
    logger.setLevel(logging.DEBUG)
    return logger
