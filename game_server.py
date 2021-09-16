import socket
import threading
import asyncio
import time
import queue
import logging
import json


class ServerLog(object):
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


server_logger = ServerLog("server.log").logger

# 我们使用 socket 模块的 socket 函数来创建一个 socket 对象。socket 对象可以通过调用其他函数来设置一个 socket 服务。
# 现在我们可以通过调用 bind(hostname, port) 函数来指定服务的 port(端口)。
# 接着，我们调用 socket 对象的 accept 方法。该方法等待客户端的连接，并返回 connection 对象，表示已连接到客户端。

# 获取本地主机名
# HOST = socket.gethostname()
HOST = "10.30.99.42"
PORT = 9996
BUFFSIZ = 102400
ADDR = (HOST, PORT)

# 创建事件对象
event = threading.Event()
msg_event = threading.Event()


# 用来存放客户端连接对象
global clients_connect_list
clients_connect_list = []

# 暂时用json，后面用数据库存
roles_data = {
    "abcd1": {"user_name": "abcd1", "role_id": "11121", "role_name": "plaer1", "jump_hight": 0.75, "pos": [0, 0, 0], "ip": ""},
    "abcd2": {"user_name": "abcd2", "role_id": "11122", "role_name": "plaer2", "jump_hight": 0.75, "pos": [2, 2, 0], "ip": ""}
}

update_player_data = {
    "11121": {"role_id": "11121", "role_name": "plaer1", "jump_hight": 0.75, "pos": [0, 0, 0], "setH": 0, "action": None},
    "11122": {"role_id": "11122", "role_name": "plaer2", "jump_hight": 0.75, "pos": [2, 2, 0], "setH": 0, "action": None}
}

def get_role_for_ip(ip):
    for role in roles_data:
        if roles_data[role]['ip'] == ip:
            return roles_data[role]


def send_msg_to_client(datas, clients_connect):
    datas = json.dumps(datas)
    clients_connect[0].send(datas.encode("utf-8"))

def send_msg_to_all_client(datas):
    datas = json.dumps(datas)
    global clients_connect_list
    for clients_connect in clients_connect_list:
        clients_connect[0].send(datas.encode("utf-8"))


def send_msg_to_other_client(datas, clients_connect):
    datas = json.dumps(datas)
    global clients_connect_list
    for clients_connect in clients_connect_list:
        if clients_connect == clients_connect:
            continue
        clients_connect[0].send(datas.encode("utf-8"))


# 队列最大数为10个
work_queue = queue.Queue(10)
def more_thread_listen_clients_connect(server_socket):
    global clients_connect_list
    while True:
        aa = len(clients_connect_list) + 1
        server_logger.info("服务开启，等待第%s个客户端连接" % aa)
        # 等待客户端连接，返回连接到服务器的客户端对象和地址
        client_socket, addr = server_socket.accept()
        work_queue.put((client_socket, addr))
        clients_connect_list.append((client_socket, addr))
        server_logger.info("第%s个客户端主动和我建立了连接, 客户端ip和端口号: %s" % (aa, str(addr)))


def client_more_thread_recv(clients_connect):
    client_socket, addr = clients_connect
    while True:
        try:
            recv_msg = client_socket.recv(BUFFSIZ)
        except ConnectionResetError:
            role_data = get_role_for_ip(addr[0])
            msg = "客户端:%s , %s 断开了连接" % (addr[0], role_data["user_name"])
            push_msg = role_data["role_name"] + "退出了游戏"
            datas_msg = {
                "request_type": "logout",
                "role_id": role_data["role_id"],
                "push_msg": push_msg
            }
            server_logger.warning(msg)
            client_socket.close()
            clients_connect_list.remove(clients_connect)
            # 通知其他人发消息
            send_msg_to_other_client(datas_msg, clients_connect)
            break
            exit(0)
        except BlockingIOError:
            server_logger.warning("接收客户端:%s 的消息时出现阻塞错误BlockingIOError" % str(addr))
        if not recv_msg:
            server_logger.warning("接收到了客户端空的值，可能客户端关闭了或者发错了")
            client_socket.close()
            clients_connect_list.remove(clients_connect)
            exit(0)
        # 接收数据后进行解码
        recv_msg = recv_msg.decode("utf-8")
        after_recv_client_msg_doing(recv_msg, clients_connect)


def after_recv_client_msg_doing(data, clients_connect):
    client_socket, addr = clients_connect
    server_logger.debug("客户端请求内容：%s" % data)
    data = json.loads('%s' % data)
    request_type = data["request_type"]
    if request_type == "update_player":
        role_id = data["role_id"]
        for key in data:
            update_player_data[role_id][key] = data[key]
        datas = {
            "request_type": "update_player",
            "role_data": update_player_data[role_id]
        }
        send_msg_to_other_client(datas, clients_connect)
        return
    if request_type == "login":
        server_logger.info("%s 请求登录" % data["user_name"])
        role_data = roles_data[data["user_name"]]
        role_data["ip"] = addr[0]
        datas = {
            "request_type": "login",
            "role_data": role_data
        }
        send_msg_to_client(datas, clients_connect)
        return
    if request_type == "push":
        server_logger.info("收到了客户端%s 的消息: %s" % (addr[0], data))
        return
    server_logger.warning("接收到客户端%s的请求，但是request_type中没有定义这个类型要做什么事，因此没有做任何处理，"
                          "客户端消息: %s" % (addr[0], data))



def more_thread_server_and_client_messaging():
    while True:
        clients_connect = work_queue.get()
        client_recv_thread = threading.Thread(target=client_more_thread_recv, args=(clients_connect,))
        server_logger.info("和客户端通信:%s,当前线程:%s" % (clients_connect[1], client_recv_thread.getName(), ))
        client_recv_thread.setDaemon(True)
        client_recv_thread.start()


def main_tcp_more_thread_recv():
    # 创建 socket 对象, af_inet,stream
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        # 防止端口号被占用，强制关闭之前的服务器连接
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # 绑定端口号
        try:
            server_socket.bind(ADDR)
        except OSError:
            server_logger.error("端口号被占用, 或ip不对")
            raise
        # 设置监听的最大连接数，超过后排队
        server_socket.listen(200)
        more_client_messaging_thread = threading.Thread(target=more_thread_server_and_client_messaging)
        more_client_messaging_thread.setDaemon(True)
        server_logger.info("开启监听线程，当前监听线程:%s" % more_client_messaging_thread.getName())
        more_client_messaging_thread.start()
        more_thread_listen_clients_connect(server_socket)

def main_udp():
    BUFFSIZ = 102400
    # 创建 socket 对象, udp连接
    with socket.socket(type=socket.SOCK_DGRAM) as udp_server_socket:
        # 防止端口号被占用
        udp_server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # 绑定端口号
        try:
            udp_server_socket.bind(ADDR)
        except OSError:
            server_logger.error("端口号被占用, 或ip不对")
            raise
        while True:
            # 接收客户端的消息，客户端带上ip和端口号
            from_client_msg, client_addr = udp_server_socket.recvfrom(BUFFSIZ)
            # 接收数据后进行解码
            from_client_msg = from_client_msg.decode("utf-8")
            server_logger.info("来自 %s 发来的消息：%s" % (client_addr, from_client_msg))
            udp_server_socket.sendto("我收到你的消息了".encode("utf-8"), client_addr)


async def tcp_echo_client(message):
    pass



if __name__ == "__main__":
    main_tcp_more_thread_recv()
    #main_udp()