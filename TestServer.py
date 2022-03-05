import unittest
import server
import socket


class TestServer(unittest.TestCase):

    def test_sign_in(self):
        users ={}
        clSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.sign_in(users,"<connect><tal>", clSocket)
        self.assertEqual(users[clSocket], "tal")

    def test_file_list(self):
        self.assertEqual(server.get_files_string(), "<server_files> : beni.txt, pic9.png")

    def test_user_list(self):
        users ={"socket1" : "tal", "socket2" :"tzach"}
        self.assertEqual(server.get_user_string(users), "tal, tzach")

    def test_disconnect(self):
        users ={"socket1" : "tal", "socket2" :"tzach"}
        server.remove_user_meta_data(users, "socket1")
        self.assertEqual(users, {"socket2" :"tzach"})

    def test_send_message_to_all(self):
        message = "<set_msg_all>hello world"
        res1, res2 = server.get_text_for_send_all(message,"beni")
        self.assertEqual(res1, "beni: hello world")
        self.assertEqual(res2, "me: hello world")



if __name__ == '__main__':
    unittest.main()
