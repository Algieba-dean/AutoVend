#!/usr/bin/env python
"""
Simple HTTP server for the AutoVend frontend test
Run this script to serve the frontend test files
"""

import http.server
import socketserver
import os

# Configuration
PORT = 8000
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

def main():
    """Run the HTTP server"""
    handler = Handler
    
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        print(f"Frontend test server running at: http://localhost:{PORT}")
        print(f"Please ensure the backend API server is running at http://localhost:5000")
        print("Press Ctrl+C to stop the server")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped")

if __name__ == "__main__":
    main() 