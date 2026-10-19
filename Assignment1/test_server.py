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

            # Extract submitted name and email
            name = form_data.get("name", [""])[0]
            email = form_data.get("email", [""])[0]

            # Check if required fields are missing
            if not name or not email:
                self.send_response(400)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(b"Missing required fields")
                return

            # Check basic email format
            if "@" not in email or "." not in email.split("@")[-1]:
                self.send_response(400)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(b"Invalid email")
                return

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