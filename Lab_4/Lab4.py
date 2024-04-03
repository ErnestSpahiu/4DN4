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



        status, addr_size_field = recv_bytes(connection, ADDR_SIZE_FIELD_LEN)
        if not status:
            return 'close'
        addr_size_bytes = int.from_bytes(addr_size_field, byteorder='big')
        if not addr_size_bytes:
            return 'close'

        # Now read and decode the requested addr.
        status, addr_bytes = recv_bytes(connection, addr_size_bytes)
        if not status:
            return 'close'
        if not addr_bytes:
            print("Connection is closed!")
            return 'close'

        addr = addr_bytes.decode(MSG_ENCODING)
        print('Requested addr = ', addr)



        status, port_size_field = recv_bytes(connection, PORT_SIZE_FIELD_LEN)
        if not status:
            return 'close'
        port_size_bytes = int.from_bytes(port_size_field, byteorder='big')
        if not port_size_bytes:
            return 'close'

        # Now read and decode the requested port.
        status, port_bytes = recv_bytes(connection, port_size_bytes)
        if not status:
            return 'close'
        if not port_bytes:
            print("Connection is closed!")
            return 'close'

        port = port_bytes.decode(MSG_ENCODING)
        print('Requested port = ', port)
    
        new_chatroom = ChatRoom(chatname, addr, port)
        if all(chatname != chat.name or port != chat.port for chat in self.chatrooms.items()):
            self.chatrooms[chatname] = new_chatroom
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
                    "Please enter one of the following commands (connect, bye, name <chat name>, chat <chat room name>: ")
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
        self.input_for_server()

    def input_for_server(self):
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
                            break
                        except Exception as msg:
                            print(msg)
                            exit()

                    elif server_prompt_cmd =='makeroom':
                        try:
                            if (len(server_prompt_args) == 3):
                                self.makeRoom(server_prompt_args[0], server_prompt_args[1], int(server_prompt_args[2]))
                                break
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
                                self.deleteRoom(server_prompt_args[0])
                            else:
                                print("No <chat room name> passed in")
                        except Exception as msg:
                            print(msg)
                            exit()
                    else:
                        pass
                
            #go back to main command prompt
            self.prompt_user_forever() 

        except (KeyboardInterrupt, EOFError):
            print()
            print("Closing server connection ...")
            # If we get and error or keyboard interrupt, make sure
            # that we close the socket.
            self.socket.close()
            sys.exit(1)

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
        if len(recv_bytes) == 0:
            print("Closing server connection ... ")
            self.socket.close()
            return
        dir = recvd_bytes.decode(MSG_ENCODING)
        print("Here is the listing of the current chat room directory:", json.loads(dir))
        
    def makeRoom(self, roomname, address, port):
        cmd_field = CMD["MAKEROOM"].to_bytes(1, byteorder='big')
        room = (" " + str(roomname) + " " + str(address) + " " + str(port)).encode(MSG_ENCODING)
        pkt = cmd_field + room

        try:
            #send request to server
            self.socket.sendall(pkt)
            #receive response
            recvd_bytes = self.socket.recv(Client.RECV_SIZE)
            if len(recv_bytes) == 0:
                print("Closing server connection ... ")
                self.socket.close()
                return
            resp = recvd_bytes.decode(MSG_ENCODING)
        except:
            print("No connection.")
            return
    
    def deleteRoom(self, roomname):
        cmd_field = CMD["DELETEROOM"].to_bytes(1, byteorder='big')
        room = (" "+str(roomname)).encode(MSG_ENCODING)
        pkt = cmd_field + room
        try:
            #send request to server
            self.socket.sendall(pkt)
            #receive response
            recvd_bytes = self.socket.recv(Client.RECV_SIZE)
            if len(recv_bytes) == 0:
                print("Closing server connection ... ")
                self.socket.close()
                return
            resp = recvd_bytes.decode(MSG_ENCODING)
        except:
            print("No connection.")
            return


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
