#!/usr/bin/env python3

########################################################################

import socket
import argparse
import sys
import time
import struct
import ipaddress

########################################################################
# Multicast Address and Port
########################################################################

# MULTICAST_ADDRESS = "239.1.1.1"
MULTICAST_ADDRESS = "239.2.2.2"

MULTICAST_PORT = 2000

# Make them into a tuple.
MULTICAST_ADDRESS_PORT = (MULTICAST_ADDRESS, MULTICAST_PORT)

# Ethernet/Wi-Fi interface address
IFACE_ADDRESS = "192.168.1.22"

########################################################################
# Multicast Sender
########################################################################

class Sender:

    HOSTNAME = socket.gethostname()

    TIMEOUT = 2
    RECV_SIZE = 256
    
    MSG_ENCODING = "utf-8"
    MESSAGE =  HOSTNAME + " multicast beacon: "
    MESSAGE_ENCODED = MESSAGE.encode('utf-8')

    # Create a 1-byte maximum hop count byte used in the multicast
    # packets (i.e., TTL, time-to-live).
    TTL = 1 # multicast hop count
    TTL_BYTE = TTL.to_bytes(1, byteorder='big')
    # or: TTL_BYTE = struct.pack('B', TTL)
    # or: TTL_BYTE = b'01'

    def __init__(self):
        self.create_send_socket()
        self.send_messages_forever()

    def create_send_socket(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            ############################################################
            # Set the TTL for multicast.

            self.socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, Sender.TTL_BYTE)

            ############################################################
            # Bind to the interface that will carry the multicast
            # packets, or you can let the OS decide, which is usually
            # ok for a laptop or simple desktop. Include the port in
            # the binding or have the OS pick it.

            # self.socket.bind((IFACE_ADDRESS, 30000)) # Bind to port 30000.
            self.socket.bind((IFACE_ADDRESS, 0)) # Have the system pick a port number.

        except Exception as msg:
            print(msg)
            sys.exit(1)

    def send_messages_forever(self):
        try:
            beacon_sequence_number = 1
            while True:
                print("Sending multicast beacon {} {}".format(beacon_sequence_number, MULTICAST_ADDRESS_PORT))
                beacon_bytes = Sender.MESSAGE_ENCODED + str(beacon_sequence_number).encode('utf-8')

                ########################################################
                # Send the multicast packet
                self.socket.sendto(beacon_bytes, MULTICAST_ADDRESS_PORT)

                # Sleep for a while, then send another.
                time.sleep(Sender.TIMEOUT)
                beacon_sequence_number += 1
        except Exception as msg:
            print(msg)
        except KeyboardInterrupt:
            print()
        finally:
            self.socket.close()
            sys.exit(1)

########################################################################
# Multicast Receiver 
########################################################################
#
# There are two things that we need to do:
#
# 1. Signal to the os that we want a multicast group membership, so
# that it will capture multicast packets arriving on the designated
# interface. This will also ensure that multicast routers will forward
# packets to us. Note that multicast is at layer 3, so ports do not
# come into the picture at this point.
#
# 2. Bind to the appopriate address/port (L3/L4) so that packets
# arriving on that interface will be properly filtered so that we
# receive packets to the designated address and port.
#
############################################
# 1. IP add multicast group membership setup
############################################
#
# Signal to the os that you want to join a particular multicast group
# address on a specified interface. Done via setsockopt function call.
# The multicast address and interface (address) are part of the add
# membership request that is passed to the lower layers.
#
# This is done via MULTICAST_ADDRESS from above and RX_IFACE_ADDRESS
# defined below.
#
# If you choose "0.0.0.0" for the Rx interface, the system will select
# the interface, which will probably work ok. In more complex
# situations, where, for example, you may have multiple network
# interfaces, you may have to specify the interface explicitly by
# using its address, as shown in the examples below.

# RX_IFACE_ADDRESS = "0.0.0.0"
# RX_IFACE_ADDRESS = "127.0.0.1"
RX_IFACE_ADDRESS = IFACE_ADDRESS 

#################################################
# 2. Multicast receiver bind (i.e., filter) setup
#################################################
#
# The receiver socket bind address. This is used at the IP/UDP level to
# filter incoming multicast receptions. Using "0.0.0.0" should work
# ok. Binding using the unicast address, e.g., RX_BIND_ADDRESS =
# "192.168.1.22", fails (Linux) since arriving packets don't carry this
# destination address.
# 

RX_BIND_ADDRESS = "0.0.0.0"
# RX_BIND_ADDRESS = MULTICAST_ADDRESS # Ok for Linux/MacOS, not for Windows 10.

# Receiver socket will bind to the following.
RX_BIND_ADDRESS_PORT = (RX_BIND_ADDRESS, MULTICAST_PORT)

########################################################################

class Receiver:

    RECV_SIZE = 256

    def __init__(self):
        print("Bind address/port = ", RX_BIND_ADDRESS_PORT)
        
        self.get_socket()
        self.receive_forever()

    def get_socket(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
            # For MacOS use the following instead:
            # self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, True)

            ############################################################            
            # Bind to an address/port. In multicast, this is viewed as
            # a "filter" that deterimines what packets make it to the
            # UDP app.
            ############################################################            
            self.socket.bind(RX_BIND_ADDRESS_PORT)

            ############################################################
            # The multicast_request must contain a bytes object
            # consisting of 8 bytes. The first 4 bytes are the
            # multicast group address. The second 4 bytes are the
            # interface address to be used. An all zeros I/F address
            # means all network interfaces. They must be in network
            # byte order.
            ############################################################
            multicast_group_bytes = socket.inet_aton(MULTICAST_ADDRESS)
            # or
            # multicast_group_int = int(ipaddress.IPv4Address(MULTICAST_ADDRESS))
            # multicast_group_bytes = multicast_group_int.to_bytes(4, byteorder='big')
            # or
            # multicast_group_bytes = ipaddress.IPv4Address(MULTICAST_ADDRESS).packed
            print("Multicast Group: ", MULTICAST_ADDRESS)

            # Set up the interface to be used.
            multicast_iface_bytes = socket.inet_aton(RX_IFACE_ADDRESS)

            # Form the multicast request.
            multicast_request = multicast_group_bytes + multicast_iface_bytes
            print("multicast_request = ", multicast_request)

            # You can use struct.pack to create the request, but it is more complicated, e.g.,
            # 'struct.pack("<4sl", multicast_group_bytes,
            # int.from_bytes(multicast_iface_bytes, byteorder='little'))'
            # or 'struct.pack("<4sl", multicast_group_bytes, socket.INADDR_ANY)'

            # Issue the Multicast IP Add Membership request.
            print("Adding membership (address/interface): ", MULTICAST_ADDRESS,"/", RX_IFACE_ADDRESS)
            self.socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, multicast_request)
        except Exception as msg:
            print(msg)
            sys.exit(1)

    def receive_forever(self):
        while True:
            try:
                data, address_port = self.socket.recvfrom(Receiver.RECV_SIZE)
                address, port = address_port
                print("Received: {} {}".format(data.decode('utf-8'), address_port))
            except KeyboardInterrupt:
                print(); exit()
            except Exception as msg:
                print(msg)
                sys.exit(1)

########################################################################
# Process command line arguments if run directly.
########################################################################

if __name__ == '__main__':
    roles = {'receiver': Receiver,'sender': Sender}
    parser = argparse.ArgumentParser()

    parser.add_argument('-r', '--role',
                        choices=roles, 
                        help='sender or receiver role',
                        required=True, type=str)

    args = parser.parse_args()
    roles[args.role]()

########################################################################











