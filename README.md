# xeoverse

##Xeoverse呼叫Mininet

Xeoverse在main.py中呼叫 x_substrate/constellation_mininet.py 裡的setup_mininet_topology()函式,呼叫x_substrate/constellation_mininet.py

```xEO_mininet.setup_mininet_topology(new_satellites, path, ip_assignment, routing_r)
# xEO_network.print_satellite_neighbors_and_ips(new_satellites)
# print(xEO_network.distribute_ip_addresses(xTP["matrix"], xTP["satellites"], ip_subnet))
# (adjacency_matrix, terminals, start_terminal, end_terminal, satellites, timestamp):
# # # Example Usage
# interface_counts = xEO_network.map_satellites_to_interface_counts(xTP["mx"], xTP["name2index"])
# satellite_name = 'STARLINK-30700'  # Example satellite name

# interfaces_info = xEO_network.get_satellite_interfaces(satellite_name, xTP["mx"], xTP["name2index"], link_assignments, interface_counts)
# print(interfaces_info)
```
new_satellites:告訴 Mininet要建哪些節點、每個節點幾個介面
決定要建哪些 Host(可以發送或接收的端點)
path:告訴 Mininet 封包要走哪條路
設定 routing（只讓封包走這條 path）
ip_assignment:告訴 Mininet 每個介面的 IP
設定每個 Host 的介面 IP、讓 routing 指令有正確的下一跳
routing_r:告訴 Mininet 要下哪些 routing 指令

'''
***
new_satellites:告訴 Mininet要建哪些節點、每個節點幾個介面
決定要建哪些 Host(可以發送或接收的端點)
path:告訴 Mininet 封包要走哪條路
設定 routing（只讓封包走這條 path）
ip_assignment:告訴 Mininet 每個介面的 IP
設定每個 Host 的介面 IP、讓 routing 指令有正確的下一跳
routing_r:告訴 Mininet 要下哪些 routing 指令
