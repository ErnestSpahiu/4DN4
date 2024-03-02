#!/usr/bin/env python3

# Use the Python cryptography module to do some symmetric encryption.
# If it is not installed, you need to run: pip3 install cryptography.

from cryptography.fernet import Fernet

message = "To be, or not to be: that is the question."
print("message = ", message)
message_bytes = message.encode('utf-8')

encryption_key = "M7E8erO15CIh902P8DQsHxKbOADTgEPGHdiY0MplTuY="
# Previously generated using: encryption_key = Fernet.generate_key()
# Shared by the server and client.
encryption_key_bytes = encryption_key.encode('utf-8')

# Encrypt the message for transmission at the server.
fernet = Fernet(encryption_key_bytes)
encrypted_message_bytes = fernet.encrypt(message_bytes)
print()
print("encrypted_message_bytes = ", encrypted_message_bytes)
print()

# Decrypt the message after reception at the client.
decrypted_message_bytes = fernet.decrypt(encrypted_message_bytes)
decrypted_message = decrypted_message_bytes.decode('utf-8')
print("decrypted_message = ", decrypted_message)

