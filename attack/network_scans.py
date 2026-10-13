from scapy.all import IP, TCP, sr1, send

TARGET_IPS = ["10.12.0.10", "10.12.0.20", "10.12.0.30", "10.12.0.40"]
PORTS = [20,21, 22, 53, 80, 443, 3306, 5353, 8080]

def try_connect(ip, port):
    syn = IP(dst=ip)/TCP(dport=port, flags="S")
    response = sr1(syn, timeout=1, verbose=0)

    if response is None:
        print("Filtered / no response")
    elif response.haslayer(TCP):
        if response[TCP].flags == 0x12:  # SYN-ACK
            print("Port open")

            # Send RST to tear down
            rst = IP(dst=ip)/TCP(dport=port, flags="R",
                                    seq=response.ack)
            send(rst, verbose=0)

        elif response[TCP].flags == 0x14:
            pass

def run():
    print("=" * 50)
    print("Port Scanner - DMZ Servers")
    print(f"Targets: {TARGET_IPS}")
    print(f"Ports: {PORTS}")
    print("=" * 50)

    for ip in TARGET_IPS:
        print(f"\nScanning {ip}...")
        for port in PORTS:
            print(f"  [{ip}:{port}] ... ", end="", flush=True)
            success = try_connect(ip, port)

    print("\nFinished")

if __name__ == "__main__":
    run()