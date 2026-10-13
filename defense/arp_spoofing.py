#!/usr/bin/env python3
import argparse
import subprocess
import socket
import struct
from scapy.all import ARP, Ether, srp, get_if_hwaddr,get_if_addr

def discover_hosts(subnet: str, iface: str) -> dict:
    """ARP scan the subnet, return {ip: mac}"""
    print(f" Scanning {subnet} on interface {iface}...")
    ans, _ = srp(
        Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=subnet),
        iface=iface,
        timeout=3,
        verbose=False
    )
    hosts = {}
    for _, rcv in ans:
        hosts[rcv.psrc] = rcv.hwsrc
        print(f"    Found {rcv.psrc} -> {rcv.hwsrc}")
    return hosts

def build_nftables_ruleset(hosts: dict, iface: str) -> str:
    rules = []
    for ip, mac in hosts.items():
        rules.append(
            f"        ether saddr {mac} arp saddr ip {ip} accept"
        )
    rules_str = "\n".join(rules)

    return f"""table netdev filter {{
    chain arp_in {{
        type filter hook ingress device "{iface}" priority 0; policy accept;

        # Only process ARP packets
        ether type != arp accept

        # Auto-generated ARP whitelist
{rules_str}

        # Drop all spoofed ARP
        drop
    }}
}}
"""

def apply_nftables(ruleset: str, iface: str):
    config_path = "/tmp/arp_whitelist.nft"
    with open(config_path, "w") as f:
        f.write(ruleset)

    subprocess.run(["nft", "-f", config_path], check=True)
    print(" nftables ruleset applied successfully")

def main():
    parser = argparse.ArgumentParser(description="Auto ARP whitelist via nftables")
    parser.add_argument("--iface",  required=True, help="Interface facing the protected subnet (e.g. r1-eth12)")
    parser.add_argument("--subnet", required=True, help="Subnet to scan (e.g. 10.12.0.0/24)")
    args = parser.parse_args()

    # Step 1 — discover legitimate hosts
    hosts = discover_hosts(args.subnet, args.iface)

    if not hosts:
        return

    # Step 2 — add ourselves to the whitelist
    our_mac = get_if_hwaddr(args.iface)
    our_ip  = get_if_addr(args.iface)
    hosts[our_ip] = our_mac
    print(f"    Self {our_ip} -> {our_mac}")

    # Step 3 — build and show ruleset
    ruleset = build_nftables_ruleset(hosts,args.iface)
    print("\n Generated ruleset:")
    print(ruleset)

    # Step 4 — apply it
    apply_nftables(ruleset,args.iface)

if __name__ == "__main__":
    main()