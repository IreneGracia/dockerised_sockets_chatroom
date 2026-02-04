import socket
import sys
from threading import Thread, Event, Lock
import signal
import os

PORT = int(os.getenv("PORT", "8000"))
ADDRESS = os.getenv("ADDRESS", "127.0.0.1")


class ClientReceive(Thread):
    def __init__(self, c_socket: socket.socket, stop_event: Event):
        super().__init__()
        self.c_socket = c_socket
        self.stop_event = stop_event

    def run(self):
        while not self.stop_event.is_set():
            try:
                msg_received = self.c_socket.recv(1024)
                if msg_received == b"":
                    # server closed connection
                    self.stop_event.set()
                    try:
                        os.close(0)
                        # unblocks input()
                    except OSError:
                        pass
                    break
                print(msg_received.decode("ascii", errors="replace"))
            except OSError:
                self.stop_event.set()
                try:
                    os.close(0)
                except OSError:
                    pass
                break


def shutdown(c_socket, stop_event, socket_lock: Lock, msg="Disconnected from server"):
    stop_event.set()
    if msg:
        print(msg)

    # unblock input() by closing stdin
    try:
        os.close(0)
    except OSError:
        pass

    with socket_lock:
        try:
            c_socket.close()
        except OSError:
            pass


def make_signal_handler(c_socket, stop_event, socket_lock):
    def handler(signum, frame):
        shutdown(c_socket, stop_event, socket_lock)
        sys.exit(0)
    return handler


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("You must pass the client name as a command line argument.")
    client_name = sys.argv[1]

    c_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        c_socket.connect((ADDRESS, PORT))

    except OSError:
        print("Could not connect to server. Connection failed")
        sys.exit(1)

    stop_event = Event()
    socket_lock = Lock()

    handler = make_signal_handler(c_socket, stop_event, socket_lock)

    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)

    print("Connected to server on address", ADDRESS)

    with socket_lock:
        try:
            c_socket.sendall(client_name.encode("ascii"))
        except OSError:
            shutdown(c_socket, stop_event, socket_lock, msg="Failed to send client name")
            sys.exit(1)

    try:
        msg = c_socket.recv(1024)
    except OSError:
        msg = b""

    users = msg.decode("ascii", errors="replace").split(", ") if msg else []

    if client_name in users:
        users.remove(client_name)

    if not users:
        print(f'You joined the chat as "{client_name}". You are the first to join.')
    else:
        print(f'You joined the chat as "{client_name}". People in the chatroom: {", ".join(users)}')

    receiver = ClientReceive(c_socket, stop_event)
    #ensure immediate shutdown with low risk of lost printed messages
    receiver.daemon = True
    receiver.start()

    try:
        while not stop_event.is_set():
            try:
                msg_sent = input()
            except EOFError:
                break

            with socket_lock:
                try:
                    c_socket.sendall(msg_sent.encode("ascii"))
                except OSError:
                    stop_event.set()
                    break
    finally:
        shutdown(c_socket, stop_event, socket_lock, msg="")

    sys.exit(0)
