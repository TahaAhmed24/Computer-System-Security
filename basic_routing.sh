r1 nft flush ruleset
r1 nft add table inet filter
r1 nft add chain inet filter forward { type filter hook forward priority 0 \; policy drop \; }
r1 nft add rule inet filter forward ct state established,related accept
r1 nft add rule inet filter forward ip saddr 10.1.0.0/24 accept

r2 nft flush ruleset
r2 nft add table inet filter
r2 nft add chain inet filter forward { type filter hook forward priority 0 \; policy drop \; }
r2 nft add rule inet filter forward ct state established,related accept

r2 nft add rule inet filter forward ip saddr 10.1.0.0/24 accept
r2 nft add rule inet filter forward ip saddr 10.2.0.0/24 ip daddr 10.12.0.0/24 accept
r2 nft add rule inet filter forward ip saddr 10.12.0.0/24 ip daddr 10.1.0.0/24 accept