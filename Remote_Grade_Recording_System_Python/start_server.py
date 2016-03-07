#!/usr/bin/python
# start_server.py


# Computer Enginnering: Advanced Network Communications
# 
# <Topic: Remote Grade Recording System Based on TCP Client/Server>
#
# Author: Jin Kuan Zhou <zhoujk93@hotmail.com>
# Date: 2016-01-21


import logging
import socket
from grade_server import GradeServer

def init_logger():
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    # create file handler which logs even debug messages
    fh = logging.FileHandler('grade_server.log')
    fh.setLevel(logging.DEBUG)
    
    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    
    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s %(levelname)s:%(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    
    # add the handlers to the logger
    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger

if __name__ == '__main__':
    #print "Host:", config.Debug.HOST, "Port:", config.Debug.PORT

    logger = init_logger()
    host = socket.gethostname()
    port = 8080
    
    with GradeServer(logger, host, port) as server:
        server.run()
