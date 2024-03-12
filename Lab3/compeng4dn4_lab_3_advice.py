#!/usr/bin/env python3

########################################################################

import socket
import argparse
import sys
import threading
import os

########################################################################
# File Sharing Client Template
########################################################################

class Client:

    def __init__(self):
        self.get_service_discovery_socket()
        self.prompt_user_forever()

    def get_service_discovery_socket(self):
        try:
            # Set up a UDP socket for service discovery.  Set socket
            # layer socket options, i.e., socket.SO_REUSEADDR. Enable
            # broadcasting, i.e., socket.SO_BROADCAST. Set
            # timeout on socket, e.g., settimeout(3).
            self.sd_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # set socket layer socket options.
            self.sd_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # Set the option for broadcasting.
            self.sd_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            # Set service discovery timeout.
            self.sd_socket.settimeout(3)
        except Exception as msg:
            # exit

    def scan_for_server(self):
        print("SERVICE DISCOVERY scan ...")
        # Send a service scan broadcast. If a socket timeout occurs,
        # there is probably no FS server listening.
        self.sd_socket.sendto(Client.MESSAGE_ENCODED, Client.ADDRESS_PORT)
        try:
            recvd_bytes, address = self.sd_socket.recvfrom(1024)
            # If a FS server responds, print out the details so that
            # we can connect to its file sharing port.
            print(recvd_bytes.decode('utf-8'), "found.", address)
        except socket.timeout:
            print("No services found.")

    def process_connect_prompt_input(self):
        while True:
            # We are connected to the FS. Prompt the user for what to
            # do.
            connect_prompt_input = input(Client.CONNECT_PROMPT)
            if connect_prompt_input:
            # If the user enters something, process it.
                try:
                    # Parse the input into a command and its
                    # arguments.
                    connect_prompt_cmd, *connect_prompt_args = connect_prompt_input.split()
                except Exception as msg:
                    print(msg)
                    continue
                if connect_prompt_cmd =='llist':
                    # Get a local files listing and print it out.
                    pass
                elif connect_prompt_cmd =='rlist':
                    # Do a sendall and ask the FS for a remote file listing.
                    # Do a recv and output the response when it returns.
                elif connect_prompt_cmd =='put':
                    # Write code to interact with the FS and upload a
                    # file.
                    pass
                elif connect_prompt_cmd =='get':
                    # Write code to interact with the FS and download
                    # a file.
                    pass
                elif connect_prompt_cmd =='bye':
                    # Disconnect from the FS.
                    self.fs_ocket.close()
                    break
                else:
                    pass                                    


########################################################################
# File Sharing Server Template
########################################################################

class Server:

    def __init__(self):
        self.get_service_discovery_socket()
        self.get_file_sharing_socket()        
        self.receive_forever()

    def get_service_discovery_socket(self):
        try:
            # Create an IPv4 UDP socket, self.sd_socket, to listen for
            # service discovery broadcasts.
            self.socketSD = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # set socket layer socket options.
            self.socketSD.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # Bind to all interfaces and the agreed on broadcast port.
            self.socketSD.bind(Server.ADDRESS_PORT)
            print("Listening for service discovery messages on SD port", Client.SD_PORT)            
        except Exception as msg:
            print(msg)
            sys.exit(1)

    def get_file_sharing_socket(self):
        try:
            # Create a file sharing TCP socket self.fs_socket as per
            # usual and get it into the listen state.
        except Exception as msg:
            print(msg)
            sys.exit(1)

    def listen_for_service_discovery(self):
        while True:
            # Check for service discovery queries and respond with
            # your name and address.
            data, address = self.sd_socket.recvfrom(Server.RECV_SIZE)
            data = data.decode('utf-8')
            if data == "SERVICE DISCOVERY":
                print("Broadcast received: ", data, address)
                self.sd_socket.sendto(self.SD_RESPONSE_ENCODED, address)
            else:
                pass

    def receive_forever(self):
        # First, create a thread that will handle incoming service
        # discoveries.
        threading.Thread(target=self.listen_for_service_discovery).start()
        # Then loop forever, accepting incoming file sharing
        # connections. When one occurs, create a new thread for
        # handling it.
        while True:
            # Check for new file sharing clients. Pass the new client
            # off to the connection handler with a new execution
            # thread.
            client = self.fs_socket.accept()
            threading.Thread(target=self.connection_handler, args=(client,)).start()

    def connection_handler(self, client):
        connection, address_port = client
        connection.setblocking(True)
        threadName = threading.currentThread().getName()
        print(threadName," - Connection received from",address_port)
        while True:
            recvd_bytes = connection.recv(1024).decode('utf-8')
            if len(recvd_bytes) == 0:
                print(threadName," - Closing client connection ... ")
                connection.close()
                break
            # recv the first byte of the incoming message and go into
            # an if statement that tests for all of the client/server
            # commands. Handle the command as appropriate.






