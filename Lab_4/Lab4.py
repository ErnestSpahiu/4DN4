#!/usr/bin/env python3

########################################################################

import socket
import argparse
import sys, errno
import threading
import os

########################################################################

# Define all of the packet protocol field lengths.

CMD_FIELD_LEN            = 1 # 1 byte commands sent from the client.
FILENAME_SIZE_FIELD_LEN  = 1 # 1 byte file name size field.
FILESIZE_FIELD_LEN       = 8 # 8 byte file size field.
    
# Define a dictionary of commands. The actual command field value must
# be a 1-byte integer. For now, we only define the "GET" command,
# which tells the server to send a file.

CMD = {"NAME" : 1, "CHAT" : 2}

MSG_ENCODING = "utf-8"
SOCKET_TIMEOUT = 4

########################################################################
# Service Discovery Server
#
# The server listens on a UDP socket. When a service discovery packet
# arrives, it returns a response with the name of the service.
# 
########################################################################

class Server:

    ALL_IF_ADDRESS = "0.0.0.0"
    SERVICE_SCAN_PORT = 30000
    ADDRESS_PORT = (ALL_IF_ADDRESS, SERVICE_SCAN_PORT)

    HOSTNAME = "127.0.0.1"
    CHAT_ROOM_DIRECTORY_PORT = 50000

    MSG_ENCODING = "utf-8" 

    RECV_SIZE = 1024
    BACKLOG = 10

    def __init__(self):
        self.directory = {}
        self.showDir()        
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
            # Then loop forever, accepting incoming file sharing
            # connections. When one occurs, create a new thread for
            # handling it.
            while True:
                # Check for new file sharing clients. Pass the new client
                # off to the connection handler with a new execution
                # thread.
                client = self.socket.accept()
                connection, address_port = client
                threading.Thread(target=self.connection_handler, args=(client,)).start()
        except Exception as msg:
            print(msg)
        except KeyboardInterrupt:
            print()
        finally:
            # If something bad happens, make sure that we close the
            # socket.
            print("Closing {} client connection ... ".format(address_port))     
            connection.close()
            self.socket.close()
            sys.exit(1)


    def connection_handler(self, client):
        connection, address_port = client
        connection.setblocking(True)
        threadName = threading.current_thread().name
        print(threadName," - Connection received from",address_port)
        while True:
            # Receive bytes over the TCP connection. This will block
            # until "at least 1 byte or more" is available.
            recvd_bytes = connection.recv(1)
                        
            # If recv returns with zero bytes, the other end of the
            # TCP connection has closed (The other end is probably in
            # FIN WAIT 2 and we are in CLOSE WAIT.). If so, close the
            # server end of the connection and get the next client
            # connection.
            if len(recvd_bytes) == 0:
                print("Closing {} client connection ... ".format(address_port))
                connection.close()
                # Break will exit the connection_handler and cause the
                # thread to finish.
                break

            cmd = int.from_bytes(recvd_bytes, byteorder='big')
            print(cmd)
            if cmd == CMD["NAME"]:
                print("Server: Recieved NAME CMD")
                self.changeName(client)
            if cmd == CMD["CHAT"]:
                print("Server: Recieved CHAT CMD")
                error = self.getRoom(client)
                if(error == 'close'):
                    print("Closing {} client connection ... ".format(address_port))           
                    connection.close()
                    break
            if cmd == CMD["PUT"]:
                print("Server: Recieved PUT CMD")
                error = self.putFile(client)
                if(error == 'close'):
                    print("Closing {} client connection ... ".format(address_port))           
                    connection.close()
                    break

    def changeName(self):
        print("Name")

    def getRoom(self):
        print("Room")
        
    def showDir(self):
        server_list = os.listdir(Server.SERVER_DIR)
        list_item = ""
        for item in server_list:
            list_item += item + "\n"
        print(list_item)




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

    BROADCAST_ADDRESS = "255.255.255.255"
    # BROADCAST_ADDRESS = "192.168.1.255"    
    SERVICE_PORT = 30000
    ADDRESS_PORT = (BROADCAST_ADDRESS, SERVICE_PORT)

    SCAN_CYCLES = 2
    SCAN_TIMEOUT = 2

    SCAN_CMD = "SCAN"
    SCAN_CMD_ENCODED = SCAN_CMD.encode(MSG_ENCODING)

    SERVER_DIR = "./serverDirectory/"
    CLIENT_DIR = "./clientDirectory/"

    # Define the local file name where the downloaded file will be
    # saved.


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
                    elif client_prompt_cmd =='put':
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
                        
                    elif client_prompt_cmd =='bye':
                        # Disconnect from the FS.
                        self.socket.close()
                        break
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






