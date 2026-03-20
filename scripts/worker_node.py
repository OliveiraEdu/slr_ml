import http.server
import socketserver


def run_worker():
    print("Starting ML worker health check server...")

    class HealthHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status":"healthy"}')

        def log_message(self, format, *args):
            pass

    print("Health check server ready on port 8001...")
    with socketserver.TCPServer(('', 8001), HealthHandler) as httpd:
        httpd.serve_forever()


if __name__ == "__main__":
    run_worker()
