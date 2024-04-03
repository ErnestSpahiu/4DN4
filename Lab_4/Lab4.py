#!/usr/bin/env python3

########################################################################

import socket
import argparse
import sys
import threading
import json

########################################################################
# recv_bytes frontend to recv
########################################################################


CMD_FIELD_LEN = 1  # 1 byte commands sent from the client.
CHATNAME_SIZE_FIELD_LEN = 1  # 1 byte Chat name size field.
ADDR_SIZE_FIELD_LEN = 1  # 1 byte Chat name size field.
PORT_SIZE_FIELD_LEN = 1  # 1 byte Chat name size field.

MSG_ENCODING = "utf-8"
CMD = {"GETDIR": 1, "MAKEROOM": 2, "DELETEROOM": 3}
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

    chatrooms = [{'name': 'Room_0', 'address': '239.0.0.1', 'port': '1000'}]

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
                self.makeRoom(connection)
            if cmd == CMD["DELETEROOM"]:
                print("Server: Recieved DELETEROOM CMD")
                self.deleteRoom(connection)

    def getDir(self, connection):
        data_string = json.dumps(self.chatrooms)
        connection.send(data_string.encode(MSG_ENCODING))

    def makeRoom(self, connection):
        roomname_size = int.from_bytes(connection.recv(1), byteorder='big')
        roomname = connection.recv(roomname_size).decode(Server.MSG_ENCODING)

        multicast_ip = socket.inet_ntoa(connection.recv(4))
        multicast_port = connection.recv(
            Server.RECV_SIZE).decode(Server.MSG_ENCODING)

        for room in self.chatrooms:
            print(room['address'])
            print(room['port'])
            if room['address'] != multicast_ip or room['port'] != multicast_port:
                self.chatrooms.append(
                    {'name': roomname, 'address': multicast_ip, 'port': multicast_port})

    def deleteRoom(self, connection):
        roomname_size = int.from_bytes(connection.recv(1), byteorder='big')
        roomname = connection.recv(roomname_size).decode(Server.MSG_ENCODING)
        for room in self.chatrooms:
            if room['name'] == roomname:
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

RX_BIND_ADDRESS = "0.0.0.0"


class Client:

    RECV_SIZE = 1024
    MSG_ENCODING = "utf-8"
    TTL = 1  # Hops
    TTL_SIZE = 1  # Bytes
    TTL_BYTE = TTL.to_bytes(TTL_SIZE, byteorder='big')

    def __init__(self):
        self.get_socket()
        self.connected = False
        self.name = ""
        self.chat_rooms = []
        self.kill_threads = False
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
                # We are connected to the server. Prompt the user for what to
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

                    elif client_prompt_cmd == 'bye':
                        # Disconnect from the FS.
                        self.connected = False
                        self.socket.close()
                        continue

                    elif client_prompt_cmd == 'name':
                        try:
                            if (len(client_prompt_args) == 1):
                                self.changeName(client_prompt_args[0])
                            else:
                                print("No <chat name> passed in")
                        except Exception as msg:
                            print(msg)
                            exit()
                    elif client_prompt_cmd == 'chat':
                        try:
                            if (len(client_prompt_args) == 1):
                                self.start_chat_room(client_prompt_args[0])
                            else:
                                print("No <chat room name> passed in")
                        except Exception as msg:
                            print(msg)
                            exit()

                    elif client_prompt_cmd == 'getdir' and self.connected:
                        try:
                            self.getDir()
                            break
                        except Exception as msg:
                            print(msg)
                            exit()

                    elif client_prompt_cmd == 'makeroom' and self.connected:
                        try:
                            if (len(client_prompt_args) == 3):
                                self.makeRoom(
                                    client_prompt_args[0], client_prompt_args[1], client_prompt_args[2])
                                break
                            elif (len(client_prompt_args) == 2):
                                print("No <port> passed in")
                            elif (len(client_prompt_args) == 1):
                                print("No <address>, <port> passed in")
                            else:
                                print("No arguments passed in")

                        except Exception as msg:
                            print(msg)
                            exit()
                    elif client_prompt_cmd == 'deleteroom' and self.connected:
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

    def start_chat_room(self, chat_name):
        # checks
        if self.name == "":
            print("Please enter a name first")
            return
        # Make sure chatroom exists
        for room in self.chat_rooms:
            if room['name'] == chat_name:
                chat_room_address = room['address']
                chat_room_port = room['port']
                break
        else:
            print("Chat room does not exist")
            return

        # connect to chatroom with multicast ip and port
        print(
            f"Entering chat mode for chat room {chat_name}. Press <ctrl>] to exit chat mode.")

        self.multicast_addr_port = (chat_room_address, chat_room_port)

        # Sender
        self.multicast_send = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.multicast_send.setsockopt(
            socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, Client.TTL_BYTE)

        # Receiver and Registration
        self.multicast_rec = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.multicast_rec.setsockopt(
            socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        self.multicast_rec.setsockopt(
            socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, Client.TTL_BYTE)
        self.multicast_rec.bind(
            (RX_BIND_ADDRESS, int(self.multicast_addr_port[1])))

        multicast_group_bytes = socket.inet_aton(self.multicast_addr_port[0])
        print("Multicast Group: ", self.multicast_addr_port[0])

        # Set up the interface to be used.
        multicast_if_bytes = socket.inet_aton(RX_BIND_ADDRESS)

        # Form the multicast request.
        multicast_request = multicast_group_bytes + multicast_if_bytes
        print("multicast_request = ", multicast_request)

        # Issue the Multicast IP Add Membership request.
        print("Adding membership (address/interface): ",
              self.multicast_addr_port[0], "/", self.multicast_addr_port[1])
        self.multicast_rec.setsockopt(
            socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, multicast_request)

        # Start the receiver/sender threads.
        self.recv_thread = threading.Thread(target=self.receive_chat_messages,
                                            args=(chat_name,))
        self.send_thread = threading.Thread(target=self.send_chat_messages,
                                            args=(chat_name,))

        self.recv_thread.daemon = True
        self.send_thread.daemon = True

        self.recv_thread.start()
        self.send_thread.start()

        self.recv_thread.join()
        self.send_thread.join()

        return

    def receive_chat_messages(self, chat_name):
        try:
            while True:
                if self.kill_threads:
                    return
                # Receive messages from the multicast group
                response, address = self.multicast_rec.recvfrom(
                    Client.RECV_SIZE)
                response = response.decode(self.MSG_ENCODING)
                print(f'\n{response}')
                print(f"{chat_name} > ")
        except (KeyboardInterrupt):
            print()
            print("Exiting chat mode...")
            return

    def send_chat_messages(self, chat_name):
        # Send messages in the chat room
        try:
            while True:
                if self.kill_threads:
                    return

                # Prompt the user for a message to send to the chat room.
                message = input(f"{chat_name} > ")
                # "\x1d == Ctrl + ]"
                if '\x1d' in message:
                    # Exit chat mode if the control sequence is entered.
                    print('Exiting chat mode...')
                    self.kill_threads = True
                    return
                # Send the message to the multicast group
                message_bytes = f'{self.name}: {message}'.encode(
                    self.MSG_ENCODING)
                port = (self.multicast_addr_port[0], int(
                    self.multicast_addr_port[1]))
                self.multicast_send.sendto(message_bytes, port)
        except (KeyboardInterrupt):
            print()
            print("Exiting chat mode...")

    def getDir(self):
        cmd_field = CMD["GETDIR"].to_bytes(1, byteorder='big')
        try:
            # Send the request packet to the server.
            self.socket.sendall(cmd_field)
        except:
            print("No connection.")
            return
        # receive the directory listing from server
        recvd_bytes = self.socket.recv(Client.RECV_SIZE)
        if len(recvd_bytes) == 0:
            print("Closing server connection ... ")
            self.socket.close()
            return
        dir = json.loads(recvd_bytes.decode(Server.MSG_ENCODING))
        self.chat_rooms = dir
        print("Here is the listing of the current chat room directory:",
              dir)
        self.prompt_user_forever()

    def makeRoom(self, roomname, address, port):
        cmd_field = CMD["MAKEROOM"].to_bytes(1, byteorder='big')
        roomname_bytes = roomname.encode(Server.MSG_ENCODING)
        roomname_size = len(roomname).to_bytes(1, byteorder='big')

        address_bytes = socket.inet_aton(address)
        port_str_bytes = port.encode(Server.MSG_ENCODING)

        pkt = cmd_field + roomname_size + roomname_bytes + address_bytes + port_str_bytes

        self.chat_rooms.append(
            {'name': roomname, 'address': address, 'port': port})
        self.socket.send(pkt)
        self.prompt_user_forever()

    def deleteRoom(self, roomname):
        cmd_field = CMD["DELETEROOM"].to_bytes(1, byteorder='big')
        delete_bytes = roomname.encode(Server.MSG_ENCODING)
        delete_size = len(roomname).to_bytes(1, byteorder='big')
        pkt = cmd_field + delete_size + delete_bytes
        for room in self.chat_rooms:
            if room['name'] == roomname:
                self.chat_rooms.remove(room)
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
