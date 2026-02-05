import socket
import threading

# 1. Configuration
# Load balancer will listen on this port

LB_HOST='127.0.0.1'
LB_PORT=8080

BACKEND_SERVERS=[
    ('127.0.0.1',9001),
    ('127.0.0.1',9002)
]

# Variable to keep track of Round Robin
current_server_index=0

def handle_client(client_socket):
    """
    This function handles a single connection from a browser.
    It acts as a middleman (proxy).
    """

    global current_server_index

    # 1. Pick the next server
    backend_ip, backend_port = BACKEND_SERVERS[current_server_index]

    # 2. Update the index for the next request (0 -> 1 -> 0 -> 1...)
    # The % operator ensures we loop back to the start of the list
    current_server_index = (current_server_index + 1) % len(BACKEND_SERVERS)

    print(f"[*] Routing request to {backend_ip}:{backend_port}")


    # --- B. CONNECT TO BACKEND ---
    try:
        # Create a socket to talk to the backend server
        backend_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        backend_socket.connect((backend_ip, backend_port))

        # --- C. FORWARD DATA (Browser -> LB -> Server) ---
        # Read the request from the browser
        request_data = client_socket.recv(4096)

        if len(request_data) > 0:
            # Send that exact request to the backend server
            backend_socket.sendall(request_data)

            # --- D. RETURN RESPONSE (Server -> LB -> Browser) ---
            # Read the response from the backend server
            response_data = backend_socket.recv(4096)
            # Send that exact response back to the browser
            client_socket.sendall(response_data)

    except Exception as e:
        print(f"[!] Error: {e}")

    finally:
        # --- E. CLEANUP ---
        # Close both connections
        client_socket.close()
        backend_socket.close()



def start_load_balancer():
    # Create the main socket for the Load Balancer
    lb_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Allow reusing the address (fixes "Address already in use" errors)
    lb_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # Bind to our chosen port (8080)
    lb_socket.bind((LB_HOST, LB_PORT))

    # Start listening for connections
    lb_socket.listen(5)
    print(f"--- Load Balancer running on {LB_HOST}:{LB_PORT} ---")


    while True:
        # Accept a new connection from a browser
        client_socket, addr = lb_socket.accept()

        # Start a new thread to handle this client
        # We use threads so multiple people can connect at once
        client_handler = threading.Thread(target=handle_client, args=(client_socket,))
        client_handler.start()


if __name__ == "__main__":
    start_load_balancer()





