from http.server import BaseHTTPRequestHandler, HTTPServer

# Define the port we want to listen on
PORT = 9001
SERVER_NAME = "Server 1"

class MyServerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Prepare the message first so we can measure its length
        message = f"Hello! This is a response from {SERVER_NAME} (running on port {PORT})."
        # Convert to bytes immediately to get accurate length
        message_bytes = message.encode('utf-8')

        # 1. Send the HTTP 200 OK response status
        self.send_response(200)

        # 2. Send the HTTP headers
        self.send_header('Content-type', 'text/plain')
        # CRITICAL FIX: Tell the browser exactly how long the data is
        self.send_header('Content-Length', len(message_bytes))
        self.end_headers()

        # 3. Write the response body
        self.wfile.write(message_bytes)

if __name__ == "__main__":
    try:
        server_address = ('', PORT)
        httpd = HTTPServer(server_address, MyServerHandler)
        print(f"--- Starting {SERVER_NAME} on port {PORT}... ---")
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n--- Stopping server... ---")
        httpd.socket.close()