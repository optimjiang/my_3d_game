import socket
import threading
from queue import Queue
import sys
import time
import logging
import json
# pip install PyExecJS
#import execjs

# # 1. 在windows上不需要其他的依赖便可运行execjs， 也可以调用其他的JS环境
# # windows 默认的执行JS的环境
# execjs.get().name
# 返回值： JScript
# # 作者本人的windows上装有Node.js ， 所以返回值不同
# execjs.get().name
# 返回值： Node.js(V8)
#
# # 2. 在ubuntu下需要安装执行JS环境依赖, 作者的环境为PhantomJS
# execjs.get().name
# 返回值： PhantomJS
#
# # 3. 源码中给出， 可执行execjs的环境：
# PyV8 = "PyV8"
# Node = "Node"
# JavaScriptCore = "JavaScriptCore"
# SpiderMonkey = "SpiderMonkey"
# JScript = "JScript"
# PhantomJS = "PhantomJS"
# SlimerJS = "SlimerJS"
# Nashorn = "Nashorn"
# 调用javascript代码
#print(execjs.eval("new Date"))



class ClientLog(object):
    def __init__(self, filename):
        self.logger = logging.getLogger(filename)
        log_format = logging.Formatter("%(asctime)s %(filename)s第%(lineno)s行 %(levelname)s: %(message)s")
        file_handler = logging.FileHandler(filename=filename, encoding="utf-8")
        file_handler.setFormatter(log_format)
        self.logger.addHandler(file_handler)
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(log_format)
        self.logger.addHandler(stream_handler)
        self.logger.setLevel(logging.DEBUG)

class ClientLogObject():
    client_logger = ClientLog("client.log").logger

client_logger = ClientLogObject().client_logger

# 接下来我们写一个简单的客户端实例连接到以上创建的服务。端口号为 9999。
# socket.connect(hosname, port ) 方法打开一个 TCP 连接到主机为 hostname 端口为 port 的服务商。
# 连接后我们就可以从服务端获取数据，记住，操作完成后需要关闭连接。

# 创建 socket 对象, af_inet,stream
# tcpc_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# 获取本地主机名
# HOST = socket.gethostname()

class CommWithServer(object):
    def __init__(self, host="10.30.99.42", port=9996, role=None):
        client_logger.debug("执行CommWithServer.__init__()")
        self.buffsize = 1024
        # udp最多接收100M的数据
        self.udp_buffsize = 104857600
        self.addr = (host, port)
        self.requeset_fun_dict = {}
        self.player = role


    def recv_server_tcp(self, timeout=10):
        client_logger.debug("执行CommWithServer.recv_server_tcp()")
        isretry = False
        while True:
            # 接收TCP连接的服务器的消息
            try:
                data = self.tcp_socket.recv(self.buffsize)
                if not data:
                    if not isretry:
                        stime = time.time()
                        isretry = True
                    if time.time()-stime > timeout:
                        client_logger.warning("服务器连接不上，或服务器消息一直丢失，或服务器一直发空消息，断开连接")
                        # 关闭服务器连接
                        self.tcp_socket.close()
                        return -1
                    else:
                        client_logger.warning("读取到了服务器的空消息，服务器可能有异常，如丢包、发错了消息，关闭了服务器等，重试中...")
                        time.sleep(1)
                        continue
            except ConnectionResetError:
                client_logger.info("服务器关闭了连接")
                self.tcp_socket.close()
                return -1
            # 接收数据后进行解码
            data = data.decode("utf-8")
            self.after_recv_server_msg_doing(data)



    def after_recv_server_msg_doing(self, data):
        client_logger.debug("执行CommWithServer.after_recv_server_msg_doing()")
        data = json.loads(data)
        client_logger.info("接收到服务端发来的消息:%s" % data)
        request_type = data["request_type"]
        if request_type == "update_player":
            client_logger.warning(data["push_msg"])

        elif request_type == "login":
            client_logger.info("登录成功！")
            self.after_login_update_data(data["role_data"])

        elif request_type == "push":
            client_logger.warning(data["push_msg"])

        elif request_type == "logout":
            client_logger.info(data["push_msg"])
            self.local.requeset_fun(data)

        else:
            client_logger.warning("接收到服务端发来的请求, 但request_type没有定义服务器发来request_type类型，因此没有做任何处理，"
                              "服务器消息：%s" % data)


    def send_server_tcp(self, msg):
        client_logger.debug("执行CommWithServer.send_server_tcp()")
        client_logger.debug("请求:%s" % msg)
        msg = json.dumps(msg)
        # 给服务器发送消息，这里需要编码成字节才能传输
        if not msg:
            client_logger.warning("不能发空消息给服务器")
            return 0
        try:
            self.tcp_socket.send(msg.encode("utf-8"))
        except ConnectionAbortedError:
            client_logger.info("服务器关闭了连接")
            self.tcp_socket.close()
            return -1
        except OSError:
            client_logger.info("服务器套接字已经关闭了")
            self.tcp_socket.close()
            return -1
        except ConnectionResetError:
            client_logger.error("无法连接到服务器...服务器ip:%s,端口号:%s" % self.addr)
            self.tcp_socket.close()
        return 1


    def connect_server_tcp(self):
        client_logger.debug("执行CommWithServer.connect_server_tcp()")
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            # 尝试连接服务器，指定主机和端口
            self.tcp_socket.connect(self.addr)
        except ConnectionRefusedError:
            client_logger.error("无法连接到服务器...服务器ip:%s,端口号:%s" % self.addr)
            self.tcp_socket.close()
            return 0
        except TimeoutError:
            self.tcp_socket.close()
            client_logger.error("连接服务器超时...服务器ip:%s,端口号:%s" % self.addr)
            return -1
        recv_msg_thread = threading.Thread(target=self.recv_server_tcp, args=(self.tcp_socket,))
        recv_msg_thread.start()
        return 1


    def request_server(self, request_concent, key, request_fun=None):
        client_logger.debug("执行CommWithServer.request_server()")
        # 向服务器发起请求，服务器回应了，则以及服务器的回应来执行request_fun方法
        if self.send_server_tcp(request_concent) == 1:
            self.requeset_fun_dict[key] = request_fun


    def login_server(self, user_name, passwd):
        client_logger.debug("执行CommWithServer.login_server()")
        client_logger.debug("开始连接服务器")
        if self.connect_server_tcp():
            login_msg = {"request_type": "login", "user_name": user_name, "passwd": passwd}
            self.send_server_tcp(login_msg)
        else:
            client_logger.debug('登录服务器失败 %s')
            self.player.jump_hight = 0.75
            self.player.role_id = "00000"

    def after_login_update_data(self, data):
        client_logger.debug("执行CommWithServer.after_login_update_data()")
        client_logger.debug('服务器:%s' % data)
        self.player.user_name = data["user_name"]
        self.player.role_id = data["role_id"]
        self.player.role_name = data["role_name"]
        self.player.set_pos(tuple(data["pos"]))
        self.player.jump_hight = data["jump_hight"]


    def connect_server_udp(self):
        self.udp_socket = socket.socket(type=socket.SOCK_DGRAM)
        return 1


    def recev_server_udp(self):
        # 客户端接收服务发来的值
        data, server_addr = self.udp_socket.recvfrom(self.udp_buffsize)
        data = data.decode("utf-8")
        self.after_recv_server_msg_doing(data)


    def send_server_udp(self, msg):
        if not msg:
            client_logger.warning("不能发空消息给服务器")
            return 0
        self.udp_socket.sendto(msg.encode("utf-8"), self.addr)
        return 1