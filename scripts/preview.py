from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import os

root = Path(__file__).resolve().parents[1] / "docs"
os.chdir(root)
print("Previewing http://127.0.0.1:8000/ (Ctrl-C to stop)")
ThreadingHTTPServer(("127.0.0.1", 8000), SimpleHTTPRequestHandler).serve_forever()

