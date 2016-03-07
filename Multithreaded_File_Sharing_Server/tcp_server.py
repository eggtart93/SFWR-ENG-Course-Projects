#!/usr/bin/python


# Computer Enginnering: Advanced Network Communications
# 
# <Topic: Multithreaded File Sharing TCP Server/Client>
#
# Author: Jin Kuan Zhou <zhoujk93@hotmail.com>
# Date: 2016-02-18


import os
import socket
import threading
import logging
import math
from struct import *

HOST = ''
PORT = 8080
MAX_PENDING = 0
BUFFER_SIZE = 2048
ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
SHARED_DIR_PATH = os.path.join(ROOT_DIR, 'shared')

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


logging.basicConfig(level=logging.INFO,
        format='[%(levelname)5s](%(threadName)-s) %(message)s',
        )

def get_dir_struct(dirname, sort_key="Name", prefix="", reverse=False):
    """ Return list of file paths in directory sorted by file size """

    # Get list of files
    files = []
    updir = prefix
    for entry_name in os.listdir(dirname):
        entry_path = os.path.join(dirname, entry_name)
        if os.path.isfile(entry_path):
            name, ext = os.path.splitext(entry_name)
            if updir: name = updir + '\\\\' + name
            entry = {'Name':name, 'Type':ext, 'Size':math.ceil(os.path.getsize(entry_path) / 1024.0)}
            files.append(entry)
        else:
            if updir: prefix = os.path.join(updir, os.path.basename(entry_path))
            else: prefix = os.path.basename(entry_path)
            files += get_dir_struct(entry_path, sort_key, prefix, reverse)

    files.sort(key=lambda entry: entry[sort_key])
    return files


def get_dir_struct_str(dirname, sort_key="Name", reverse=False):
    """ Return directory structure list in string format """

    table = "%s:\n" % (os.path.basename(dirname))
    row_format = "{:<26}" * (3)
    table += row_format.format("Name", "Type", "Size (KB)") + '\n\n'
    for entry in get_dir_struct(dirname, sort_key, reverse):
        table += row_format.format(entry['Name'], entry['Type'], str(entry['Size']))
        table += '\n'
    return table


def send_pkt(client, pkt_type, data=''):
    pkt = pack("!hB%ds" % (len(data)), len(data), pkt_type, data)
    client.sendall(pkt)


def recv_pkt(client):
    buf = ""
    try:
        header = client.recv(3)
        length, pkt_type = unpack("!hB", header)
        buf_size = length if length < BUFFER_SIZE else BUFFER_SIZE
        logging.debug("Incoming packet: %d bytes, type: %s" % (length, pkt_type))
        while len(buf) < length:
            data = client.recv(buf_size)
            if not data:
                logging.error("No incoming data, connection is broken")
                break
            else:
                buf += data
    except Exception as e:
        logging.error("Recv failed: ", e.args)
        return None
    return (pkt_type, buf)


def send_file(client, filename):
    path = os.path.join(SHARED_DIR_PATH, filename)
    if os.path.isfile(path):
        length = os.path.getsize(path)
        send_pkt(client, ON_READ_READY, str(length))

        try:
            with open(path, 'rb') as f:
                data = f.read(BUFFER_SIZE)
                while data:
                    send_pkt(client, ON_READ, data)
                    data = f.read(BUFFER_SIZE)
            logging.info("File %s transferred to client successfully." % (filename))
        except Exception as e:
            logging.error("Send file failed: ", e.args)
            send_pkt(client, ON_READ_ERROR, "Error occurs")
        return

    else:
        msg = "Error: %s not exist" % (filename)
        logging.error(msg)
        send_pkt(client, ON_READ_ERROR, msg)
    return


def recv_file(client, file_info):
    try:
        filename, file_size = file_info.split(':')
        path = os.path.join(SHARED_DIR_PATH, filename)
        file_size = int(file_size)
    except Exception as e:
        logging .error("Receive Failed: ", e.args)
        msg = "Invalid file info: filename = %s, file_size = %s" % (filename, file_size)
        logging.error(msg)
        send_pkt(client, ON_WRITE_ERROR, msg)
        return False

    # Send Ack
    send_pkt(client, ON_WRITE_READY)
    tmp = path + '.' + "%s.%d" % (client.getpeername())
    nbytes = 0
    try:
        with open(tmp, 'wb') as f:
            while nbytes < file_size:
                status, data = recv_pkt(client)
                if status == ON_WRITE:
                    f.write(data)
                    nbytes = f.tell()
                else:
                    logging.error("Write %s Failed: packet corrupted" % (filename))
                    send_pkt(client, ON_WRITE_ERROR, "Write %s Failed, Packet corrupted" % (filename))
                    return False
    except IOError as e:
        logging.error("IOError: " + e.strerror)
        send_pkt(client, ON_WRITE_ERROR, "Write %s Failed, IOError" % (filename))
        return False
    else:
        try:
            # Delete old file if exist
            os.remove(path)
        except OSError:
            pass

        try:
            os.rename(tmp, path)
        except OSError:
            logging.error("Cannot rename file, Permission required")
            return False
        else:
            logging.info("File %s transferred from client successfully." % (filename))
            return True


def handle_tcp_client(client):

    is_running = True
    while is_running:

        pkt = recv_pkt(client)
        logging.debug("Recv: " + str(pkt))

        if pkt is None:
            logging.error("Connection error occurs")
            break;

        response = ""
        req, args = pkt
        if req == CMD_BYE:
            break;

        elif req == CMD_LIST_ALL:
            logging.info("LIST-ALL Request")
            response = get_dir_struct_str(SHARED_DIR_PATH)
            send_pkt(client, MSG_REPLY, response)

        elif req == CMD_READ:
            logging.info("READ Request")
            send_file(client, args)

        elif req == CMD_WRITE:
            logging.info("WRITE Request")
            is_running = recv_file(client, args)

        else:
            logging.error("Invalid Command %s" % (req))


    logging.info("Closing client connection ...")
    client.close()
    return

if __name__ == '__main__':

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server.bind((HOST, PORT))
    except socket.error as e:
        logging.error("Bind failed: " + e.strerror)
        sys.exit()

    server.listen(MAX_PENDING)
    logging.info("Now listening at Port %d" % (PORT))

    while True:
        logging.info("Waiting incoming connection ...")
        client, addr = server.accept()
        logging.info("Client %s:%d is connected" % addr)
        threading.Thread(name="Handle_%s:%d" % addr, target=handle_tcp_client, args=(client,)).start()

    server.close()
    logging.error("Should never reach here, Something is wrong")
