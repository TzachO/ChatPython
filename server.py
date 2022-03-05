import os
import socket
import threading
import time
import traceback
import select
from os import listdir
from os.path import isfile, join
import const

BUFFER_SIZE = 4096

"""
this function get from the client message to connect
"""


def sign_in(users, message, connect):
    start_from = len(const.connect)
    # get from the client message his name
    name = message[start_from + 1: -1]
    """
    check if the client name ia already in use if yes,
    tell the client to chose anther name, else, connect to the server
    """
    if name in users.values():
        connect.send(("" + name + " this nick name in use. please choose different nickname.").encode())
    else:
        print("User " + name + " Joined the chat.")
        message = "User " + name + " has been connected to the chat room."
        sent_message_to_all(message, users)
        users[connect] = name


"""
this function send a broadcast message
"""


def sent_message_to_all(message, users):
    # go over all the client and send them the message
    for user in users.keys():
        user.send(message.encode())


"""
this function send s broadcast message or a single message
<set_msg_all>message
<set_msg_all><user_name><message>
"""


def send_message(message, users, connection):
    # get the name of the client from the users dict
    name = users[connection]
    # check if the client ask for broadcast message
    if message.startswith(const.set_msg_all):
        # send the message to all the online users
        msg_to_all, msg_to_me = get_text_for_send_all(message, name)
        for socket in users.keys():
            if connection != socket:
                socket.send(msg_to_all.encode())
            else:
                socket.send(msg_to_me.encode())
    # if not a broadcast message , its private , so send it to from source to dest
    else:
        message = message[len(const.set_msg) + 1:]
        index_of_name_closer = message.index(">")
        send_to = message[:index_of_name_closer]
        for socket in users:
            if users[socket] == send_to:
                message_to_sent = name + ":" + message[index_of_name_closer + 1:]
                socket.send(message_to_sent.encode())


def get_text_for_send_all(message, name):
    message_to_send = message[len(const.set_msg_all):]
    msg_to_all = name + ": " + message_to_send
    msg_to_me = "me: " + message_to_send
    return msg_to_all, msg_to_me

"""
this function send all the users that are in the chat
"""
def get_users(users, connection):
    users_list = get_user_string(users)
    connection.send(users_list.encode())

def get_user_string(users):
    return ", ".join(users.values())


"""
this function remove the chat user from the server metadata
"""
def user_disconnection(connection, users):
    name = users[connection]
    remove_user_meta_data(users, connection)
    message = "User " + name + " disconnected."
    print(message)
    sent_message_to_all(message.encode(), users)

def remove_user_meta_data(users, connection):
    users.pop(connection)

"""
this function send list of files
"""
def get_files(connection):
    connection.send(get_files_string().encode())

def get_files_string():
    files = [f for f in listdir(const.files_dir) if isfile(join(const.files_dir, f))]
    return "<server_files> : " + ", ".join(files)

"""
This function get form the client command to download a file
"""
def request_to_download_file(message, connection, files_waiting_for_download):
    data_str = message
    file_name = data_str[len(const.download) + 1: -1]
    files_waiting_for_download[connection] = file_name
    connection.send(('file - ' + file_name + ' request received, proceed, and file name to save as').encode())


"""
this function get port that not in use
"""
def get_free_port(ports_in_use):
    for i in range(const.server_port_range_start, const.server_port_range_end + 1):
        if i not in ports_in_use:
            return (i, i + 1)


"""
this function send file from the server to the client
Sending file data in chuncks, attaching serial number for each chunck.
this function trying to keep sending the same chunck until ack it sent from the client.
after all the data is sent, closing the resouces
"""
def send_file(message, connection, users, files):
    udp_server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    save_as_name = message[len(const.proceed) + 1: -1]
    name = users[connection]
    if connection not in files:
        connection.send('first ask for file downlod'.encode())
    else:
        server_file = files[connection]
        file_size = os.path.getsize("files/{}".format(server_file))
        port_to_use, port_to_recieve = get_free_port(ports)
        ports.add(port_to_use)
        ports.add(port_to_recieve)
        # <download><file_name><file_size><port>
        message = "<download><{},{},{}, {}>".format(save_as_name, file_size, port_to_use, port_to_recieve)

        connection.send(message.encode())
        client_address = connection.getsockname()[0]
        time.sleep(3)
        sent_data = 0
        file = open("files/{}".format(server_file), 'rb')
        chunk_num = 0
        socket_to_recieve = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        socket_to_recieve.bind(('0.0.0.0', int(port_to_recieve)))
        #while data still exist
        while True:
            reading_bytes = file.read(BUFFER_SIZE - 100)
            if not reading_bytes:
                break
            chunck_prefix = "<{}>".format(chunk_num).encode()
            data = ""
            #waiting for ack from the user, keep sending data
            while data != "ack {}".format(chunk_num):
                udp_server_socket.sendto(chunck_prefix + reading_bytes, (client_address, port_to_use))
                ready = select.select([socket_to_recieve], [], [], const.timeout_in_seconds)
                if ready[0]:
                    data = socket_to_recieve.recv(4096).decode()
            chunk_num += 1
            #count number of bytes sent from the user
            sent_data += len(reading_bytes)
            connection.send(f'sent: {sent_data} / {file_size}'.encode())
            print(f'sent: {sent_data} / {file_size} bytes to {name}')
        ports.remove(port_to_use)
        ports.remove(port_to_recieve)

        file.close()
        files.pop(connection)


def connection_communication(current_socket):
    while True:
        try:
            clientMsg = current_socket.recv(1024).decode()
            # sign in
            if clientMsg.startswith(const.connect):
                sign_in(users, clientMsg, current_socket)
                # send msg to user
            elif clientMsg.startswith(const.set_msg[:-1]):
                send_message(clientMsg, users, current_socket)
                # get users
            elif clientMsg.startswith(const.get_users):
                get_users(users, current_socket)
                # client exit / remove
            elif clientMsg.startswith(const.disconnect):
                user_disconnection(current_socket, users)
                return
                # get server file list
            elif clientMsg.startswith(const.get_list_file):
                get_files(current_socket)
            # file requests
            elif clientMsg.startswith(const.download):
                request_to_download_file(clientMsg, current_socket, files_waiting_for_download)
            # file download over UDP (proceed button)
            elif clientMsg.startswith(const.proceed):
                t1 = threading.Thread(target=send_file,
                                      args=(clientMsg, current_socket, users, files_waiting_for_download))
                t1.start()
        except ValueError and KeyError and FileNotFoundError as e:
            traceback.print_exc()
users = {}
ports = set()
files_waiting_for_download = {}
def run_server():

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('', const.server_port))
    server_socket.listen(const.number_of_users)

    print('~~~ Server is Running and listening ~~~')
    while True:
        connect, addr = server_socket.accept()
        connect.send(("You are connected from:" + str(addr)).encode())
        user_thread = threading.Thread(target=connection_communication, args=(connect,))
        user_thread.start()
    server_socket.close()

if __name__ == '__main__':
    run_server()