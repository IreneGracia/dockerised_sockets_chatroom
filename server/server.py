import socket
from threading import Thread, Event, Lock
import signal
import sys
import os


PORT = int(os.getenv("PORT", "8000"))
ADDRESS = os.getenv("ADDRESS", "")
MAX_CONNECTIONS = 4
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKUP_PATH = os.getenv("BACKUP_PATH", os.path.join(BASE_DIR, "Backup.txt"))


class Server(Thread):
    def __init__(self, name: str, address: str, port: int, c_socket: socket.socket):
        super().__init__(name=name)
        self.address = address
        self.port = port
        self.c_socket = c_socket

    def run(self):
        while True:
            try:
                msg = self.c_socket.recv(1024)
            except socket.error:
                msg = b""

            if msg == b"":
                # remove from client map and snapshot recipients
                with client_log_lock:
                    username = client_log.get(self.c_socket)
                    if username is None:
                        break  # already removed
                    del client_log[self.c_socket]
                    recipients = [s for s in client_log.keys()]

                log_print(f'Client "{username}" with address {self.address} disconnected.')

                try:
                    self.c_socket.close()
                except OSError:
                    pass

                left_msg = f"{username} left the chat!"
                log_only(left_msg)

                for socket_item in recipients:
                    try:
                        socket_item.sendall(left_msg.encode("ascii"))
                    except socket.error:
                        pass
                break

            msg_text = msg.decode("ascii")

            with client_log_lock:
                recipients = [s for s in client_log.keys() if s != self.c_socket]
                sender_name = client_log.get(self.c_socket)

            outbound = f"{sender_name} says: {msg_text}"
            log_only(outbound)

            for socket_item in recipients:
                try:
                    socket_item.sendall(outbound.encode("ascii"))
                except socket.error:
                    pass


class BackupThread(Thread):
    def __init__(self, stop_event: Event, interval_seconds: int = 5):
        super().__init__(daemon=True)
        self.stop_event = stop_event
        self.interval_seconds = interval_seconds

    def run(self):
        while not self.stop_event.wait(self.interval_seconds):
            try:
                update_backup()
            except Exception:
                pass


def signal_handler(signum, frame):
    stop_event.set()
    try:
        s_socket.close()  # unblocks accept()
    except OSError:
        pass
    try:
        update_backup()
    except Exception:
        pass


# Open or create backup file
def create_backup():
    os.makedirs(os.path.dirname(BACKUP_PATH) or ".", exist_ok=True)
    with open(BACKUP_PATH, "w", encoding="utf-8"):
        pass


def update_backup():
    with log_lock:
        if not conversation_log:
            return
        to_write = conversation_log[:]
        conversation_log.clear()

    with open(BACKUP_PATH, "w", encoding="utf-8") as f:
        for line in to_write:
            f.write(line + "\n")



def record_line(message: str):
    with log_lock:
        conversation_log.append(message)


def log_print(message: str):
    #Server terminal prints: server start, client connect, client disconnect
    record_line(message)
    print(message, flush= True)


def log_only(message: str):
    #Record without printing: chat messages, join and leave notifications
    record_line(message)


if __name__ == "__main__":
    s_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s_socket.bind((ADDRESS, PORT))
    s_socket.listen(MAX_CONNECTIONS)

    conversation_log = []
    log_lock = Lock()
    client_log = {}
    client_log_lock = Lock()

    create_backup()

    stop_event = Event()
    BackupThread(stop_event, 30).start()

    # catching both SIGINT and SIGTERM fully covers local and dockerised runs
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    log_print(f"Started server on, {socket.gethostname()}, and port, {PORT}")

    while not stop_event.is_set():
        try:
            c_socket, address = s_socket.accept()
        except OSError:
            break

        log_print(f"Client on address {address} connected")

        try:
            username = c_socket.recv(1024).decode("ascii")
        except socket.error:
            try:
                c_socket.close()
            except OSError:
                pass
            continue

        # add client + snapshot recipients
        with client_log_lock:
            client_log[c_socket] = str(username)
            current_usernames = list(client_log.values())
            recipients = [s for s in client_log.keys() if s != c_socket]

        joined_msg = f"{username} joined the chat!"
        log_only(joined_msg)

        for socket_item in recipients:
            try:
                socket_item.sendall(joined_msg.encode("ascii"))
            except socket.error:
                pass

        # send online users list back to the new client
        try:
            c_socket.send(", ".join(current_usernames).encode("ascii"))
        except socket.error:
            with client_log_lock:
                client_log.pop(c_socket, None)
            try:
                c_socket.close()
            except OSError:
                pass
            continue

        Server(name=username, address=address, port=PORT, c_socket=c_socket).start()

    # shutdown of server, copy sockets under lock so other threads don't modify client_log simultaneously
    with client_log_lock:
        closing_sockets = list(client_log.keys())
        client_log.clear()

    for client_socket in closing_sockets:
        try:
            client_socket.close()
        except OSError:
            pass

    sys.exit(0)
