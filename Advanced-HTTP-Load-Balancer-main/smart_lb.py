import socket
import threading
import time
from collections import deque

# --- CONFIGURATION ---
LB_IP = '127.0.0.1'
LB_PORT = 8080

# DDoS Protection Settings
RATE_LIMIT_MAX = 5       # Max requests allowed
RATE_LIMIT_WINDOW = 10    # ...in this many seconds
BAN_TIME = 30             # Time to ban an IP if they exceed limit

# List of backend servers
SERVER_LIST = [
    {'host': '127.0.0.1', 'port': 9001}, # Server 1 (Index 0)
    {'host': '127.0.0.1', 'port': 9002}  # Server 2 (Index 1)
]

# --- GLOBAL STATE ---
class Backend:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.is_alive = True  
        self.request_count = 0

    def get_address(self):
        return (self.host, self.port)

backends = [Backend(s['host'], s['port']) for s in SERVER_LIST]
current_server_index = 0

# Security: Dictionary to track client requests { '127.0.0.1': [timestamp1, timestamp2] }
client_traffic = {}
# Security: Dictionary to track banned IPs { '127.0.0.1': ban_expiry_timestamp }
banned_ips = {}

# --- FEATURE 1: HEALTH CHECKS ---
def health_check_loop():
    while True:
        for backend in backends:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2) 
            try:
                sock.connect(backend.get_address())
                if not backend.is_alive:
                    print(f"[+] Server {backend.port} is BACK ONLINE.")
                backend.is_alive = True
                sock.close()
            except:
                if backend.is_alive:
                    print(f"[-] Server {backend.port} is DOWN/DEAD.")
                backend.is_alive = False
        time.sleep(5) 

# --- FEATURE 2: SECURITY (DDoS PROTECTION) ---
def is_rate_limited(client_ip):
    current_time = time.time()
    
    # 1. Check if already banned
    if client_ip in banned_ips:
        if current_time < banned_ips[client_ip]:
            return True, f"BANNED (Wait {int(banned_ips[client_ip] - current_time)}s)"
        else:
            del banned_ips[client_ip] # Ban expired

    # 2. Initialize tracking for new IP
    if client_ip not in client_traffic:
        client_traffic[client_ip] = deque()

    # 3. Remove requests older than the window (clean up history)
    timestamps = client_traffic[client_ip]
    while timestamps and timestamps[0] < current_time - RATE_LIMIT_WINDOW:
        timestamps.popleft()

    # 4. Check count
    if len(timestamps) >= RATE_LIMIT_MAX:
        banned_ips[client_ip] = current_time + BAN_TIME
        print(f"[!!!] SECURITY ALERT: Banning IP {client_ip} for spamming.")
        return True, "Rate limit exceeded. You are banned for 30s."

    # 5. Record this request
    timestamps.append(current_time)
    return False, "OK"

# --- FEATURE 3: DASHBOARD ---
def handle_stats_request(client_socket):
    rows = ""
    for b in backends:
        status_color = "green" if b.is_alive else "red"
        status_text = "ONLINE" if b.is_alive else "OFFLINE"
        rows += f"<tr><td>{b.host}:{b.port}</td><td style='color:{status_color}'><b>{status_text}</b></td><td>{b.request_count}</td></tr>"

    banned_rows = ""
    for ip, expiry in banned_ips.items():
        remaining = int(expiry - time.time())
        banned_rows += f"<tr><td style='color:red'>{ip}</td><td>{remaining} seconds</td></tr>"

    html = f"""HTTP/1.1 200 OK
Content-Type: text/html; charset=utf-8
Connection: close

<html>
<head><title>LB Dashboard</title>
<meta http-equiv="refresh" content="3">
<style>
    body {{ font-family: sans-serif; padding: 20px; }}
    table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
    th {{ background-color: #f2f2f2; }}
    h2 {{ border-bottom: 2px solid #333; }}
</style>
</head>
<body>
    <h1>🛡️ Enterprise Load Balancer</h1>
    
    <h2>Backend Status</h2>
    <table>
        <tr><th>Server Address</th><th>Status</th><th>Total Requests</th></tr>
        {rows}
    </table>

    <h2>🚫 Security Logs (Banned IPs)</h2>
    <table>
        <tr><th>IP Address</th><th>Ban Remaining</th></tr>
        {banned_rows}
    </table>
</body>
</html>
"""
    client_socket.sendall(html.encode('utf-8'))
    client_socket.close()

# --- FEATURE 4: LAYER 7 ROUTING ---
def get_target_server(request_text):
    """
    Decides which server to use based on the URL path.
    """
    global current_server_index
    
    # Rule 1: If path starts with /app1, FORCE Server 1
    if "GET /app1" in request_text:
        print("[L7 Routing] Path is /app1 -> Routing to Server 1")
        if backends[0].is_alive: return backends[0]
    
    # Rule 2: If path starts with /app2, FORCE Server 2
    if "GET /app2" in request_text:
        print("[L7 Routing] Path is /app2 -> Routing to Server 2")
        if backends[1].is_alive: return backends[1]

    # Rule 3: Default to Round Robin for everything else
    for _ in range(len(backends)):
        backend = backends[current_server_index]
        current_server_index = (current_server_index + 1) % len(backends)
        if backend.is_alive:
            return backend
    return None

def handle_client(client_socket, client_address):
    try:
        client_ip = client_address[0]
        
        # 1. READ REQUEST FIRST (So we know what they want)
        client_socket.settimeout(5.0)
        request_data = client_socket.recv(4096)
        if not request_data:
            client_socket.close()
            return
        
        request_text = request_data.decode('utf-8', errors='ignore')

        # 2. IGNORE NOISE (Favicon) - Don't count this towards limit
        if "GET /favicon.ico" in request_text:
            client_socket.close()
            return

        # 3. WHITELIST DASHBOARD - Admins shouldn't get banned
        if "GET /stats" in request_text:
            handle_stats_request(client_socket)
            return

        # 4. CHECK SECURITY (Only count actual traffic to servers)
        # We moved this check AFTER the whitelist!
        is_blocked, reason = is_rate_limited(client_ip)
        if is_blocked:
            print(f"[SECURITY] Blocking {client_ip} due to rate limit.")
            error_msg = f"HTTP/1.1 429 Too Many Requests\nContent-Type: text/plain\n\n{reason}".encode('utf-8')
            client_socket.sendall(error_msg)
            client_socket.close()
            return

        # 5. GET SERVER (Layer 7 Routing)
        backend = get_target_server(request_text)
        
        if not backend:
            client_socket.sendall(b"HTTP/1.1 503 Service Unavailable\n\nNo servers available!")
            client_socket.close()
            return

        backend.request_count += 1
        
        # 6. FORWARD DATA
        try:
            backend_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            backend_socket.connect(backend.get_address())
            # Send the data we ALREADY read
            backend_socket.sendall(request_data)
            
            while True:
                response_data = backend_socket.recv(4096)
                if not response_data: break
                client_socket.sendall(response_data)
            backend_socket.close()
        except Exception as e:
            print(f"[!] Backend Error: {e}")

    except Exception as e:
        pass
    finally:
        client_socket.close()

def start_lb():
    t = threading.Thread(target=health_check_loop)
    t.daemon = True 
    t.start()

    lb_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    lb_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    lb_socket.bind((LB_IP, LB_PORT))
    lb_socket.listen(5)
    
    print(f"--- Enterprise Load Balancer running on {LB_IP}:{LB_PORT} ---")
    print(f"--- Dashboard: http://{LB_IP}:{LB_PORT}/stats ---")
    print(f"--- Features: Round Robin, L7 Path Routing, DDoS Protection ---")

    while True:
        try:
            client, addr = lb_socket.accept()
            # Pass the address (IP) to the handler so we can rate limit it
            client_handler = threading.Thread(target=handle_client, args=(client, addr))
            client_handler.start()
        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    start_lb()