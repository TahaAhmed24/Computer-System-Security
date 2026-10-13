# Network Attacks

## Project Description

## Setup

Make all attack and defense scripts executable:

```bash
sudo chmod +x attack/*.py attack/botnet/*.py defense/*.py defense/*.sh
```

Start the topology (opens the Mininet CLI):

```bash
sudo -E python3 topo.py
```

Apply the basic routing/firewall rules before running any attack or defense:

```bash
mininet> source basic_routing.sh
```

This sets up the default forwarding policy on `r1` and `r2` (drop-by-default with stateful tracking and LAN egress allowed) that all defenses build on top of.

## Network Scans
### Attack Description

Network scans are information gathering attacks. They are used to find a vulnerable host and discover the network topology. 
You can conduct this attack in several ways:
- TCP port scan with regular connections
- TCP port scan with SYN packets only
- TCP port scan: Xmas-tree scan

### Attack Script
TCP port scan with SYN packets only

```bash
internet python3 attack/network_scans.py
```
### Mitigations
block incoming network traffic based on thresholds. Since order is important in nftable rulelists you need to add the new rule before the default rules. 

```bash
source defense/network_scans.sh
```

## SSH/FTP Brute-force attack

### Attack Description
SSH/brute force attacks are automated attempts to gain unauthrized access to a server by systematically trying large numbers of username/password combinations until one works. 
An attacker will send rapid fire login attempt at the SSH (port 22) or FTP (port 21) service.

Attackers typically rely on:
- Wordlists and leaked credential databases (e.g. RockYou, HaveIBeenPwned dumps) rather than purely random guesses.
- Common default credentials for known operating systems, services, and devices.
- Username enumeration — some services reveal valid usernames through response timing differences, even without a successful login.

### Attack Script

The attack script below simulates the connection phase of a brute-force attempt (TCP handshake to the target port). It does not implement a real authentication protocol such as SSH or FTP — it confirms reachability and generates the traffic pattern visible in packet captures.

This is a simulation because the Mininet environment does not have a configured SSH server with real credentials to test against. The nftables rate-limiting defense triggers on new TCP connections regardless, so the simulation is sufficient to demonstrate and validate the mitigation. A real implementation would use a library such as `paramiko` (SSH) or `ftplib` (FTP) to perform actual authentication attempts with each credential pair.

```bash
internet python3 attack/ssh_brute_force.py
```
### Mitigations Description

To protect against this kind of attack, we introduce rate limiting per source IP on both the SSH and FTP ports. This uses stateful, metered nftables rules that track per-IP connection rates via a dynamic table (meter).

How the rules work:
- Only new connections (`ct state new`) are counted — established sessions are unaffected.
- Each source IP is tracked independently in the meter table with a 60-second sliding window.
- If a source IP exceeds 10 new connections per minute, all further attempts from that IP are dropped for the remainder of the window.

Known limitation: rate limiting alone does not block slow-and-low attacks. An attacker sending 9 attempts per minute indefinitely would never be blocked. For stronger protection, consider complementary controls:
- Fail2ban — permanently bans IPs after a configurable threshold of failed authentication attempts.
- SSH key authentication — disabling password-based login entirely eliminates the attack surface.
- IP allowlisting — restricting SSH/FTP access to known trusted IP ranges.

### Mitigation Script
```bash
source defense/ssh_brute_force.sh
```

## (Reflected) DDoS

### Attack Description

A DNS reflection/amplification DDoS attack exploits open DNS resolvers to flood a victim with traffic the victim never requested. The attacker spoofs the victim's IP address as the source, then sends DNS queries to a DNS server. The server, unaware of the spoofing, sends its (often much larger) response directly to the victim.

The amplification factor comes from using query type `ANY` (qtype=255): a small query (~40 bytes) can trigger a response of several hundred bytes. By sending thousands of such spoofed queries, the attacker overwhelms the victim's bandwidth and/or CPU without needing equivalent outbound capacity.

In this topology:
- **Attacker**: `internet` (10.2.0.2) — spoofs the victim's IP as the source
- **Reflector**: `dns` (10.12.0.20) — the DNS server that receives the spoofed queries and reflects responses
- **Victim**: `ws3` (10.1.0.3) — receives the amplified DNS responses it never requested

Random subdomains are generated per query to bypass DNS caching, ensuring the server must process every request.

### Attack Script

```bash
internet python3 attack/reflected_ddos.py
```

### Mitigations Description

The root enabler of this attack is **IP spoofing**: the attacker can forge the source address because router `r2` does not validate that packets arriving from the internet actually originate from internet-side addresses. The mitigation applies **ingress filtering (BCP38)**: any packet arriving on the external interface (`r2-eth0`) that claims to come from an internal subnet (`10.1.0.0/24` or `10.12.0.0/24`) is immediately dropped.

How the rule works:
- The `iif "r2-eth0"` condition matches only traffic entering from the internet-facing interface.
- The `ip saddr { 10.1.0.0/24, 10.12.0.0/24 }` condition catches packets that spoof internal source addresses.
- The rule is inserted at the top of the `forward` chain (`nft insert`) so it takes priority over permissive rules added later.

This does not prevent all DDoS techniques, but it eliminates the spoofing precondition required for reflection attacks. Complementary controls include:
- **DNS response-rate limiting (RRL)** on the DNS server — limits how many responses per second the server sends to any single destination.
- **Firewall rate limiting on UDP/53** — drops excessive DNS response traffic heading toward the LAN.
- **Disabling `ANY` query type** on the resolver — removes the primary amplification vector.

### Mitigation Script

```bash
source defense/reflected_ddos.sh
```

## ARP cache poisoning

### Attack Description
ARP Spoofing is a Layer 2 attack where a malicious host sends unsolicited ARP replies to poison the ARP cache of other hosts on the same subnet, associating its own MAC address with a legitimate IP. This positions the attacker as a Man-in-the-Middle, intercepting traffic between two victims. Since ARP has no authentication mechanism, hosts blindly accept and update their cache with any received reply.
### Attack Script
```bash
http python3 attack/arp_spoofing.py
```
### Mitigation Description
The mitigation uses a two-layer defense running on each router. First, a Python script performs an ARP scan at startup to discover all legitimate IP→MAC mappings and generates nftables netdev ingress rules that whitelist only those bindings, dropping any ARP packet from an unknown or mismatched source. Second, the discovered mappings are written as permanent entries (nud permanent) in the kernel ARP table, so even if a spoofed packet somehow bypassed the filter, the kernel would refuse to overwrite the locked entries.
### Mitigation Script
```
r1 python3 defense/arp_spoofing.py --iface r1-eth12 --subnet 10.12.0.0/24
r2 python3 defense/arp_spoofing.py --iface r2-eth12 --subnet 10.12.0.0/24
```

- `--iface`: the router interface facing the DMZ subnet (`r1-eth12` / `r2-eth12`), where ARP traffic is monitored and filtered.
- `--subnet`: the subnet to scan at startup to discover legitimate IP→MAC mappings (`10.12.0.0/24` = DMZ).

## Botnet

### Attack Description

A botnet is a network of compromised machines (bots) controlled by an attacker (botmaster) through a Command & Control (C2) server. The botmaster issues commands to the C2, which the bots periodically poll and execute, reporting results back.

The key property that makes botnets firewall-evasive is that **bots initiate all connections outbound** — the botmaster never needs to reach the bots directly. In this topology:

- **Botmaster**: `internet` (10.2.0.2) — issues commands via HTTP POST to the C2
- **C2 server**: `http` (10.12.0.10:8080) — stores the current command and collects results
- **Bots**: `ws2` (10.1.0.2), `ws3` (10.1.0.3) — poll the C2, execute commands, POST results back

This exploits the existing firewall rules: `internet → DMZ` is allowed by r2, and `LAN → anywhere` is allowed by r1. All connections are initiated from inside, so `ct state established,related` handles the return traffic transparently.

### Attack Script

**C2 server** — run on `http` in the background before starting the attack:

```bash
http python3 attack/botnet/command_server.py &
```

**Bot** — run on `ws2` and/or `ws3`, also in the background:

```bash
ws2 python3 attack/botnet/bot.py &
ws3 python3 attack/botnet/bot.py &
```

**Botmaster** — run on `internet`:

```bash
internet python3 attack/botnet/botmaster.py <command>
```
replace `<command>` with your command. Ex: `whoami` or `ip addr`
### Mitigation Description

The defense runs on `r1` and enforces a **LAN→DMZ egress port whitelist** using nftables. Three rules are inserted before the existing blanket `ip saddr 10.1.0.0/24 accept` rule:

1. **Accept** TCP from LAN to DMZ on trusted ports `{ 21, 22, 80 }` (FTP, SSH, HTTP)
2. **Accept** UDP from LAN to DMZ on trusted ports `{ 5353, 123 }` (DNS, NTP)
3. **Drop** all other new TCP/UDP connections from LAN to DMZ

Any bot attempting to poll the C2 on port 8080 is dropped by rule 3 since 8080 is not in the trusted set. ICMP (ping) is unaffected since it is not TCP/UDP and falls through to the existing blanket accept. The blanket rule is preserved to continue allowing LAN→internet traffic and ICMP to the DMZ.

An additional rate-limit on port 80 (10 new connections/minute) disrupts polling even if the C2 migrates to the standard HTTP port.

### Mitigation Script

```bash
r1 python3 defense/botnet.py
```