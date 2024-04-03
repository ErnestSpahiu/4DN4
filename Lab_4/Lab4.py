#!/usr/bin/env python3

########################################################################

import socket
import argparse
import sys, errno
import threading
import os



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


# Call recv to read bytecount_target bytes from the socket. Return a
# status (True or False) and the received butes (in the former case).
def recv_bytes(sock, bytecount_target):
    # Be sure to timeout the socket if we are given the wrong
    # information.
    print(bytecount_target)
    sock.settimeout(SOCKET_TIMEOUT)
    try:
        byte_recv_count = 0 # total received bytes
        recv_bytes = b''    # complete received message
        while byte_recv_count < bytecount_target:
            # Ask the socket for the remaining byte count.
            new_bytes = sock.recv(bytecount_target-byte_recv_count)
            # If ever the other end closes on us before we are done,
            # give up and return a False status with zero bytes.
            if not new_bytes:
                return(False, b'')
            byte_recv_count += len(new_bytes)
            recv_bytes += new_bytes
        # Turn off the socket timeout if we finish correctly.
        sock.settimeout(None)            
        return (True, recv_bytes)
    # If the socket times out, something went wrong. Return a False
    # status.
    except socket.timeout:
        sock.settimeout(None)        
        print("recv_bytes: Recv socket timeout!")
        return (False, b'')
    

########################################################################
# Chat room Class 
########################################################################
class ChatRoom:
    def __init__(self, name, address, port):
        self.port = port
        self.address = address
        self.name = name

    def get_chat(self):
        return (self.name, self.address, self.port)
    
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

    def __init__(self):
        self.chatrooms = {}
        self.get_socket()
        self.receive_forever()


    def get_socket(self):
        try:
            # Create the TCP server listen socket in the usual way.
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((Server.HOSTNAME, Server.CHAT_ROOM_DIRECTORY_PORT))
            self.socket.listen(Server.BACKLOG)
            print("Chat Room Directory Server listening on port <port number> {} ...".format(Server.CHAT_ROOM_DIRECTORY_PORT))
        except Exception as msg:
            print(msg)
            exit()


    def receive_forever(self):
        try:
            while True:
                client = self.socket.accept()
                connection, address_port = client
                threading.Thread(target=self.connection_handler, args=(client,)).start()
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
                self.getDir()
            if cmd == CMD["MAKEROOM"]:
                print("Server: Recieved MAKEROOM CMD")
                error = self.makeRoom(client)
            if cmd == CMD["DELETEROOM"]:
                print("Server: Recieved DELETEROOM CMD")
                error = self.deleteRoom(client)
                if(error == 'close'):
                    print("Closing {} client connection ... ".format(address_port))           
                    connection.close()
                    break

        
    def getDir(self):
        return list(self.chatrooms.values())
    
    def makeRoom(self, client):
        connection, address = client

        status, chatname_size_field = recv_bytes(connection, CHATNAME_SIZE_FIELD_LEN)
        if not status:
            return 'close'
        chatname_size_bytes = int.from_bytes(chatname_size_field, byteorder='big')
        if not chatname_size_bytes:
            return 'close'

        # Now read and decode the requested chatname.
        status, chatname_bytes = recv_bytes(connection, chatname_size_bytes)
        if not status:
            return 'close'
        if not chatname_bytes:
            print("Connection is closed!")
            return 'close'

        chatname = chatname_bytes.decode(MSG_ENCODING)



        status, chatname_size_field = recv_bytes(connection, CHATNAME_SIZE_FIELD_LEN)
        if not status:
            return 'close'
        chatname_size_bytes = int.from_bytes(chatname_size_field, byteorder='big')
        if not chatname_size_bytes:
            return 'close'

        # Now read and decode the requested chatname.
        status, chatname_bytes = recv_bytes(connection, chatname_size_bytes)
        if not status:
            return 'close'
        if not chatname_bytes:
            print("Connection is closed!")
            return 'close'

        chatname = chatname_bytes.decode(MSG_ENCODING)
        print('Requested chatname = ', chatname)



        status, chatname_size_field = recv_bytes(connection, CHATNAME_SIZE_FIELD_LEN)
        if not status:
            return 'close'
        chatname_size_bytes = int.from_bytes(chatname_size_field, byteorder='big')
        if not chatname_size_bytes:
            return 'close'

        # Now read and decode the requested chatname.
        status, chatname_bytes = recv_bytes(connection, chatname_size_bytes)
        if not status:
            return 'close'
        if not chatname_bytes:
            print("Connection is closed!")
            return 'close'

        chatname = chatname_bytes.decode(MSG_ENCODING)
        print('Requested chatname = ', chatname)
    
        new_chatroom = ChatRoom(name, address, port)
        if all(new_chatroom[name] != obj[name] or new_chatroom["port"] != obj["port"] for obj in self.chatrooms.values()):
            self.chatrooms[name] = ChatRoom(name, address, port)
        else:
            print("Chat room has same address and port as an existing room")

    def deleteRoom(self, client):
        connection, address = client

        status, chatname_size_field = recv_bytes(connection, CHATNAME_SIZE_FIELD_LEN)
        if not status:
            return 'close'
        chatname_size_bytes = int.from_bytes(chatname_size_field, byteorder='big')
        if not chatname_size_bytes:
            return 'close'

        # Now read and decode the requested chatname.
        status, chatname_bytes = recv_bytes(connection, chatname_size_bytes)
        if not status:
            return 'close'
        if not chatname_bytes:
            print("Connection is closed!")
            return 'close'

        chatname = chatname_bytes.decode(MSG_ENCODING)
        print('delete chat = ', chatname)

        del self.chatrooms[chatname]
        




"""
            try:
                while True:
                    server_prompt_input = input("Connected to CRDS, please enter one of the following commands (getdir, makeroom <chat room name> <address> <port>, deleteroom <chat room name>: ")
                    if server_prompt_input:
                    # If the user enters something, process it.
                        try:
                            # Parse the input into a command and its
                            # arguments.
                            server_prompt_cmd, *server_prompt_args = server_prompt_input.split()
                        except Exception as msg:
                            print(msg)
                            continue
                        if server_prompt_cmd =='getdir':
                            try:
                                self.getDir()
                            except Exception as msg:
                                print(msg)
                                exit()

                        elif server_prompt_cmd =='makeroom':
                            try:
                                if (len(server_prompt_args) == 3):
                                    self.makeRoom(server_prompt_args[0], server_prompt_args[1], int(server_prompt_args[2]))
                                elif (len(server_prompt_args) == 2):
                                    print("No <port> passed in")
                                elif(len(server_prompt_args) == 1):
                                    print("No <address>, <port> passed in")
                                else:
                                    print("No arguments passed in")

                            except Exception as msg:
                                print(msg)
                                exit()
                        elif server_prompt_cmd =='deleteroom':
                            try:
                                if (len(server_prompt_args) == 1):
                                    pass
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
"""
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
        self.prompt_user_forever()

    
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
                client_prompt_input = input("Please enter one of the following commands (connect, bye, name <chat name>, chat <chat room name>: ")
                if client_prompt_input:
                # If the user enters something, process it.
                    try:
                        # Parse the input into a command and its
                        # arguments.
                        client_prompt_cmd, *client_prompt_args = client_prompt_input.split()
                    except Exception as msg:
                        print(msg)
                        continue
                    if client_prompt_cmd =='connect':
                        try:
                            self.connect_to_server()
                        except Exception as msg:
                            print(msg)
                            exit()
                        
                    elif client_prompt_cmd =='bye':
                        # Disconnect from the FS.
                        self.socket.close()
                        break

                    elif client_prompt_cmd =='name':
                        try:
                            if (len(client_prompt_args) == 2):
                                pass
                            else:
                                print("No <chat name> passed in")

                        except Exception as msg:
                            print(msg)
                            exit()
                    elif client_prompt_cmd =='chat':
                        try:
                            if (len(client_prompt_args) == 2):
                                pass
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






