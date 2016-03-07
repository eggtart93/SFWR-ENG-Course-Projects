#!/usr/bin/python
# client.py

 
# Computer Enginnering: Advanced Network Communications
# 
# <Topic: Remote Grade Recording System Based on TCP Client/Server>
#
# Author: Jin Kuan Zhou <zhoujk93@hotmail.com>
# Date: 2016-01-21


import sys
import socket
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

class Client(object):
    """
    This is the TCP Client class which encapsulates
    all necessary operations to communicate to the
    grade server.
    """

    TAG = "Client"
    RECV_BUFFER_SIZE = 1024
    STUDENT = "Student"
    TA = "TA"

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.client = socket.socket()
        self.__is_running = False
        self.user = ""

    # with-statement support
    def __enter__(self):
        return self

    # with-statement support
    def __exit__(self, type, value, traceback):
        self.__close()

    def __close(self):
        print "%s: Shutting down" % (self.TAG)
        if self.client is not None: self.client.close()
        self.client = None

    def run(self):
        print "%s: start running" % (self.TAG)

        self.client.connect((self.host, self.port))

        self.user = self.TA if self.__select_user() == 1 else self.STUDENT

        self.__is_running = True
        while self.__is_running:
            cmd = self.__read_ta_cmd() if self.user == self.TA else self.__read_st_cmd()
            if cmd is None: break

            client_pkt = self.__generate_pkt(cmd)
            self.__send_all(client_pkt)
            server_pkt = self.__receive_all()
            self.__handle_pkt(server_pkt)

    def __select_user(self):
        while True:
            args = self.__get_args("Pick a user type, select '1' for TA, '2' for Student:")
            if args[0] == '1':
                return 1
            elif args[0] == '2':
                return 2
            else:
                print "%s: Invalid input" % (self.TAG)

    def __read_st_cmd(self):
        valid = False
        op = UNKNOWN_OP
        param = ""
        while not valid:
            args = self.__get_args("Enter SEARCH <Name> <ID> to query your grade('QUIT' to exit):")
            if len(args) < 1 or len(args) > 3:
                print "%s: Incorrect number of arguments" % (self.TAG)
            elif args[0] == "SEARCH":
                op = SEARCH_OP
            elif args[0] == "QUIT":
                op = QUIT_OP
                self.__is_running = False
                return None
            else:
                print "%s: <" % (self.TAG), args[0], "> is not a valid CMD"
                continue

            if len(args) == 1:
                args = self.__get_args("Enter Student's <Name> <ID>:")
                if len(args) != 2:
                    print "%s: Incorrect number of arguments" % (self.TAG)
                else:
                    param += args[0] + DELIM + args[1]
                    valid = True
            elif len(args) == 2:
                param += args[1] + DELIM
                args = self.__get_args("Enter Student's <ID>:")
                if len(args) != 1:
                    print "%s: Incorrect number of arguments" % (self.TAG)
                else:
                    param += args[0]
                    valid = True
            else:
                param = args[1] + DELIM + args[2]
                valid = True

        return (op, param)

    def __read_ta_cmd(self):
        valid = False
        op = UNKNOWN_OP
        param = ""
        while not valid:
            args = self.__get_args("Enter your CMD ('QUIT' to exit or 'HELP' to see usage):")
            if len(args) < 1 or len(args) > 4:
                print "%s: Incorrect number of arguments, type <HELP> to see usage" % (self.TAG)

            elif args[0] == "LIST":
                op = LIST_OP
                break
            elif args[0] == "ADD":
                op = ADD_OP
            elif args[0] == "CHANGE":
                op = CHANGE_OP
            elif args[0] == "QUIT":
                op = QUIT_OP
                self.__is_running = False
                return None
            elif args[0] == "HELP":
                hint = "1) LIST\n"
                hint += "2) ADD <NAME> <ID> <GRADE>\n"
                hint += "3) CHANGE <NAME> <ID> <GRADE>\n"
                hint += "4) HELP\n"
                hint += "5) QUIT"
                print hint
                continue
            else:
                print "%s: <" % (self.TAG), args[0], "> is not a valid CMD, type <HELP> to see usage"
                continue

            # Get parameters
            if len(args) == 1:
                args = self.__get_args("Enter Student's <Name> <ID> <Grade>:")
                if len(args) != 3:
                    print "%s: Incorrect number of arguments" % (self.TAG)
                else:
                    param += args[0] + DELIM + args[1] + DELIM + args[2]
                    valid = True
            elif len(args) == 2:
                param += args[1] + DELIM
                args = self.__get_args("Enter Student's <ID> <Grade>:")
                if len(args) != 2:
                    print "%s: Incorrect number of arguments" % (self.TAG)
                else:
                    param += args[0] + DELIM + args[1]
                    valid = True
            elif len(args) == 3:
                param += args[1] + DELIM + args[2] + DELIM
                args = self.__get_args("Enter Student's <Grade>:")
                if len(args) != 1:
                    print "%s: Incorrect number of arguments" % (self.TAG)
                else:
                    param += args[0]
                    valid = True
            elif len(args) == 4:
                param += args[1] + DELIM + args[2] + DELIM + args[3]
                valid = True

        return (op,param)

    def __get_args(self, prompt):
        args = raw_input(prompt).split()
        return args

    def __generate_pkt(self, cmd):
        if len(cmd) != 2:
            print "%s: Invalid CMD Format" % (self.TAG)
        return pack("!hB%ds" % (len(cmd[1])), len(cmd[1]), cmd[0], cmd[1])

    def __send_all(self, pkt):
        self.client.sendall(pkt)
        print "%s: Request sent (%d bytes)." % (self.TAG, len(pkt))

    def __receive_all(self):
        buffer = ""
        try:
            # read incoming pkt total length, a short type
            header = self.client.recv(3)
            length, status = unpack("!hB", header)
            print "%s: Incoming packet: %d bytes, status code: %s" % (self.TAG, length, status)
            while len(buffer) < length:
                data = self.client.recv(self.RECV_BUFFER_SIZE)
                if data == "":
                    print "%s: No more data coming, lost connection to server" % (self.TAG)
                    break
                else:
                    buffer += data
        except socket.error as e:
            print "%s: recv failure:%s" % (self.TAG, e.strerror)

        return (status, buffer)

    def __handle_pkt(self, pkt):
        if (pkt[0] == SUCCESS):
            print pkt[1]
            if (self.user == self.STUDENT):
                self.__is_running = False
        else:
            print "[FAILED]: " + pkt[1]


if __name__ == '__main__':
    host = socket.gethostname()
    port = 8080

    with Client(host, port) as client:
        client.run()
