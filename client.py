import socket
import sys
import threading
import time

import const






# get information while connect to the chat
def receive(clSocket):
    # if the server is running
    global continue_running
    while continue_running:
        # get the nessage from client
        receiveMessage = clSocket.recv(1024).decode()
        """""
        check if the client ask to download a file from the 
        server if it is get the name of the file and start the process
        """
        if receiveMessage.startswith(const.download):
            message = receiveMessage[len(const.download) + 1: -1]
            file_name, file_size, port, port_back = message.split(",")
            t3 = threading.Thread(target=down_file, args=(file_name, file_size, port, port_back))
            t3.start()
        # if this is anther command send it to the receive function and than to the server
        elif len(receiveMessage) > 0:
            print(receiveMessage)


"""
this function ask from the client to command to do and send it to the server
"""


def clientMsg(clSocket):
    # while the chat is on air do:
    global continue_running
    while True:
        # get a message from the client
        msg = input("Enter your message:")
        # check if the command from the client is to disconnect from the chat
        if msg == const.disconnect:
            # send the command to the server
            clSocket.send(msg.encode())
            # close the client thread
            continue_running = False
            # close the client socket
            close_resoueces(clSocket)
            return
        else:
            # if its anther command send it to the server
            message_out = msg.encode()
            clSocket.send(message_out)


"""
this function 
"""


def parse_download_file(reads_bytes):
    index_of_closer = reads_bytes.index(bytes(">", "utf-8"))
    chunck = reads_bytes[1:index_of_closer]
    message = reads_bytes[index_of_closer + 1:]
    return (chunck.decode(), message)


"""
this function download file from the server
this function read data from the udp connection, and sending acks for each chunk that has been provided
in case chunck already send, don't add it.
keep doing it until all the file is sent. close the resources after that.
file-name - nameof the file to create
file_size - size of the file
free_port- port to read the file from
free_port_to_send_back - port to send ack to

"""
def down_file(file_name, file_size, free_port, free_port_to_send_back):
    global continue_running
    file_size = int(file_size)
    sent_chuncks = set()
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind(('0.0.0.0', int(free_port)))
    file = open(file_name, 'wb')
    bytes_recived_from_server = 0
    while continue_running and bytes_recived_from_server < file_size:
        reads_the_bytes = udp_socket.recv(const.buffer_size)
        chunk_num, sent_bytes = parse_download_file(reads_the_bytes)
        # in case the server sent the same chunck twice
        if chunk_num not in sent_chuncks:
            if not sent_bytes:
                break
            file.write(sent_bytes)
            bytes_recived_from_server += len(sent_bytes)
            ack_message = "ack {}".format(chunk_num)
            sent_chuncks.add(chunk_num)
            socket_to_write_back = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            #sending ack to the server
            socket_to_write_back.sendto(ack_message.encode(), ('127.0.0.1', int(free_port_to_send_back)))
            print(f'received: {bytes_recived_from_server} / {file_size} bytes')
    file.close()
    udp_socket.close()
    print("completed")
    return


"""
this function close client socket 
"""

def close_resoueces(clSocket):
    print("close client")
    clSocket.close()
    sys.exit(0)



continue_running = True

def run_client():
    clSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    clSocket.connect((const.HOST, const.server_port))

    # the client options
    print('---Client Manual---')
    print('\tTo connect the chat "<connect>"')
    print('\tTo send a private message to Another user enter "<set_msg><Name>"')
    print('\tTo send a message to all the users in the chat write "<set_msg_all>"')
    print('\tTo get a list of online users enter "<get_users>"')
    print('\tTo get the server files list enter:"<get_list_file>')
    print('\tIn order to receive a specific file from the server, write "f<download><test.txt>')
    print('\tTo download the file after requesting it enter "<proceed>')
    print("\tPlease select one of the options: ")

    connectMessage = clSocket.recv(1024)
    print(connectMessage.decode())
    t1 = threading.Thread(target=receive, args=(clSocket,))
    t2 = threading.Thread(target=clientMsg, args=(clSocket,))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

if __name__ == '__main__':
    run_client()
