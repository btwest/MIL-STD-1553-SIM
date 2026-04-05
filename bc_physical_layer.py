import socket
import threading
import queue

_BUS_SEND_PORTS   = {'A': 2001, 'B': 2003}
_BUS_LISTEN_PORTS = {'A': 2000, 'B': 2002}

class BC_Sender:
    def __init__(self, bus: str = 'A'):
        if bus not in ('A', 'B'):
            raise ValueError(f"bus must be 'A' or 'B', got '{bus}'")
        self._port = _BUS_SEND_PORTS[bus]
        self.bus = bus

    def send_message(self, message):
        destination_ip = "127.255.255.255"  # loopback broadcast — avoids duplicate delivery on WSL/multi-interface hosts
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.sendto(message.encode('utf-8'), (destination_ip, self._port))

class BC_Listener:
    def __init__(self, bus: str = 'A'):
        if bus not in ('A', 'B'):
            raise ValueError(f"bus must be 'A' or 'B', got '{bus}'")
        self._port = _BUS_LISTEN_PORTS[bus]
        self.bus = bus
        self.data_received = queue.Queue()

    def start_listening(self):
        socket_variable = \
            socket.socket(
                socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        socket_variable.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        socket_variable.bind(("", self._port))
        while True:
            data, addr = socket_variable.recvfrom(1024)
            self.data_received.put(data.decode('utf-8'))

if __name__ == "__main__":
    listener = BC_Listener()
    listener_thread = threading.Thread(
        target=listener.start_listening
    )
    listener_thread.start()
    while True:
        try:
            item = listener.data_received.get_nowait()
            print(item)
        except queue.Empty:
            pass
