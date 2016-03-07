#!/usr/bin/python


# Computer Enginnering: Advanced Network Communications
# 
# <Topic: Multithreaded File Sharing TCP Server/Client>
#
# Author: Jin Kuan Zhou <zhoujk93@hotmail.com>
# Date: 2016-02-18


import socket
import sys
import os
import math
from struct import *

REMOTE_HOST = socket.gethostname()
REMOTE_PORT = 8080
BUFFER_SIZE = 2048

# Packet Type
CMD_LIST_ALL = 0xC1
CMD_READ = 0xC2
CMD_WRITE = 0xC3
CMD_BYE = 0xC4
MSG_REPLY = 0xD1

ON_READ_READY = 0x10
ON_READ = 0x11
ON_READ_ERROR = 0x12

ON_WRITE_READY = 0x20
ON_WRITE = 0x21
ON_WRITE_ERROR = 0x22


def send_pkt(client, cmd, args=''):
    pkt = pack("!hB%ds" % (len(args)), len(args), cmd, args)
    client.sendall(pkt)

def recv_pkt(client):
    buf = ""
    try:
        header = client.recv(3)
        length, pkt_type = unpack("!hB", header)
        buf_size = length if length < BUFFER_SIZE else BUFFER_SIZE
        #print "Incoming packet: %d bytes, type: %s" % (length, pkt_type)
        while len(buf) < length:
            data = client.recv(buf_size)
            if not data:
                print "No more data coming, connection is broken"
                break
            else:
                buf += data
    except socket.error as e:
        print "Recv failed: ", e.strerror
        return None
    return (pkt_type, buf)

def update_progress(progress, total):
    percent = int(float(progress) / float(total) * 100)
    sys.stdout.write("\rProgress: %d/%d Bytes (%d%%)" % (progress, total, percent))
    sys.stdout.flush()


def read_file(client, filename):

    remote_path = filename
    filename = os.path.basename(filename)
    # Send Read Request
    send_pkt(client, CMD_READ, remote_path)

    # Get file info
    status, info = recv_pkt(client)
    file_size = 0

    if status == ON_READ_ERROR:
        print "Read Failed: ", info
    elif status == ON_READ_READY:
        file_size = int(info)

        try:
            with open(filename, 'wb') as f:
                print "\nStart receiving file %s (%d KB) ..." % (filename, math.ceil(file_size/1024))
                nbytes = 0
                while nbytes < file_size:
                    status, data = recv_pkt(client)
                    if status == ON_READ:
                        f.write(data)
                        nbytes = f.tell()
                        update_progress(nbytes, file_size)
                    else:
                        print "\n\nRead failed: Data corrupted"
                        return
        except IOError as e:
            print "\n\nRead file failed: ", e.strerror
        else:
            print "\n\nRead completed."


def write_file(client, filename):
    remote_path = filename
    filename = os.path.basename(filename)
    if os.path.isfile(filename):
        file_size = os.path.getsize(filename)
        file_info = "%s:%d" % (remote_path, file_size)

        # Send Wrte Request
        send_pkt(client, CMD_WRITE, file_info)

        # Get Ack from server
        status, info = recv_pkt(client)

        if status == ON_WRITE_ERROR:
            print "Write Failed: ", info
        elif status == ON_WRITE_READY:
            print "\nStart sending file %s (%d KB) ..." % (filename, math.ceil(file_size/1024))
            try:
                with open(filename, 'rb') as f:
                    data = f.read(BUFFER_SIZE)
                    while data:
                        send_pkt(client, ON_WRITE, data)
                        data = f.read(BUFFER_SIZE)
                        update_progress(f.tell(), file_size)
            except IOError as e:
                    print "\n\nWrite Failed: ", e.strerror
                    send_pkt(client, ON_WRITE_ERROR, e.strerror)
            else:
                print "\n\nWrite completed."
    else:
        print "\n\nWrite Failed: %s is not a valid file path" % (filename)

    return


if __name__ == '__main__':

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    is_connected = False
    while True:
        args = raw_input("Enter cmd: ").split()

        if is_connected:
            if args[0] == "CONNECT":
                print "Already connected"
                continue

            elif args[0] == "BYE":
                send_pkt(sock, CMD_BYE)
                break

            elif args[0] == "LIST-ALL":
                send_pkt(sock, CMD_LIST_ALL)
                pkt_type, pkt_msg = recv_pkt(sock)
                print pkt_msg

            elif args[0] == "READ":
                if len(args) < 2:
                    print "Incorrect number of arg, READ <filename>"
                    continue
                read_file(sock, args[1])

            elif args[0] == "WRITE":
                if len(args) < 2:
                    print "Incorrect number of arg, WRITE <filename>"
                    continue
                write_file(sock, args[1])

            else:
                print "Invalid CMD"
        else:
            if args[0] == "CONNECT":
                if len(args) < 3:
                    print "Incorrect number of arg, CONNECT <IP> <PORT>"
                    continue
                try:
                    sock.connect((args[1], int(args[2])))
                except Exception as e:
                    print "Connect failed: ", e.args
                    continue
                else:
                    is_connected = True
                    print "Connected to server"
            else:
                print "Disconnect to server"

    print "Closing connection to server"
    sock.close()
