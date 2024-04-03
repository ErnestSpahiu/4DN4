#!/usr/bin/env python3

########################################################################

import socket
import argparse
import sys
import errno
import threading
import os
import json



########################################################################
# recv_bytes frontend to recv
########################################################################


CMD_FIELD_LEN            = 1 # 1 byte commands sent from the client.
CHATNAME_SIZE_FIELD_LEN  = 1 # 1 byte Chat name size field.
ADDR_SIZE_FIELD_LEN  = 1 # 1 byte Chat name size field.
PORT_SIZE_FIELD_LEN  = 1 # 1 byte Chat name size field.

MSG_ENCODING = "utf-8"
CMD = {"GETDIR" : 1, "MAKEROOM" : 2, "DELETEROOM": 3}
SOCKET_TIMEOUT = 4

    
########################################################################
# Chat room Discovery Server
# 
########################################################################


class Server:
    HOSTNAME = "127.0.0.1"
    CHAT_ROOM_DIRECTORY_PORT = 50000

    MSG_ENCODING = "utf-8"

    RECV_SIZE = 1024
    BACKLOG = 10

    chatrooms = [{'name': 'Room_0', 'addr_port': ['239.0.0.1', '1000']}]

    def __init__(self):
        self.get_socket()
        self.receive_forever()

    def get_socket(self):
        try:
            # Create the TCP server listen socket in the usual way.
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind(
                (Server.HOSTNAME, Server.CHAT_ROOM_DIRECTORY_PORT))
            self.socket.listen(Server.BACKLOG)
            print("Chat Room Directory Server listening on port <port number> {} ...".format(
                Server.CHAT_ROOM_DIRECTORY_PORT))
        except Exception as msg:
            print(msg)
            exit()

    def receive_forever(self):
        try:
            while True:
                client = self.socket.accept()
                connection, address_port = client
                threading.Thread(target=self.connection_handler,
                                 args=(client,)).start()
        except Exception as msg:
            print(msg)
        except KeyboardInterrupt:
            print()
        finally:
            print("Closing {} client connection ... ".format(address_port))     
            connection.close()
            self.socket.close()
            sys.exit(1)

    def connection_handler(self, client):
        connection, address_port = client
        connection.setblocking(True)
        while True:
            recvd_bytes = connection.recv(1)
                        
            if len(recvd_bytes) == 0:
                print("Closing {} client connection ... ".format(address_port))
                connection.close()
                # Break will exit the connection_handler and cause the
                # thread to finish.
                break

            cmd = int.from_bytes(recvd_bytes, byteorder='big')
            if cmd == CMD["GETDIR"]:
                print("Server: Recieved GETDIR CMD")
                self.getDir(connection)
            if cmd == CMD["MAKEROOM"]:
                print("Server: Recieved MAKEROOM CMD")
                error = self.makeRoom(connection)
            if cmd == CMD["DELETEROOM"]:
                print("Server: Recieved DELETEROOM CMD")
                error = self.deleteRoom(connection)

        
    def getDir(self, connection):
        data_string = json.dumps(self.chatrooms)
        connection.send(data_string.encode(MSG_ENCODING))
    
    def makeRoom(self, connection):
        # recieve more bytes containing chatroom name and multicast ip and port
        chatroom_name_byte_len = int.from_bytes(connection.recv(1), byteorder='big')
        chatroom_name = connection.recv(chatroom_name_byte_len).decode(Server.MSG_ENCODING)

        multicast_ip = socket.inet_ntoa(connection.recv(4))
        multicast_port = connection.recv(Server.RECV_SIZE).decode(Server.MSG_ENCODING)

        for room in self.chatrooms:
            if list(room['addr_port']) == [multicast_ip, multicast_port]:
                resp = 0
                break
        else:
            self.chatrooms.append({'name': chatroom_name, 'addr_port': (multicast_ip, multicast_port)})
            print("Added Chatroom to Directory: ", self.chatrooms[-1])

    def deleteRoom(self, connection):
        chatroom_del_byte_len = int.from_bytes(connection.recv(1), byteorder='big')
        chatroom_del = connection.recv(chatroom_del_byte_len).decode(Server.MSG_ENCODING)
        print("Delete: " + chatroom_del)
        for room in self.chatrooms:
            if room['name'] == chatroom_del:
                #print("Time to delete chatroom: ", room)
                self.chatrooms.remove(room)
        

########################################################################
# Service Discovery Client
#
# In this version, the client broadcasts service discovery packets and
# receives server responses. After a broadcast, the client continues
# to receive responses until a socket timeout occurs, indicating that
# no more responses are available. This scan process is repeated a
# fixed number of times. The discovered services are then output.
#
########################################################################

class Client:

    RECV_SIZE = 1024
    MSG_ENCODING = "utf-8"

    def __init__(self):
        self.get_socket()
        self.connected = False
        self.prompt_user_forever()
        self.name = ""

    def get_socket(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except Exception as msg:
            print(msg)
            exit()

    def prompt_user_forever(self):

        try:
            while True:
                # We are connected to the FS. Prompt the user for what to
                # do.
                client_prompt_input = input(
                    "Please enter one of the following commands (connect, bye, name <chat name>, chat <chat room name>: ") if not self.connected else input(
                    "Connected to CRDS please enter one of the following commands (getdir, makeroom <chat room name> <address> <port>, deleteroom <chat room name>, connect, bye, name <chat name>, chat <chat room name>: ")
                if client_prompt_input:
                    # If the user enters something, process it.
                    try:
                        # Parse the input into a command and its
                        # arguments.
                        client_prompt_cmd, *client_prompt_args = client_prompt_input.split()
                    except Exception as msg:
                        print(msg)
                        continue
                    if client_prompt_cmd == 'connect':
                        try:
                            self.connect_to_server()
                        except Exception as msg:
                            print(msg)
                            exit()
                        
                    elif client_prompt_cmd =='bye':
                        # Disconnect from the FS.
                        self.connected = False
                        self.socket.close()
                        break

                    elif client_prompt_cmd =='name':
                        try:
                            if (len(client_prompt_args) == 1):
                                self.changeName(client_prompt_args[0])
                            else:
                                print("No <chat name> passed in")
                        except Exception as msg:
                            print(msg)
                            exit()
                    elif client_prompt_cmd == 'chat':
                        print(len(client_prompt_args))
                        print(f"args: {client_prompt_args}")
                        try:
                            if (len(client_prompt_args) == 1):
                                self.chat(client_prompt_args[0])
                            else:
                                print("No <chat room name> passed in")
                        except Exception as msg:
                            print(msg)
                            exit()

                    elif client_prompt_cmd =='getdir' and self.connected:
                        try:
                            self.getDir()
                            break
                        except Exception as msg:
                            print(msg)
                            exit()

                    elif client_prompt_cmd =='makeroom' and self.connected:
                        try:
                            if (len(client_prompt_args) == 3):
                                self.makeRoom(client_prompt_args[0], client_prompt_args[1], client_prompt_args[2])
                                break
                            elif (len(client_prompt_args) == 2):
                                print("No <port> passed in")
                            elif(len(client_prompt_args) == 1):
                                print("No <address>, <port> passed in")
                            else:
                                print("No arguments passed in")

                        except Exception as msg:
                            print(msg)
                            exit()
                    elif client_prompt_cmd =='deleteroom' and self.connected:
                        try:
                            if (len(client_prompt_args) == 1):
                                self.deleteRoom(client_prompt_args[0])
                            else:
                                print("No <chat room name> passed in")
                        except Exception as msg:
                            print(msg)
                            exit()
                    else:
                        pass

        except (KeyboardInterrupt, EOFError):
            print()
            print("Closing server connection ...")
            # If we get and error or keyboard interrupt, make sure
            # that we close the socket.
            self.socket.close()
            sys.exit(1)

    def connect_to_server(self, hostname=Server.HOSTNAME, port=Server.CHAT_ROOM_DIRECTORY_PORT):
        # Connect to the server using its socket address tuple.
        self.socket.connect((hostname, port))
        print("Connected to \"{}\" on port {}".format(hostname, port))
        self.connected = True

    def changeName(self, name):
        if name == "":
            print("Please enter a name")
            return

        print(f"Setting name to {name}")
        self.name = name

    def chat(self, chat_name):
        # checks
        if self.name == "":
            print("Please enter a name first")
            return
        # try to connect to the chat room

        print(f"Entering chat mode for chat room {chat_name}. Press <ctrl>] to exit chat mode.")
        while True:
            try:
                # Prompt the user for a message to send to the chat room.
                message = input(f"{chat_name} > ")
                if '\x1d' in message:
                    # Exit chat mode if the control sequence is entered.
                    print('Exiting chat mode...')
                    break
                print(message)
                # Send the message to the chat room.
                # self.socket.sendall(message.encode(self.MSG_ENCODING))
                # # Receive messages from the chat room.
                # response = self.socket.recv(self.RECV_SIZE).decode(self.MSG_ENCODING)
                # Output the received messages.
                # print(response)
            except (KeyboardInterrupt):
                print()
                print("Exiting chat mode...")
                break
    
    def getDir(self):
        cmd_filed = CMD["GETDIR"].to_bytes(1, byteorder='big')
        try:
            # Send the request packet to the server.
            self.socket.sendall(cmd_filed)
        except:
            print("No connection.")
            return
        #receive the directory listing from server
        recvd_bytes = self.socket.recv(Client.RECV_SIZE)
        if len(recvd_bytes) == 0:
            print("Closing server connection ... ")
            self.socket.close()
            return
        dir = recvd_bytes.decode(Server.MSG_ENCODING)
        print("Here is the listing of the current chat room directory:", json.loads(dir))
        self.prompt_user_forever()
        
    def makeRoom(self, roomname, address, port):
        cmd_field = CMD["MAKEROOM"].to_bytes(1, byteorder='big')
        name_len_bytes = len(roomname).to_bytes(1, byteorder='big')
        name_bytes = roomname.encode(Server.MSG_ENCODING)

        address_bytes = socket.inet_aton(address)
        port_str_bytes = port.encode(Server.MSG_ENCODING)

        pkt = cmd_field + name_len_bytes + name_bytes + address_bytes + port_str_bytes

        self.socket.send(pkt)
        self.prompt_user_forever()
    
    def deleteRoom(self, roomname):
        cmd_field = CMD["DELETEROOM"].to_bytes(1, byteorder='big')
        del_len_bytes = len(roomname).to_bytes(1, byteorder='big')
        del_bytes = roomname.encode(Server.MSG_ENCODING)
        pkt = cmd_field + del_len_bytes + del_bytes
        self.socket.send(pkt)
        self.prompt_user_forever()


########################################################################
# Fire up a client/server if run directly.
########################################################################

if __name__ == '__main__':
    roles = {'client': Client, 'server': Server}
    parser = argparse.ArgumentParser()

    parser.add_argument('-r', '--role',
                        choices=roles,
                        help='client or server role',
                        required=True, type=str)

    args = parser.parse_args()
    roles[args.role]()


########################################################################
