
import socket
import requests
import sys

def check_port(host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    result = sock.connect_ex((host, port))
    if result == 0:
        print(f"✅ Port {port} is OPEN")
        return True
    else:
        print(f"❌ Port {port} is CLOSED or BLOCKED (Error: {result})")
        return False

def test_request(url):
    try:
        print(f"Trying GET {url}...")
        resp = requests.get(url, timeout=5)
        print(f"Response: {resp.status_code}")
        print(resp.text[:200])
    except Exception as e:
        print(f"❌ Request Failed: {e}")

if __name__ == "__main__":
    host = "127.0.0.1"
    port = 8001
    if check_port(host, port):
        test_request(f"http://{host}:{port}/")
