import socket
import threading
import msvcrt
import traceback

HOST = "127.0.0.1"
PORT = 5000

done = threading.Event()

def send_keys(sock):
    while True:
        ch = msvcrt.getwch()
        if done.is_set():
            return
        if ch in ("\x00", "\xe0"):
            msvcrt.getwch()
            continue
        if ch == "\r":
            ch = "\n"
        try:
            sock.sendall(bytes([ord(ch) & 0xFF]))
        except OSError:
            pass

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
    server.connect((HOST, PORT))

    keyThread = threading.Thread(target=send_keys, args=(server,), daemon=True)
    keyThread.start()

    try:
        while True:
            data = server.recv(1024)
            if not data:
                break

            print(data.decode("utf-8", errors="replace"), end="", flush=True)
    except OSError:
        pass
    except Exception:
        traceback.print_exc()

done.set()
print("\nDisconnected. Press any key to close.", flush=True)
keyThread.join()