#!/usr/bin/python3

"""Group:20 Tae"
    Members:
    1. Ernest Spahiu
    2. Bardia Sedighi
    3. Stiv Berberi

"""
# Imports 
########################################################################

import argparse
import socket
import sys
from cryptography.fernet import Fernet
import csv
########################################################################
# Echo Server class
########################################################################

def encrypt(message, key):
    # encode both the message and the key to bytes
    message_bytes = message.encode('utf-8')
    encryption_key_bytes = key.encode('utf-8')
    # use fernet to encrypt the message with the key
    fernet = Fernet(encryption_key_bytes)
    #encrypt the message
    encrypted_message_bytes = fernet.encrypt(message_bytes)
    return encrypted_message_bytes

def decypt(encrypted_message_bytes, key):
    #encode the key to bytes
    encryption_key_bytes = key.encode('utf-8')
    # use fernet to decrypt the message with the key
    fernet = Fernet(encryption_key_bytes)
    decrypted_message_bytes = fernet.decrypt(encrypted_message_bytes)
    #decode the message
    decrypted_message = decrypted_message_bytes.decode('utf-8')
    return decrypted_message



class Server:

    # Set the server hostname used to define the server socket address
    # binding. Note that "0.0.0.0" or "" serves as INADDR_ANY. i.e.,
    # bind to all local network interfaces.
    # HOSTNAME = "192.168.1.22" # single interface    
    # HOSTNAME = "hornet"       # valid hostname (mapped to address/IF)
    # HOSTNAME = "localhost"    # local host (mapped to local address/IF)
    # HOSTNAME = "127.0.0.1"    # same as localhost
    HOSTNAME = "0.0.0.0"      # All interfaces.
    
    # Server port to bind the listen socket.
    PORT = 50000
    
    RECV_BUFFER_SIZE = 1024 # Used for recv.
    MAX_CONNECTION_BACKLOG = 10 # Used for listen.

    # We are sending text strings and the encoding to bytes must be
    # specified.
    MSG_ENCODING = "ascii" # ASCII text encoding.
    # MSG_ENCODING = "utf-8" # Unicode text encoding.

    # Create server socket address. It is a tuple containing
    # address/hostname and port.
    SOCKET_ADDRESS = (HOSTNAME, PORT)

    def __init__(self):
        self.create_listen_socket()
        self.process_connections_forever()

    def create_listen_socket(self):
        try:
            # Create an IPv4 TCP socket.
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            # Set socket layer socket options. This one allows us to
            # reuse the socket address without waiting for any timeouts.
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # Bind socket to socket address, i.e., IP address and port.
            self.socket.bind(Server.SOCKET_ADDRESS)

            # Set socket to listen state.
            self.socket.listen(Server.MAX_CONNECTION_BACKLOG)
            
            #server has started, read in the csv file
            with open('course_grades_2024.csv', 'r') as file:
                reader = csv.reader(file)
                #1st row defines meaning of columns
                #entries 2 and 3 in rows are the student id and the key
                for row in reader:
                    print(row)

            print("Listening on port {} ...".format(Server.PORT))
        except Exception as msg:
            print(msg)
            sys.exit(1)

    def process_connections_forever(self):
        try:
            while True:
                # Block while waiting for accepting incoming TCP
                # connections. When one is accepted, pass the new
                # (cloned) socket info to the connection handler
                # function. Accept returns a tuple consisting of a
                # connection reference and the remote socket address.
                self.connection_handler(self.socket.accept())
        except Exception as msg:
            print(msg)
        except KeyboardInterrupt:
            print()
        finally:
            # If something bad happens, make sure that we close the
            # socket.
            self.socket.close()
            sys.exit(1)

    def connection_handler(self, client):
        # Unpack the client socket address tuple.
        connection, address_port = client
        print("-" * 72)
        print("Connection received from {}.".format(address_port))
        # Output the socket address.
        print(client)

        while True:
            try:
                #client will always send student id followed by commands

                # Receive bytes over the TCP connection. This will block
                # until "at least 1 byte or more" is available.
                recvd_bytes = connection.recv(Server.RECV_BUFFER_SIZE)
                
                #initialize the encrypted msg
                encrypted_message_bytes = bytes("0", 'utf-8')

                # If recv returns with zero bytes, the other end of the
                # TCP connection has closed (The other end is probably in
                # FIN WAIT 2 and we are in CLOSE WAIT.). If so, close the
                # server end of the connection and get the next client
                # connection.
                if len(recvd_bytes) == 0:
                    print("Closing client connection ... ")
                    connection.close()
                    break
                
                # Decode the received bytes back into strings. Then output
                # them.
                recvd_str = recvd_bytes.decode(Server.MSG_ENCODING)
                print("Received: ", recvd_str)

                #get the student id and the key from the rcvd client 
                student_id, command_id = recvd_str.split(',')
                print("Student ID: ", student_id)
                print("Command ID: ", command_id)
                
                # ==== New Decryption Code ====
                #load data from csv file
                encrypt_key = ""
                data = []
                with open('course_grades_2024.csv', 'r') as file:
                    reader = csv.reader(file)
                    for row in reader:
                        data.append(row)
                
                #now check if the student id (2) is in the csv file
                #if it is, then get the key (3)
                for row in data:
                    if row[1] == student_id:
                        encrypt_key = row[2]
                        
                        #user was found, return data the command is requesting
                        #init user grade data
                        num_grades = 0
                        sum_grades = 0
                        if command_id == "GMA":
                            # get midterm (col 8) average of class
                            for row in data[1:]: #skipping header row
                                sum_grades += float(row[7])
                                num_grades += 1
                    
                            avg_midterm_grade = sum_grades / num_grades
                            encrypted_message_bytes = encrypt(str(avg_midterm_grade), encrypt_key)
                            print("GMA: Encrypted: ", encrypted_message_bytes)
                            print("GMA: avg midterm grade: ", avg_midterm_grade)
                        break
                    else:
                        print("Student ID not found")
                        break

                connection.sendall(encrypted_message_bytes)
                print("Sent: ", encrypted_message_bytes)

                # ==== Original Echo Code ====
                # Send the received bytes back to the client. We are
                # sending back the raw data.
                #connection.sendall(recvd_bytes)
                #print("Sent: ", recvd_str)

            except KeyboardInterrupt:
                print()
                print("Closing client connection ... ")
                connection.close()
                break

########################################################################
# Echo Client class
########################################################################

class Client:

    # Set the server to connect to. If the server and client are running
    # on the same machine, we can use the current hostname.
    # SERVER_HOSTNAME = socket.gethostname()
    # SERVER_HOSTNAME = "192.168.1.22"
    SERVER_HOSTNAME = "localhost"
    
    # Try connecting to the compeng4dn4 echo server. You need to change
    # the destination port to 50007 in the connect function below.
    # SERVER_HOSTNAME = 'compeng4dn4.mooo.com'

    RECV_BUFFER_SIZE = 1024 # Used for recv.    
    # RECV_BUFFER_SIZE = 5 # Used for recv.    

    def __init__(self):
        self.get_socket()
        self.connect_to_server()
        self.send_console_input_forever()

    def get_socket(self):
        try:
            # Create an IPv4 TCP socket.
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            # Allow us to bind to the same port right away.            
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # Bind the client socket to a particular address/port.
            # self.socket.bind((Server.HOSTNAME, 40000))
                
        except Exception as msg:
            print(msg)
            sys.exit(1)

    def connect_to_server(self):
        try:
            # Connect to the server using its socket address tuple.
            self.socket.connect((Client.SERVER_HOSTNAME, Server.PORT))
            print("Connected to \"{}\" on port {}".format(Client.SERVER_HOSTNAME, Server.PORT))
        except Exception as msg:
            print(msg)
            sys.exit(1)

    def get_console_input(self):
        # In this version we keep prompting the user until a non-blank
        # line is entered, i.e., ignore blank lines.

        # We need to send the student ID and the command ID to the server
        while True:
            self.input_text1 = input("Input Student ID: ")
            self.input_text2 = input("Input Command ID: ")
            self.input_text_ALL = f'{self.input_text1},{self.input_text2}'
            if self.input_text1 != "":
                break
    
    def send_console_input_forever(self):
        while True:
            try:
                self.get_console_input()
                self.connection_send()
                self.connection_receive()
            except (KeyboardInterrupt, EOFError):
                print()
                print("Closing server connection ...")
                # If we get and error or keyboard interrupt, make sure
                # that we close the socket.
                self.socket.close()
                sys.exit(1)
                
    def connection_send(self):
        try:
            # Send string objects over the connection. The string must
            # be encoded into bytes objects first.
            self.socket.sendall(self.input_text_ALL.encode(Server.MSG_ENCODING))
        except Exception as msg:
            print(msg)
            sys.exit(1)

    def connection_receive(self):
        try:
            # Receive and print out text. The received bytes objects
            # must be decoded into string objects.
            recvd_bytes = self.socket.recv(Client.RECV_BUFFER_SIZE)

            # recv will block if nothing is available. If we receive
            # zero bytes, the connection has been closed from the
            # other end. In that case, close the connection on this
            # end and exit.
            if len(recvd_bytes) == 0:
                print("Closing server connection ... ")
                self.socket.close()
                sys.exit(1)


            #read in the key from the csv file
            encrypt_key = ""
            data = []
            with open('course_grades_2024.csv', 'r') as file:
                reader = csv.reader(file)
                for row in reader:
                    data.append(row)
            #find key using student id = self.input_text1
            for row in data:
                if row[1] == self.input_text1:
                    encrypt_key = row[2]
                    break
                else:
                    print("Student ID not found")
                    break
            print("Key: ", encrypt_key)
            #need to decrypt the message received from the server
            decrypted_message = decypt(recvd_bytes, encrypt_key)
            print("Received: ", recvd_bytes.decode(Server.MSG_ENCODING))

        except Exception as msg:
            print(msg)
            sys.exit(1)

########################################################################
# Process command line arguments if this module is run directly.
########################################################################

# When the python interpreter runs this module directly (rather than
# importing it into another file) it sets the __name__ variable to a
# value of "__main__". If this file is imported from another module,
# then __name__ will be set to that module's name.

if __name__ == '__main__':
    roles = {'client': Client,'server': Server}
    parser = argparse.ArgumentParser()

    parser.add_argument('-r', '--role',
                        choices=roles, 
                        help='server or client role',
                        required=True, type=str)

    args = parser.parse_args()
    roles[args.role]()

########################################################################






