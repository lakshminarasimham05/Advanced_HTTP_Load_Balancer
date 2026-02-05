import socket
import threading
import time
from collections import deque

# --- CONFIGURATION ---
LB_IP = '127.0.0.1'
LB_PORT = 8080

# DDoS Settings
RATE_LIMIT_MAX = 5      
RATE_LIMIT_WINDOW = 10    
BAN_TIME = 30             

# Cache Settings (New!)
CACHE_TIMEOUT = 4  # How long to remember a page (in seconds)

# Backend Servers with WEIGHTS (New!)
# Weight 3 means Server 1 gets 3x more traffic than Server 2
SERVER_LIST = [
    {'host': '127.0.0.1', 'port': 9001, 'weight': 3}, 
    {'host': '127.0.0.1', 'port': 9002, 'weight': 3},
    {'host': '127.0.0.1', 'port': 9003, 'weight': 3}
]

# --- GLOBAL STATE ---
class Backend:
    def __init__(self, host, port, weight):
        self.host = host
        self.port = port
        self.weight = weight
        self.is_alive = True  
        self.request_count = 0

    def get_address(self):
        return (self.host, self.port)

backends = [Backend(s['host'], s['port'], s['weight']) for s in SERVER_LIST]

# Weighted Round Robin Logic: Create a distribution list like [0, 0, 0, 1]
weighted_distribution = []
for index, backend in enumerate(backends):
    for _ in range(backend.weight):
        weighted_distribution.append(index)
current_distribution_index = 0

# Security & Cache Data Stores
client_traffic = {}
banned_ips = {}
response_cache = {} # Format: { "URL": (response_bytes, timestamp) }

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

# --- FEATURE 2: SECURITY (DDoS) ---
def is_rate_limited(client_ip):
    current_time = time.time()
    if client_ip in banned_ips:
        if current_time < banned_ips[client_ip]:
            return True, f"BANNED (Wait {int(banned_ips[client_ip] - current_time)}s)"
        else:
            del banned_ips[client_ip] 

    if client_ip not in client_traffic:
        client_traffic[client_ip] = deque()

    timestamps = client_traffic[client_ip]
    while timestamps and timestamps[0] < current_time - RATE_LIMIT_WINDOW:
        timestamps.popleft()

    if len(timestamps) >= RATE_LIMIT_MAX:
        banned_ips[client_ip] = current_time + BAN_TIME
        print(f"[!!!] SECURITY ALERT: Banning IP {client_ip} for spamming.")
        return True, "Rate limit exceeded."

    timestamps.append(current_time)
    return False, "OK"

# --- FEATURE 3: DASHBOARD ---
def handle_stats_request(client_socket):
    rows = ""
    for b in backends:
        status_color = "green" if b.is_alive else "red"
        status_text = "ONLINE" if b.is_alive else "OFFLINE"
        rows += f"<tr><td>{b.host}:{b.port}</td><td>{b.weight}</td><td style='color:{status_color}'><b>{status_text}</b></td><td>{b.request_count}</td></tr>"

    # Calculate Cache Efficiency
    cache_size = len(response_cache)
    
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
</style>
</head>
<body>
    <h1>🚀 Ultra Load Balancer (Advanced)</h1>
    <h2>Backend Status (Weighted)</h2>
    <table>
        <tr><th>Server</th><th>Weight</th><th>Status</th><th>Total Requests</th></tr>
        {rows}
    </table>
    <h2>⚡ Performance Metrics</h2>
    <p><b>Active Cached Pages:</b> {cache_size}</p>
    <p><b>Cache Timeout:</b> {CACHE_TIMEOUT} seconds</p>
</body>
</html>
"""
    client_socket.sendall(html.encode('utf-8'))
    client_socket.close()

# --- FEATURE 4: CACHING & ROUTING ---
def get_from_cache(url):
    """Returns cached response if available and fresh."""
    current_time = time.time()
    if url in response_cache:
        data, timestamp = response_cache[url]
        if current_time - timestamp < CACHE_TIMEOUT:
            print(f"⚡ [CACHE HIT] Serving {url} from memory.")
            return data
        else:
            print(f"⏳ [CACHE EXPIRED] Removing {url} from memory.")
            del response_cache[url]
    return None

def save_to_cache(url, data):
    """Saves response to memory."""
    response_cache[url] = (data, time.time())

def get_target_server(request_text):
    global current_distribution_index
    
    # L7 Routing Override
    if "GET /app1" in request_text and backends[0].is_alive: return backends[0]
    if "GET /app2" in request_text and backends[1].is_alive: return backends[1]

    # Weighted Round Robin
    # We loop until we find an alive server based on the distribution list
    start_index = current_distribution_index
    while True:
        backend_index = weighted_distribution[current_distribution_index]
        current_distribution_index = (current_distribution_index + 1) % len(weighted_distribution)
        
        if backends[backend_index].is_alive:
            return backends[backend_index]
        
        # Safety break if we looped through everything and nothing is alive
        if current_distribution_index == start_index:
            return None

def handle_client(client_socket, client_address):
    try:
        client_ip = client_address[0]
        
        # 1. READ REQUEST
        client_socket.settimeout(5.0)
        request_data = client_socket.recv(4096)
        if not request_data:
            client_socket.close()
            return
        
        request_text = request_data.decode('utf-8', errors='ignore')

        # 2. FILTERS
        if "GET /favicon.ico" in request_text:
            client_socket.close()
            return
        if "GET /stats" in request_text:
            handle_stats_request(client_socket)
            return

        # 3. SECURITY CHECK
        is_blocked, reason = is_rate_limited(client_ip)
        if is_blocked:
            error_msg = f"HTTP/1.1 429 Too Many Requests\n\n{reason}".encode('utf-8')
            client_socket.sendall(error_msg)
            client_socket.close()
            return

        # 4. CACHE CHECK (New!)
        # We extract the first line (e.g., "GET / HTTP/1.1") to use as the cache key
        request_line = request_text.splitlines()[0]
        cached_response = get_from_cache(request_line)
        if cached_response:
            client_socket.sendall(cached_response)
            client_socket.close()
            return

        # 5. GET SERVER & FORWARD
        backend = get_target_server(request_text)
        if not backend:
            client_socket.sendall(b"HTTP/1.1 503 Service Unavailable\n\nNo servers available!")
            client_socket.close()
            return

        backend.request_count += 1
        print(f"[*] [CACHE MISS] Fetching from Server {backend.port} (Weight {backend.weight})")

        try:
            backend_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            backend_socket.connect(backend.get_address())
            backend_socket.sendall(request_data)
            
            # Collect full response to cache it
            full_response = b""
            while True:
                chunk = backend_socket.recv(4096)
                if not chunk: break
                full_response += chunk
            
            # Send to client
            client_socket.sendall(full_response)
            
            # Save to Cache
            save_to_cache(request_line, full_response)
            
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
    
    print(f"--- Ultra Load Balancer running on {LB_IP}:{LB_PORT} ---")
    print(f"--- Mode: Weighted Round Robin (Weights: {SERVER_LIST[0]['weight']} vs {SERVER_LIST[1]['weight']}) ---")
    print(f"--- Features: Caching, L7 Routing, DDoS Protection ---")

    while True:
        try:
            client, addr = lb_socket.accept()
            client_handler = threading.Thread(target=handle_client, args=(client, addr))
            client_handler.start()
        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    start_lb()