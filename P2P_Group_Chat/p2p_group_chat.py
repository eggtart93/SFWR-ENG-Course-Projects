#!/usr/bin/python

import sys
import socket
import threading
import time
import Queue
import select
import struct
import os
from struct import *

# ---- Global Constants ----
DEBUG_MODE = False
TIMEOUT = 3
BUFFER_SIZE = 1024
MCAST_DEFAULT_IP = "239.17.0.0"
DEFAULT_SEND_PORT = 50002
DEFAULT_RECV_PORT = 50001
DEFAULT_FILE_RECV = 8888
MCAST_TTL = 3
MAX_ATTEMPTS = 3
BUF_SIZE = 4096
# ---- Global Constants ----

# ---- Application Protocols ----
MSG_DISCOVER = "DC"
MSG_TEXT = "TX"
MSG_NOTIFY = "NT"
MSG_JOIN_REQ = "JQ"
MSG_JOIN_ACCEPTED = "JA"
MSG_SYNC_GRP = "S1"
MSG_SYNC_ME = "S2"
MSG_RECV_FILE = "RF"
MSG_ACK = "AK"

# <type>:<src>:<content>
# MSG_DISCOVER:fromGroup:userid:newGroupName
# MSG_NOTIFY:fromGroup:msg
# MSG_TEXT:fromGroup:userid:msg
# MSG_JOIN_REQ:userid:newGroupName
# MSG_JOIN_ACCEPTED:userid:newGroupName:newGroupAddr
# MSG_SYNC_GRP:fromgroup:fromuser
# MSG_SYNC_ME:fromgroup:userid
# MSG_RECV_FILE:togroup:filename
# ---- Application Protocols ----

# ---- Data Model Classes ----
class MsgType:
    ErrMsg, SysMsg, NetMsg, Debug = range(4)

class User(object):
    def __init__(self, userID, userIP):
        self.id = userID
        self.ip = userIP

    def __str__(self):
        return "<%s,%s>" % (self.id, self.ip)

class Group(object):
    def __init__(self, name, owner, ip=None):
        self.name = name
        self.owner = owner # User Obj
        if ip:
            self.ip = ip
        else:
            self.ip = int2ip(ip2int(MCAST_DEFAULT_IP) + id(self)%256)
        self.members = dict()
        console(msg=str(self) + " created.", type=MsgType.Debug)

    def __str__(self):
        info = "<Name:%s, Owner:%s, IP:%s, NumOfMembers:%d>" % (self.name,self.owner.id,self.ip,len(self.members))
        info += "\n" + str([str(member) for member in self.members.values()])
        #info = "<Name:%s, Owner:%s, IP:%s, Members:%s>" % (self.name,self.owner.id,self.ip, str(self.members))
        return info

    def add_member(self, user):
        if self.members.has_key(user.id) or len(user.id) == 0:
            return False
        self.members[user.id] = user

    def has_member(self, userID):
        return self.members.has_key(userID)

    def remove_member(self, userID):
        return self.members.pop(userID, None)

    def list_memberip(self):
        return [user.ip for user in self.members.values()]
# ---- Data Model Classes ----
        
# ---- Global Variables ----
discoverReqs = dict()
joinReqs = dict()
groupsOwned = dict()
groupsJoined = dict()
requestQ = Queue.Queue()
sendQ = Queue.Queue()
loginUser = User("","")
discoverReqID = 0
joinReqID = 0
senderSock = None
receiverSock = None
LOCAL_IP = socket.gethostbyname(socket.gethostname())
# To ensure each packet has unique seq id, we initialize it based on each user's IP
SeqID = ip2int(LOCAL_IP) % 256
# ---- Global Variables ----

print LOCAL_IP

# ---- Helper Methods ----
ip2int = lambda ipstr: struct.unpack('!I', socket.inet_aton(ipstr))[0]
int2ip = lambda n: socket.inet_ntoa(struct.pack('!I', n))

def console(msg, src=None, type=MsgType.SysMsg):
    prefix = ""
    stream = sys.stdout

    if type == MsgType.ErrMsg:
        prefix = "[ERROR]"
        stream = sys.stderr
    elif type == MsgType.SysMsg:
        prefix = "[SYSTEM]"
    elif type == MsgType.NetMsg:
        prefix = "[FROM]"
    elif type == MsgType.Debug:
        if DEBUG_MODE:
            prefix = "\n[Debug]"
        else:
            return
    else:
        print >>sys.stderr, "Unknown Message Type: %s" % type
        return
    if src:
        prefix += "[%s]" % (src)
    msg = prefix + " " + msg
    print >> stream, msg

def create_mcast_socket(mcast_ip, local_ip, port):
    # create an UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # allow reuse same addressess on one machine
    #sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # set multicast interface to local_ip
    sock.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_LOOP, 0)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(local_ip))
    # set the time-to-live for multicast packet to 2
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, MCAST_TTL)
    # subscribe to the multicast group
    mreq = socket.inet_aton(mcast_ip) + socket.inet_aton(local_ip)
    #mreq = struct.pack('4sL', mcast_ip, socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    # bind the socket to an local interface
    try:
        sock.bind((local_ip, port))
        return sock
    except socket.error, msg:
        #console(type=MsgType.ErrMsg, msg="Bind socket failed: " + str(msg[0]) + ", " + msg[1])
        return None
# ---- Helper Methods ----
        
def send_nonblocking(sock, message, address):
    global SeqID

    SeqID = (SeqID + 1) % 256
    #print "SEQ_ID = ", SeqID
    pkt = struct.pack("!B%ds" % (len(message)), SeqID, message)
    attempts = 0
    nextSend = time.time() + TIMEOUT
    sock.sendto(pkt, address)
    while attempts < MAX_ATTEMPTS:
        r,w,e = select.select([sock], [], [], TIMEOUT)
        if len(r) > 0:
            for s in r:
                response, addr = s.recvfrom(BUFFER_SIZE)
                ack, seq = struct.unpack("!%dsB" % (len(MSG_ACK)), response)
                if seq == SeqID and ack == MSG_ACK:
                    return True
        if time.time() > nextSend:
            sock.sendto(pkt, address)
            nextSend = nextSend + TIMEOUT
            attempts += 1
            console(msg="No response, attempts %d/%d ..." % (attempts, MAX_ATTEMPTS))
    return False

def recv_nonblocking(sock):
    r, w, e = select.select([sock], [], [], TIMEOUT)
    for s in r:
        pkt, addr = s.recvfrom(BUFFER_SIZE)
        header, data = struct.unpack("!B%ds" % (len(pkt)-1), pkt)
        #print "recv_nonblocking:", header, data
        if data:
            ack = struct.pack("!%dsB" % (len(MSG_ACK)), MSG_ACK, header)
            s.sendto(ack, addr)
            return (data, addr)
    return ()

def send_pack (sock, rc, data):
    packet = pack('!hB%ds' % (len(data)), len(data), rc, data)
    sock.sendall(packet)
    
def receive_pack (sock):
    data = ''
    try:
        header = sock.recv(3)
        if not header:
            print 'header receiver error'
            return (RECE_ERROR,None)
        length, rc = unpack('!hB',header)
        buf_size = BUF_SIZE
        if length <= buf_size:
            buf_size = length
        while len(data) < length:
            reply = sock.recv(buf_size)
            if not reply:
                print 'data recv error'
                return (RECE_ERROR, None)
            data += reply
    except socket.error as e:
        print 'Fail to recv data', e.strerror
        return (RECE_ERROR, None)
    return (rc, data)

def app_msg_listener(receiver):
    global discoverReqID
    global joinReqID

    while True:
        pkt = recv_nonblocking(receiver)
        if len(pkt) > 0:
            console(msg="app_msg_listener:" + str(pkt), type=MsgType.Debug)

            data, addr = pkt
            data = data.split(":")
            addr = addr[0]
            if data[0] == MSG_NOTIFY:
                #nt:fromgroup:userid:msg
                app_handle_sync_me(data[1],User(data[2], addr))
                console(data[2] + data[3], data[1], MsgType.NetMsg)

            elif data[0] == MSG_SYNC_ME:
                # S2:fromgroup:userid
                app_handle_sync_me(data[1], User(data[2], addr))

            elif data[0] == MSG_SYNC_GRP:
                # S1:fromgroup:fromuser
                app_handle_sync_grp(data[1], User(data[2], addr))

            elif data[0] == MSG_DISCOVER:
                discoverReqID += 1
                info = "%s created new group %s, REQ_ID=%d" % (data[2],data[3],discoverReqID)
                console(info, data[1], MsgType.NetMsg)
                # DC:fromGroup:userid:newGroupName
                # reqType + reqId + new group name + creator address
                discoverReq = (MSG_DISCOVER, discoverReqID, data[3], addr)
                requestQ.put(discoverReq)

            elif data[0] == MSG_JOIN_REQ:
                joinReqID += 1
                info = "%s wish to join %s, REQ_ID=%d" % (data[1],data[2],joinReqID)
                console(info, data[1], MsgType.NetMsg)
                # joinreq:userid:newGroupName
                # reqType + reqId + userID + group name + creator address
                joinReq = (MSG_JOIN_REQ, joinReqID, data[1], data[2], addr)
                requestQ.put(joinReq)

            elif data[0] == MSG_JOIN_ACCEPTED:
                # joinaccept:userid:newGroupName:newGroupAddr
                console(data[1] + " accepted your request of joining " + data[2])
                app_join_group(Group(name=data[2], owner=User(data[1],addr), ip=data[3]))

            elif data[0] == MSG_TEXT:
                console(msg=str(data), type=MsgType.Debug)
                console("%s says: %s" % (data[2], data[3]), data[1], MsgType.NetMsg)

            elif data[0] == MSG_RECV_FILE:
                threading.Thread(target=recv_file, args=(data[2])).start()

            else:
                console(msg="Unknown Message: " + str(data), type=MsgType.ErrMsg)

def app_msg_sender(sender):
    while True:
        item = sendQ.get()
        send_nonblocking(sender, item[0], item[1])
        console(msg="app_msg_sender:" + str(item), type=MsgType.Debug)
        sendQ.task_done()

def app_send_sync_grp(groupName):
    # sync1:groupname
    if groupsOwned.has_key(groupName):
        groupIP = groupsOwned[groupName].ip
    elif groupsJoined.has_key(groupName):
        groupIP = groupsJoined[groupName].ip
    else:
        console(msg="Cannot recognize group " + groupName, type=MsgType.ErrMsg)
        return
    packet = "%s:%s:%s" % (MSG_SYNC_GRP, groupName, loginUser.id)
    item = (packet, (groupIP, DEFAULT_RECV_PORT))
    sendQ.put(item)

def app_handle_sync_me(groupName, user):
    console(msg="app_handle_sync_me: from " + str(user), type=MsgType.Debug)

    if groupsOwned.has_key(groupName):
        groupsOwned[groupName].add_member(user)
    elif groupsJoined.has_key(groupName):
        groupsJoined[groupName].add_member(user)
    else:
        console(msg="Cannot recognize group " + groupName, type=MsgType.ErrMsg)

def app_handle_sync_grp(groupName, user):
    console(msg="app_handle_sync_grp: to " + groupName, type=MsgType.Debug)

    groupIP = ""
    if groupsOwned.has_key(groupName):
        groupIP = groupsOwned[groupName].ip
        groupsOwned[groupName].add_member(user)
    elif groupsJoined.has_key(groupName):
        groupIP = groupsJoined[groupName].ip
        groupsJoined[groupName].add_member(user)
    else:
        return
    # syncme:fromgroup:userid
    packet = "%s:%s:%s" % (MSG_SYNC_ME, groupName, loginUser.id)
    sendQ.put((packet, (groupIP, DEFAULT_RECV_PORT)))

def app_create_group(groupName):
    global senderSock
    global receiverSock

    # create a group
    newGroup = Group(groupName, loginUser)
    newGroup.add_member(loginUser)
    # add membership to both sockets
    mreq = socket.inet_aton(newGroup.ip) + socket.inet_aton(LOCAL_IP)
    senderSock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    receiverSock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    # add to groups dict
    groupsOwned[groupName] = newGroup

def app_join_group(group):
    global senderSock
    global receiverSock

    if  groupsJoined.has_key(group.name) or groupsOwned.has_key(group.name):
        console(msg="Already in " + group.name, type=MsgType.ErrMsg)
        return
    else:
        #mreq = struct.pack('4sL', groupIP, socket.INADDR_ANY)
        mreq = socket.inet_aton(group.ip) + socket.inet_aton(LOCAL_IP)
        senderSock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        receiverSock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        group.add_member(group.owner)
        group.add_member(loginUser)
        groupsJoined[group.name] = group

        packet = "%s:%s:%s:%s" % (MSG_NOTIFY, group.name, loginUser.id, " has joined.")
        sendQ.put((packet, (group.ip, DEFAULT_RECV_PORT)))

def app_send_text(groupName, text):
    addr = None
    if groupsJoined.has_key(groupName):
        addr = (groupsJoined[groupName].ip, DEFAULT_RECV_PORT)
    elif groupsOwned.has_key(groupName):
        addr = (groupsOwned[groupName].ip, DEFAULT_RECV_PORT)
    else:
        console(msg="Unknown group " + groupName, type=MsgType.ErrMsg)
        return

    packet = "%s:%s:%s:%s" % (MSG_TEXT, groupName, loginUser.id, text)
    item = (packet, addr)
    sendQ.put(item)

def app_send_file(groupName, filename):
    if groupsJoined.has_key(groupName):
        ip_list = groupsJoined[groupName].list_memberip()
        groupIP = groupsJoined[groupName].ip
    elif groupsOwned.has_key(groupName):
        ip_list = groupsOwned[groupName].list_memberip()
        groupIP = groupsOwned[groupName].ip
    else:
        console(msg="Unknown group " + groupName, type=MsgType.ErrMsg)
        return

    if os.path.isfile(filename):
        packet = "%s:%s:%s" % (MSG_RECV_FILE, groupName, filename)
        filesize = os.path.getsize(filename)
        item = (packet, (groupIP, DEFAULT_RECV_PORT))
        sendQ.put(item)
        sock_list = []
        for ip in ip_list:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock_list.append(sock)
            try:
                sock.connect((ip,DEFAULT_FILE_RECV))
            except socket.error, msg:
                print 'connect failure: ', msg

        try:
            with open(filename, 'rb') as f:
                data = filesize
                rc = 0
                while data:
                    for sock in sock_list:
                        send_pack(sock,rc,str(data))
                    sys.stdout.write('\r%d%% sent' % \
                            int((f.tell()/float(filesize))*100))
                    sys.stdout.flush()
                    data = f.read(BUF_SIZE)
        except IOError as e:
            print 'file I/O error', e.strerror
            rc = 1
            send_pack(sock,rc,e.strerror)
        else:
            print '\r send complete'

    else:
        console(msg="Unknown file " + fileName, type = MsgType.ErrMsg)
    
    return

def recv_file(filename):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(LOCAL_IP, DEFAULT_FILE_RECV)
    s.listen(5)
    client, addr = s.accept()
    rc, data = receive_pack(sock)
    filesize = int(data)
    n_bytes = 0
    try:
        with open(filename, 'wb') as f:
            while n_bytes < filesize:
                rc, data = receive_pack(sock)
                f.write(data)
                n_bytes = f.tell()
                sys.stdout.write('\r%d%% copied' % \
                        int((n_bytes/float(filesize))*100))
                sys.stdout.flush()
    except IOError as e:
        print 'file I/O error', e.strerror
    else:
        print '\rreceiving complete'

    return

def app_list_req():
    # reqType + reqId + new group name + creator address
    # reqType + reqId + userID + group name + creator address
    app_read_requestQ()

    info = "\n=====Discover Requests=====\nReqID\tGroupName\n"
    for reqID, req in discoverReqs.iteritems():
        info += "%d\t%s\n" % (reqID, req[2])

    info += "\n=====Join Requests=====\nReqID\tUserID\tGroupName\n"
    for reqID, req in joinReqs.iteritems():
        info += "%d\t%s\t%s\n" % (reqID, req[2], req[3])

    console(msg=info)

def app_read_requestQ():
    while not requestQ.empty():
        try:
            req = requestQ.get_nowait()
            if req[0] == MSG_DISCOVER:
                requestQ.task_done()
                discoverReqs[req[1]] = req
            elif req[0] == MSG_JOIN_REQ:
                requestQ.task_done()
                joinReqs[req[1]] = req
            else:
                console(msg="Invalid request ERROR", type=MsgType.ErrMsg)
                return
        except Queue.Empty:
            break

def app_accept_join_req(reqID):
    app_read_requestQ()

    groupName = ""
    fromAddr = ""
    if joinReqs.has_key(reqID):
        groupName = joinReqs[reqID][3]
        fromAddr = joinReqs[reqID][4]
    else:
        console(msg="Request ID not exist", type=MsgType.ErrMsg)
        return

    if groupsOwned.has_key(groupName):
        # joinaccept:userid:newGroupName:newGroupAddr
        packet = "%s:%s:%s:%s" % (MSG_JOIN_ACCEPTED, loginUser.id, groupName, groupsOwned[groupName].ip)
        sendQ.put((packet, (fromAddr, DEFAULT_RECV_PORT)))
    else:
        console(msg="Group %s not exist" % (groupName), type=MsgType.ErrMsg)

def app_send_join_req(reqID):
    app_read_requestQ()
    if discoverReqs.has_key(reqID):
        # discover:fromGroup:userid:newGroupName
        # joinreq:userid:newGroupName
        # reqType + reqId + new group name + creator address
        req = discoverReqs[reqID]
        packet = "%s:%s:%s" % (MSG_JOIN_REQ, loginUser.id, req[2])
        sendQ.put((packet, (req[3], DEFAULT_RECV_PORT)))
    else:
        console(msg="Invalid Req ID", type=MsgType.ErrMsg)

def app_list_group():
    info = "\ngroupsOwned:\n"
    for group in groupsOwned.values():
        info += str(group) + "\n"
    info += "\ngroupsJoined:\n"
    for group in groupsJoined.values():
        info += str(group) + "\n"
    console(info)

def app_init():
    global senderSock
    global receiverSock
    senderSock = create_mcast_socket(MCAST_DEFAULT_IP, LOCAL_IP, DEFAULT_SEND_PORT)
    receiverSock = create_mcast_socket(MCAST_DEFAULT_IP, LOCAL_IP, DEFAULT_RECV_PORT)

    groupsJoined["default"] = Group("default", User("Public",""), MCAST_DEFAULT_IP)

    if senderSock is None or receiverSock is None:
        console(msg="Failed to create socket", type=MsgType.ErrMsg)
        sys.exit()
    else:
        threading.Thread(target=app_msg_listener, args=(receiverSock,)).start()
        threading.Thread(target=app_msg_sender, args=(senderSock,)).start()

def app_main():
    userID = raw_input("Enter Your Group Chat User ID:")
    loginUser.id = userID
    loginUser.ip = LOCAL_IP

    groupsJoined["default"].add_member(loginUser)

    notifyPkt = "%s:%s:%s:%s" % (MSG_NOTIFY, "default", loginUser.id, " comes online.")
    sendQ.put((notifyPkt, (groupsJoined["default"].ip, DEFAULT_RECV_PORT)))
    app_send_sync_grp("default")

    time.sleep(2)

    while True:
        cmd = raw_input("Enter CMD ('HELP' to see usage)>>").strip()

        if cmd == "EXIT":
            break
        elif cmd == "HELP":
            info = "CMD List:\n"
            info += "1) DISCOVER:<NEW GROUP NAME>\n"
            info += "2) @<GROUP NAME>:<MESSAGE>\n"
            info += "3) #<GROUP NAME>:<FILE>\n"
            info += "4) LIST:<REQ|GRP>\n"
            info += "5) SYNC:<GROUP NAME>\n"
            info += "6) ACCEPT:<JOIN REQ ID>\n"
            info += "7) JOIN:<GROUP NAME>\n"
            info += "8) HELP\n"
            info += "9) EXIT\n"
            console(info)

        elif ":" in cmd:
            cmd, arg = cmd.split(":")

            if len(arg) < 0:
                console(msg="No argument", type=MsgType.ErrMsg)
                pass

            if cmd == "DISCOVER":
                # msgType fromGroup fromUser newGroupName
                packet = "%s:%s:%s:%s" % (MSG_DISCOVER, "default", loginUser.id, arg)
                item = (packet, (groupsJoined["default"].ip, DEFAULT_RECV_PORT))
                sendQ.put(item)
                app_create_group(arg)

            elif cmd[0] == "@":
                app_send_text(cmd[1:], arg)

            elif cmd[0] == "#":
                threading.Thread(target=app_send_file, args=(cmd[1:], arg)).start()

            elif cmd == "LIST":
                if arg == "REQ":
                    app_list_req()
                elif arg == "GRP":
                    app_list_group()
                else:
                    console(msg="LIST: Invalid argument "+ arg, type=MsgType.ErrMsg)

            elif cmd == "SYNC":
                app_send_sync_grp(arg)

            elif cmd == "ACCEPT":
                app_accept_join_req(int(arg))

            elif cmd == "JOIN":
                app_send_join_req(int(arg))

            else:
                console(msg="Invalid INPUT %s, %s" % (cmd, arg), type=MsgType.ErrMsg)
        elif len(cmd) == 0:
            pass
        else:
            console(msg="Invalid INPUT %s" % (cmd), type=MsgType.ErrMsg)


if __name__ == '__main__':
    app_init()
    app_main()


