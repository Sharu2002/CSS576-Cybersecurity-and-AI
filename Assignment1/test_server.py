from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import json

class TestHandler(BaseHTTPRequestHandler):

    # Handle GET requests
    def do_GET(self):

        path = urlparse(self.path).path

        if path == "/":
            with open("sample.html", "r") as file:
                html = file.read()

            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(html.encode())

        else:
            self.send_error(404, "Page not found")

    # Handle POST requests
    def do_POST(self):

        path = urlparse(self.path).path

        if path == "/subscribe":

            length = int(self.headers.get("Content-Length", 0))

            body = self.rfile.read(length).decode("utf-8")

            form_data = parse_qs(body)

            print("\nReceived form submission:")
            print(json.dumps(form_data, indent=4))

            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()

            self.wfile.write(
                b"Subscription received successfully"
            )

        else:
            self.send_error(404, "Page not found")


server = HTTPServer(("127.0.0.1", 8000), TestHandler)

print("Test server running at http://localhost:8000")

server.serve_forever()