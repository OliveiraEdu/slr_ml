import http.server
import socketserver
from src.ml.classifier import SciBERTClassifier, BackendType

def run_worker():
    print("Loading SciBERT with ctranslate2...")
    try:
        # Initialize your classifier
        c = SciBERTClassifier(backend=BackendType.CTRANSFORMATE2)
        print("SciBERT with ctranslate2 ready")
    except Exception as e:
        print(f"Failed to load model: {e}")
        exit(1)

    class HealthHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status":"healthy"}')
        def log_message(self, format, *args):
            pass

    print("Starting health check server on port 8001...")
    with socketserver.TCPServer(('', 8001), HealthHandler) as httpd:
        httpd.serve_forever()

if __name__ == "__main__":
    run_worker()