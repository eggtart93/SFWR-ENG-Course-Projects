#!/usr/bin/python
# grade_server.py


# Computer Enginnering: Advanced Network Communications
# 
# <Topic: Remote Grade Recording System Based on TCP Client/Server>
#
# Author: Jin Kuan Zhou <zhoujk93@hotmail.com>
# Date: 2016-01-21


import sys
import logging
from socket import *
from struct import *

ADD_OP = 0xF0
CHANGE_OP = 0xF1
LIST_OP = 0xF2
SEARCH_OP = 0xF3
QUIT_OP = 0xF4
UNKNOWN_OP = 0x00

SUCCESS = 0x1F
FAILURE = 0x0F

DELIM = ':'

class GradeServer(object):
    """
    This is the TCP Server class which can be used to
    handle requests from TA/Student clients and it 
    encapsulates all necessary operations to manipulate
    the grade database.
    """
    
    TAG = "GradeServer"
    RECV_BUFFER_SIZE = 1024

    def __init__(self, logger, host, port):
        self.host = host
        self.port = port
        self.server = socket()
        self.client = None
        self.__is_running = False
        self.server.bind((host, port))
        self.db_mangr = DatabaseManager(logger)
        self.logger = logger

    # with-statement support
    def __enter__(self):
        return self

    # with-statement support
    def __exit__(self, type, value, traceback):
        self.close()

    def run(self):
        #self.__wait_for_client()

        self.__is_running = True
        while self.__is_running:
            if self.client is None:
                self.__wait_for_client()
            response = None
            request = self.__recv_request()

            if request is None:
                self.client.close()
                self.client = None
                continue
            else:
                response = self.__generate_pkt(self.__handle_request(request))

            if response is not None:
                self.__send_response(response)

    def __wait_for_client(self):
        self.server.listen(5)
        self.logger.info("%s: Host:%s, Listening at Port:%d", self.TAG,self.host,self.port)
        self.client, addr = self.server.accept()
        self.logger.info("%s: Connected by %s", self.TAG, str(addr))
        self.client.setblocking(1)

    def __recv_request(self):
        try:
            # blocking call here
            pkt = self.client.recv(self.RECV_BUFFER_SIZE)
        except error as e:
            self.logger.error("%s: recv failure:%s", self.TAG, e.strerror)
        else:
            if pkt == "":
                self.logger.error("%s: Lost connection to client", self.TAG)
            else:
                # Assume it is a valid packet with correct format
                bytes, op = unpack("!hB", pkt[0:3])
                param = unpack("!%ds" % (bytes), pkt[3:])[0]

                self.logger.debug("%s: Packet arrived (%d bytes): Header:%s",
                                   self.TAG, len(pkt), (bytes, op))
                return (op,param)
        return None

    def __send_response(self, packet):
        self.client.sendall(packet)
        self.logger.debug("%s: Packet sent (%d bytes).", self.TAG, len(packet))

    def close(self):
        self.logger.info("%s: shutting down", self.TAG)
        if self.client is not None:
            self.client.close()
        if self.server is not None:
            self.server.close()
        if self.db_mangr is not None:
            self.db_mangr.close()
        self.client = None
        self.server = None
        self.logger = None


    def __handle_request(self, request):
        response = ""

        if request[0] == ADD_OP:
            args = request[1]
            args = args.split(DELIM)
            self.logger.info("%s: Recv Request: ADD %s %s %s",
                                self.TAG, args[0], args[1], args[2])
            response = self.db_mangr.add(args[0], args[1], args[2])

        elif request[0] == CHANGE_OP:
            args = request[1].split(DELIM)
            self.logger.info("%s: Recv Request: CHANGE %s %s %s",
                                self.TAG, args[0], args[1], args[2])
            response = self.db_mangr.change(args[0], args[1], args[2])

        elif request[0] == LIST_OP:
            self.logger.info("%s: Recv Request: LIST", self.TAG)
            response = self.db_mangr.list_all()

        elif request[0] == SEARCH_OP:
            args = request[1].split(DELIM)
            self.logger.info("%s: Recv Request: SEARCH %s %s", self.TAG, args[0], args[1])
            response = self.db_mangr.query(args[0], args[1])

        else:
            response = "Unknown Request Type: ", request[0]

        return response

    def __generate_pkt(self, response):
        if response:
            return pack("!hB%ds" % (len(response[1])), len(response[1]), response[0], response[1])
        else:
            return None


import sqlite3
class DatabaseManager(object):
    """
    As the class name implies, this class is used to manage the SQLite
    database, it abstracts some of the fundamental SQLite methods, so
    that user can interact with the database without knowing the SQLite
    CMDs and Syntaxs
    """

    TAG = "DatabaseManager"
    DB_NAME = "students_grades.db"
    TABLE_NAME = "grades"

    def __init__(self, logger):
        self.logger = logger
        self.db = sqlite3.connect(self.DB_NAME)
        sql_cmd = '''CREATE TABLE IF NOT EXISTS %s
                  (ID   CHAR(6) PRIMARY KEY NOT NULL,
                  NAME  TEXT            NOT NULL,
                  GRADE CHAR(2)         NOT NULL);''' % (self.TABLE_NAME)
        self.db.execute(sql_cmd)
        self.logger.info("%s: Connected to Database", self.TAG)

    # with-statement support
    def __enter__(self):
        return self

    # with-statement support
    def __exit__(self, type, value, traceback):
        self.close()

    def close(self):
        self.logger.debug("%s:close()", self.TAG)
        if self.db is not None:
            self.db.close()

    def query(self, name, id):
        msg = ""
        status = FAILURE
        record = None
        try:
            cursor = self.db.cursor()
            cursor.execute('''SELECT * FROM %s WHERE ID = ? AND NAME = ?''' % (self.TABLE_NAME),
                            (id, name))
            record = cursor.fetchone()
        except sqlite3.Error as e:
            self.logger.error("%s: query():%s", self.TAG, e.args[0])
            msg = "Error occurred when query"
        else:
            if record is None: msg = "Record not exist"
            else:
                msg = self.to_table((record,))
                status = SUCCESS
        return (status, msg)

    def list_all(self):
        cursor = self.db.cursor()
        status = FAILURE
        msg = ""
        try:
            cursor.execute('''SELECT * FROM %s''' % (self.TABLE_NAME))
            all = cursor.fetchall()
        except sqlite3.Error as e:
            self.logger.error("%s: list_all():%s", self.TAG, e.args[0])
            msg = "Error occurred when fetching data from database"
        else:
            #self.logger.info("%s:list_all():\n%s", self.TAG, all)
            msg = self.to_table(all)
            status = SUCCESS
        return (status, msg)

    def add(self, name, id, grade):
        msg = ""
        status = FAILURE
        try:
            cursor = self.db.cursor()
            cursor.execute('''INSERT INTO %s (ID, NAME, GRADE) VALUES (?,?,?)'''%(self.TABLE_NAME),
                            (id, name, grade))
            self.db.commit()
        except sqlite3.IntegrityError as e:
            self.logger.error("%s: add():%s", self.TAG, e.args[0])
            msg = "This ID is already in used"
        except sqlite3.Error as e:
            self.logger.error("%s: add():%s", self.TAG, e.args[0])
            msg = "Error occurred when adding new entry to database"
        else:
            if cursor.rowcount == 0: msg = "Record not add to database"
            else:
                msg = "New record added"
                status = SUCCESS
            self.logger.info("%s: %s", self.TAG, msg)
        return (status, msg)

    def change(self, name, id, grade):
        cursor = self.db.cursor()
        status = FAILURE
        msg = ""
        try:
            cursor.execute('''UPDATE %s SET GRADE = ? WHERE ID = ? AND NAME = ?''' % (self.TABLE_NAME),
                            (grade, id, name))
            self.db.commit()
        except sqlite3.Error as e:
            self.logger.error("%s: change():%s", self.TAG, e.args[0])
            msg = "Change not add to database"
        else:
            if cursor.rowcount == 0: msg = "Database not update"
            else:
                msg = "Database updated"
                status = SUCCESS
            self.logger.info("%s: %s", self.TAG, msg)
        return (status, msg)

    def to_table(self, list):
        table = "|\tID\t|\tName\t|\tGrade\t|\n"
        for item in list:
            table += "|\t{0}\t|\t{1}\t|\t{2}\t|\n".format(item[0], item[1], item[2])
        return table
