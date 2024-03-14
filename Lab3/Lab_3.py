#!/usr/bin/env python3

########################################################################

import socket
import argparse
import sys
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

CMD = {"GET" : 1, "PUT" : 2, "LIST" : 3, "BYE" : 4}

MSG_ENCODING = "utf-8"
SOCKET_TIMEOUT = 4

########################################################################
# recv_bytes frontend to recv
########################################################################

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
    FILE_SHARING_PORT = 50000

    MSG_ENCODING = "utf-8"    
    
    SCAN_CMD = "SCAN"
    SCAN_CMD_ENCODED = SCAN_CMD.encode(MSG_ENCODING)
    
    MSG = "Group 20's File Sharing Service"
    MSG_ENCODED = MSG.encode(MSG_ENCODING)

    RECV_SIZE = 1024
    BACKLOG = 10

    FILE_NOT_FOUND_MSG = "Error: Requested file is not available!"

    # This is the file that the client will request using a GET.
    # REMOTE_FILE_NAME = "greek.txt"
    # REMOTE_FILE_NAME = "twochars.txt"
    REMOTE_FILE_NAME = "ocanada_greek.txt"
    # REMOTE_FILE_NAME = "ocanada_english.txt"

    SERVER_DIR = "./serverDirectory/"

    def __init__(self):
        self.get_service_discovery_socket()
        self.get_file_sharing_socket()        
        self.receive_forever()

    def get_service_discovery_socket(self):
        try:
            # Create an IPv4 UDP socket, self.sd_socket, to listen for
            # service discovery broadcasts.
            self.sd_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # set socket layer socket options.
            self.sd_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # Bind to all interfaces and the agreed on broadcast port.
            self.sd_socket.bind( (Server.ALL_IF_ADDRESS, Server.SERVICE_SCAN_PORT) )
            print("Listening for service discovery messages on SD port", Server.SERVICE_SCAN_PORT)            
        except Exception as msg:
            print(msg)
            sys.exit(1)

    def get_file_sharing_socket(self):
        try:
            # Create the TCP server listen socket in the usual way.
            self.fs_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.fs_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.fs_socket.bind((Server.HOSTNAME, Server.FILE_SHARING_PORT))
            self.fs_socket.listen(Server.BACKLOG)
            print("Listening for file sharing connections on port {} ...".format(Server.FILE_SHARING_PORT))
        except Exception as msg:
            print(msg)
            exit()


    def receive_forever(self):
        try:
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
        except Exception as msg:
            print(msg)
        except KeyboardInterrupt:
            print()
        finally:
            # If something bad happens, make sure that we close the
            # socket.
            print("Closing server socket ...")
            self.fs_socket.close()
            self.sd_socket.close()
            sys.exit(1)
    
    def listen_for_service_discovery(self):
        while True:
            try:
                # Check for service discovery queries and respond with
                # your name and address.
                recvd_bytes, address = self.sd_socket.recvfrom(Server.RECV_SIZE)
                
                recvd_str = recvd_bytes.decode(Server.MSG_ENCODING)
                if Server.SCAN_CMD in recvd_str:
                    self.sd_socket.sendto(Server.MSG_ENCODED, address)
            
            except KeyboardInterrupt:
                print()
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
            if cmd == CMD["LIST"]:
                print("Server: Recieved RLIST CMD")
                server_list = os.listdir(Server.SERVER_DIR)
                list_item = ""
                for item in server_list:
                    list_item += item + "\n"

                list_item = list_item.encode(Server.MSG_ENCODING)
                list_size = len(list_item)
                list_sizeBytes = list_size.to_bytes(FILESIZE_FIELD_LEN, byteorder='big')
                connection.sendall(list_sizeBytes + list_item)
            if cmd == CMD["GET"]:
                print("Server: Recieved GET CMD")
                self.getFile(client)


    def getFile(self, client):
        connection, address = client

        status, filename_size_field = recv_bytes(connection, FILENAME_SIZE_FIELD_LEN)
        if not status:
            print("Closing connection ...")            
            connection.close()
            return
        filename_size_bytes = int.from_bytes(filename_size_field, byteorder='big')
        if not filename_size_bytes:
            print("Connection is closed!")
            connection.close()
            return
        
        print('Filename size (bytes) = ', filename_size_bytes)

        # Now read and decode the requested filename.
        status, filename_bytes = recv_bytes(connection, filename_size_bytes)
        if not status:
            print("Closing connection ...")            
            connection.close()
            return
        if not filename_bytes:
            print("Connection is closed!")
            connection.close()
            return

        filename = filename_bytes.decode(MSG_ENCODING)
        print('Requested filename = ', filename)

        ################################################################
        # See if we can open the requested file. If so, send it.
        
        # If we can't find the requested file, shutdown the connection
        # and wait for someone else.
        try:
            file = open(filename, 'r').read()
        except FileNotFoundError:
            print(Server.FILE_NOT_FOUND_MSG)
            connection.close()                   
            return

        # Encode the file contents into bytes, record its size and
        # generate the file size field used for transmission.
        file_bytes = file.encode(MSG_ENCODING)
        file_size_bytes = len(file_bytes)
        file_size_field = file_size_bytes.to_bytes(FILESIZE_FIELD_LEN, byteorder='big')

        # Create the packet to be sent with the header field.
        pkt = file_size_field + file_bytes
        
        try:
            # Send the packet to the connected client.
            connection.sendall(pkt)
            print("Sending file: ", filename)
            print("file size field: ", file_size_field.hex(), "\n")
            # time.sleep(20)
        except socket.error:
            # If the client has closed the connection, close the
            # socket on this end.
            print("Closing client connection ...")
            connection.close()
            return

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
    DOWNLOADED_FILE_NAME = "filedownload.txt"


    def __init__(self):
        self.get_service_discovery_socket()
        self.get_file_sharing_socket()       
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
            self.sd_socket.settimeout(Client.SCAN_TIMEOUT)
        except Exception as msg:
            print(msg)
            sys.exit(1)

    
    def get_file_sharing_socket(self):
        try:
            self.fs_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except Exception as msg:
            print(msg)
            exit()


    def prompt_user_forever(self):
        
        try:
            while True:
                # We are connected to the FS. Prompt the user for what to
                # do.
                connect_prompt_input = input("Please enter one of the following commands (scan, Connect <IP address> <port>, llist, rlist, put, get, bye: ")
                if connect_prompt_input:
                # If the user enters something, process it.
                    try:
                        # Parse the input into a command and its
                        # arguments.
                        connect_prompt_cmd, *connect_prompt_args = connect_prompt_input.split()
                    except Exception as msg:
                        print(msg)
                        continue
                    if connect_prompt_cmd =='scan':
                        self.scan_for_service()
                    elif connect_prompt_cmd =='connect':
                        try:
                            if(len(connect_prompt_args) == 2):
                                self.connect_to_server(connect_prompt_args[0], int(connect_prompt_args[1]))
                            else:
                                self.connect_to_server()
                        except Exception as msg:
                            print(msg)
                            exit()
                    elif connect_prompt_cmd =='llist':
                        # read the local directory and list the files
                        print("Local directory listing:")
                        print(os.listdir(Client.CLIENT_DIR))
                        pass
                    elif connect_prompt_cmd =='rlist':
                        # Do a sendall and ask the FS for a remote file listing.
                        # Do a recv and output the response when it returns.
                        self.get_remote_list()
                        pass
                    elif connect_prompt_cmd =='rlist':
                        # Do a sendall and ask the FS for a remote file listing.
                        # Do a recv and output the response when it returns.
                        pass
                    elif connect_prompt_cmd =='put':
                        # Write code to interact with the FS and upload a
                        # file.
                        pass
                    elif connect_prompt_cmd =='get':
                        try:
                            if(len(connect_prompt_args)==1):
                                self.get_file(connect_prompt_args[0])
                            else:
                                self.get_file()
                        except Exception as msg:
                            print(msg)
                            exit()
                        pass
                    elif connect_prompt_cmd =='bye':
                        # Disconnect from the FS.
                        self.fs_socket.close()
                        break
                    else:
                        pass       

        except (KeyboardInterrupt, EOFError):
            print()
            print("Closing server connection ...")
            # If we get and error or keyboard interrupt, make sure
            # that we close the socket.
            self.fs_socket.close()
            self.sd_socket.close()
            sys.exit(1)
                

    def scan_for_service(self):
        # Collect our scan results in a list.
        scan_results = []

        # Repeat the scan procedure a preset number of times.
        for i in range(Client.SCAN_CYCLES):

            # Send a service discovery broadcast.        
            self.sd_socket.sendto(Client.SCAN_CMD_ENCODED, Client.ADDRESS_PORT)
        
            while True:
                # Listen for service responses. So long as we keep
                # receiving responses, keep going. Timeout if none are
                # received and terminate the listening for this scan
                # cycle.
                try:
                    recvd_bytes, address = self.sd_socket.recvfrom(Client.RECV_SIZE)
                    recvd_msg = recvd_bytes.decode(Client.MSG_ENCODING)

                    # Record only unique services that are found.
                    if (recvd_msg, address) not in scan_results:
                        scan_results.append((recvd_msg, address))
                        continue
                # If we timeout listening for a new response, we are
                # finished.
                except socket.timeout:
                    break

        # Output all of our scan results, if any.
        if scan_results:
            for result in scan_results:
                print("{} found at IP address/port {}".format(result[0], result[1]))
        else:
            print("No services found.")

    def connect_to_server(self, hostname=Server.HOSTNAME, port=Server.FILE_SHARING_PORT):
            # Connect to the server using its socket address tuple.
            self.fs_socket.connect((hostname, port))
            print("Connected to \"{}\" on port {}".format(hostname, port))
    
    def get_remote_list(self):
        #Convert the command to native byte order.
        cmd_field = CMD["LIST"].to_bytes(CMD_FIELD_LEN, byteorder='big')

        #Send the command
        self.fs_socket.sendall(cmd_field)

        #Get size as int
        list_sizeBytes = self.fs_socket.recv(FILESIZE_FIELD_LEN)
        list_size = int.from_bytes(list_sizeBytes, byteorder='big')

        #Get the list
        list = self.fs_socket.recv(list_size).decode(MSG_ENCODING)
        print(list)

    def get_file(self, filename=Server.REMOTE_FILE_NAME):
        ################################################################
        # Generate a file transfer request to the server
        
        # Create the packet cmd field.
        cmd_field = CMD["GET"].to_bytes(CMD_FIELD_LEN, byteorder='big')

        # Create the packet filename field.
        filename_field_bytes = filename.encode(MSG_ENCODING)

        # Create the packet filename size field.
        filename_size_field = len(filename_field_bytes).to_bytes(FILENAME_SIZE_FIELD_LEN, byteorder='big')

        # Create the packet.
        print("CMD field: ", cmd_field.hex())
        print("Filename_size_field: ", filename_size_field.hex())
        print("Filename field: ", filename_field_bytes.hex())
        
        pkt = cmd_field + filename_size_field + filename_field_bytes

        # Send the request packet to the server.
        self.fs_socket.sendall(pkt)

        ################################################################
        # Process the file transfer repsonse from the server
        
        # Read the file size field returned by the server.
        status, file_size_bytes = recv_bytes(self.fs_socket, FILESIZE_FIELD_LEN)
        if not status:
            print("Closing connection ...")            
            self.fs_socket.close()
            return

        print("File size bytes = ", file_size_bytes.hex())
        if len(file_size_bytes) == 0:
            self.fs_socket.close()
            return

        # Make sure that you interpret it in host byte order.
        file_size = int.from_bytes(file_size_bytes, byteorder='big')
        print("File size = ", file_size)

        #self.socket.settimeout(4)                                  
        status, recvd_bytes_total = recv_bytes(self.fs_socket, file_size)
        if not status:
            print("Closing connection ...")            
            self.fs_socket.close()
            return
        # print("recvd_bytes_total = ", recvd_bytes_total)
        # Receive the file itself.
        try:
            # Create a file using the received filename and store the
            # data.
            print("Received {} bytes. Creating file: {}" \
                  .format(len(recvd_bytes_total), Client.DOWNLOADED_FILE_NAME))

            with open(Client.DOWNLOADED_FILE_NAME, 'w') as f:
                recvd_file = recvd_bytes_total.decode(MSG_ENCODING)
                f.write(recvd_file)
            print(recvd_file)
        except KeyboardInterrupt:
            print()
            exit(1)
            
            
                
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






