import socket
import threading
import select
import sys
import time

# Listen
LISTENING_ADDR = "127.0.0.1"
if sys.argv[1:]:
    LISTENING_PORT = int(sys.argv[1])
else:
    LISTENING_PORT = 10015

# Password header value (optional)
PASS = ""

# CONST
BUFLEN = 4096 * 4
TIMEOUT = 60
DEFAULT_HOST = "127.0.0.1:143"
RESPONSE = (
    b"HTTP/1.1 101 LunaticTunneling\r\n"
    b"Upgrade: websocket\r\n"
    b"Connection: Upgrade\r\n"
    b"Sec-WebSocket-Accept: foo\r\n\r\n"
)


class Server(threading.Thread):
    def __init__(self, host, port):
        super().__init__()
        self.running = False
        self.host = host
        self.port = port
        self.threads = []
        self.threads_lock = threading.Lock()
        self.log_lock = threading.Lock()

    def run(self):
        self.soc = socket.socket(socket.AF_INET)
        self.soc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.soc.settimeout(2)
        self.soc.bind((self.host, int(self.port)))
        self.soc.listen(0)
        self.running = True

        try:
            while self.running:
                try:
                    client, addr = self.soc.accept()
                    client.setblocking(True)
                except socket.timeout:
                    continue

                conn = ConnectionHandler(client, self, addr)
                conn.start()
                self.add_conn(conn)
        finally:
            self.running = False
            self.soc.close()

    def print_log(self, log):
        with self.log_lock:
            print(log)

    def add_conn(self, conn):
        with self.threads_lock:
            if self.running:
                self.threads.append(conn)

    def remove_conn(self, conn):
        with self.threads_lock:
            if conn in self.threads:
                self.threads.remove(conn)

    def close(self):
        self.running = False
        with self.threads_lock:
            threads = list(self.threads)
        for conn in threads:
            conn.close()


class ConnectionHandler(threading.Thread):
    def __init__(self, soc_client, server, addr):
        super().__init__()
        self.client_closed = False
        self.target_closed = True
        self.client = soc_client
        self.client_buffer = ""
        self.server = server
        self.log = "Connection: " + str(addr)

    def close(self):
        try:
            if not self.client_closed:
                self.client.shutdown(socket.SHUT_RDWR)
                self.client.close()
        except Exception:
            pass
        finally:
            self.client_closed = True

        try:
            if not self.target_closed:
                self.target.shutdown(socket.SHUT_RDWR)
                self.target.close()
        except Exception:
            pass
        finally:
            self.target_closed = True

    def run(self):
        try:
            initial = self.client.recv(BUFLEN)
            self.client_buffer = initial.decode("utf-8", errors="ignore")

            host_port = self.find_header(self.client_buffer, "X-Real-Host")
            if host_port == "":
                host_port = DEFAULT_HOST

            split = self.find_header(self.client_buffer, "X-Split")
            if split != "":
                extra = self.client.recv(BUFLEN)
                initial += extra
                self.client_buffer = initial.decode("utf-8", errors="ignore")

            # Keep any bytes that arrive after the HTTP upgrade headers.
            # Some clients send SSH banner/KEX in the same packet as upgrade.
            payload = b""
            head_end = initial.rfind(b"\r\n\r\n")
            if head_end != -1:
                payload = initial[head_end + 4 :]

            if host_port != "":
                passwd = self.find_header(self.client_buffer, "X-Pass")

                if len(PASS) != 0 and passwd == PASS:
                    self.method_connect(host_port, payload)
                elif len(PASS) != 0 and passwd != PASS:
                    self.client.sendall(b"HTTP/1.1 400 WrongPass!\r\n\r\n")
                elif host_port.startswith("127.0.0.1") or host_port.startswith("localhost"):
                    self.method_connect(host_port, payload)
                else:
                    self.client.sendall(b"HTTP/1.1 403 Forbidden!\r\n\r\n")
            else:
                print("- No X-Real-Host!")
                self.client.sendall(b"HTTP/1.1 400 NoXRealHost!\r\n\r\n")

        except Exception as exc:
            self.log += " - error: " + str(exc)
            self.server.print_log(self.log)
        finally:
            self.close()
            self.server.remove_conn(self)

    def find_header(self, head, header):
        aux = head.find(header + ": ")
        if aux == -1:
            return ""

        aux = head.find(":", aux)
        head = head[aux + 2 :]
        aux = head.find("\r\n")
        if aux == -1:
            return ""

        return head[:aux]

    def connect_target(self, host):
        idx = host.find(":")
        if idx != -1:
            port = int(host[idx + 1 :])
            host = host[:idx]
        else:
            port = LISTENING_PORT

        (soc_family, soc_type, proto, _, address) = socket.getaddrinfo(host, port)[0]
        self.target = socket.socket(soc_family, soc_type, proto)
        self.target_closed = False
        self.target.connect(address)

    def method_connect(self, path, payload=b""):
        self.log += " - CONNECT " + path
        self.connect_target(path)
        self.client.sendall(RESPONSE)
        self.client_buffer = ""
        if payload:
            self.target.sendall(payload)
        self.server.print_log(self.log)
        self.do_connect()

    def do_connect(self):
        sockets = [self.client, self.target]
        count = 0
        error = False

        while True:
            count += 1
            recv, _, err = select.select(sockets, [], sockets, 3)
            if err:
                error = True

            if recv:
                for incoming in recv:
                    try:
                        data = incoming.recv(BUFLEN)
                        if data:
                            if incoming is self.target:
                                self.client.sendall(data)
                            else:
                                while data:
                                    sent = self.target.send(data)
                                    data = data[sent:]
                            count = 0
                        else:
                            error = True
                            break
                    except Exception:
                        error = True
                        break

            if count >= TIMEOUT:
                error = True

            if error:
                break


def main(host=LISTENING_ADDR, port=LISTENING_PORT):
    print("\n:-------PythonProxy-------:\n")
    print("Listening addr: " + str(host))
    print("Listening port: " + str(port) + "\n")
    print(":-------------------------:\n")

    server = Server(host, port)
    server.start()

    while True:
        try:
            time.sleep(2)
        except KeyboardInterrupt:
            print("Stopping...")
            server.close()
            break


if __name__ == "__main__":
    main()
