import socket
import time
import random

TARGET_IP = "10.12.0.40"
TARGET_SSH_PORT = 22
TARGET_FTP_PORT = 21
DELAY = 1.0

"""List of the tested credentials"""
CREDENTIALS = [
    ("root", "root"),                                                                                                                                                                                                                                                                      
    ("admin", "admin"),                                                                                                                                                                                                                                                                    
    ("root", "toor"),                                                                                                                                                                                                                                                                      
    ("admin", "password"),
    ("user", "1234"),
]

def try_connect():
    """Attempt TCP connection to SSH port."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)

    try:
        s.connect((TARGET_IP, TARGET_SSH_PORT))
        return True
    except Exception:
        return False
    finally:
        s.close()

def run():
    print("=" * 50)
    print(f"Target: {TARGET_IP}:{TARGET_SSH_PORT}")
    print(f"Attempts: {len(CREDENTIALS)}")
    print("=" * 50)

    for i, (user, pwd) in enumerate(CREDENTIALS, 1):
        print(f"[{i:02d}] Trying {user}:{pwd} ... ", end="", flush=True)

        success = try_connect()

        if success:
            print("CONNECTED ")
        else:
            print("FAILED")

        time.sleep(DELAY)

    print("\n Done. Check tcpdump/Wireshark.")

if __name__ == "__main__":
    run()