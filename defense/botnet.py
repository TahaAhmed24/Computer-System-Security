#!/usr/bin/env python3
import subprocess, sys
from scapy.all import get_if_list

TRUSTED_TCP = "{ 21, 22, 80 }"
TRUSTED_UDP = "{ 5353, 123 }"
RATE_LIMIT  = 10

def run_nft(cmd):
    subprocess.run(f"nft {cmd}", shell=True)

# Rules are inserted in reverse desired order (each insert goes to position 1)

# Inserted first -> ends up last (rule 3): drop anything unmatched
run_nft("insert rule inet filter forward "
        "ip saddr 10.1.0.0/24 ip daddr 10.12.0.0/24 "
        "ip protocol { tcp, udp } ct state new drop")

# Inserted second -> ends up at rule 2: accept trusted UDP
run_nft(f"insert rule inet filter forward "
        f"ip saddr 10.1.0.0/24 ip daddr 10.12.0.0/24 udp dport {TRUSTED_UDP} accept")

# Inserted last -> ends up at rule 1: accept trusted TCP
run_nft(f"insert rule inet filter forward "
        f"ip saddr 10.1.0.0/24 ip daddr 10.12.0.0/24 tcp dport {TRUSTED_TCP} accept")

# Additional: rate-limit new HTTP connections
run_nft(f"insert rule inet filter forward "
        f"ip saddr 10.1.0.0/24 ip daddr 10.12.0.0/24 "
        f"tcp dport 80 ct state new limit rate over {RATE_LIMIT}/minute drop")