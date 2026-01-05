# Xeoverse

<img width="897" height="224" alt="image" src="https://github.com/user-attachments/assets/b9b80bc9-da6e-4919-8096-4c40ef2de90e" />

## Xeoverse做完模擬產生的OUTPUT

Xeoverse 在模擬過程中，於 routing 計算相關流程中輸出多項中間與最終結果，包含 connectivity_matrices、routing_configs、constellation_ip_addresses 與 path.json 等檔案，作為後續 Mininet 網路模擬之輸入與設定依據

### 1.1 connectivity_matrices  
connectivity_matrices描述各時間點衛星之間是否存在可用連線，用以表示當下的網路拓樸狀態   ，並作為後續 routing 計算之基礎輸入資料
<img width="960" height="777" alt="image" src="https://github.com/user-attachments/assets/6c09b286-eb2d-4939-8c83-e34ca1f4497a" />   
Xeoverse 會於每一個模擬時間點輸出一份 adjacency matrix（鄰接矩陣），用以表示該時間點衛星節點之間的連線關係。以 adjacency_matrix_20231113_103000.json 為例，該檔案描述 2023/11/13 10:30:00 時刻之衛星連線狀態。

### 1.2 routing_configs

routing_configs 為 Xeoverse routing 計算後之最終輸出，用以將抽象路徑結果轉換為可實際套用之系統設定。  
*每一秒皆有相對應的routing_configs產生  
*以20231113_103000時刻的routing_configs做解釋
<img width="956" height="191" alt="image" src="https://github.com/user-attachments/assets/4bc35384-244a-4be7-b51b-d736b208202d" />  
在`20231113_103000`的結果中有許多顆衛星(e.g. STARLINK-1054…)，每一顆衛星節點，都有一份獨立的 routing 設定檔

*`.sh` 檔格式是用以將 routing 計算結果轉換為可直接在系統中執行之腳本形式


## Xeoverse呼叫Mininet
<img width="1015" height="267" alt="image" src="https://github.com/user-attachments/assets/e99dbb67-6605-4e50-9d92-37e36c79aca8" />
呼叫mininet流程圖
  
Xeoverse在main.py中呼叫 x_substrate/constellation_mininet.py 裡的setup_mininet_topology()函式

```
xEO_mininet.setup_mininet_topology(new_satellites, path, ip_assignment, routing_r)

```
new_satellites:告訴 Mininet要建哪些節點、每個節點幾個介面   
決定要建哪些 Host(可以發送或接收的端點)  
path:告訴 Mininet 封包要走哪條路  
設定 routing（只讓封包走這條 path）  
ip_assignment:告訴 Mininet 每個介面的 IP  
設定每個 Host 的介面 IP、讓 routing 指令有正確的下一跳  
routing_r:告訴 Mininet 要下哪些 routing 指令  

## constellation_mininet
### 匯入mininet api
用 Mininet 來模擬網路
```
from mininet.net import Mininet
from mininet.node import Controller, OVSSwitch
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel
```

### 建立mininet物件
net為空的虛擬網路
net.start為開始啟動
```
net = Mininet(controller=None, switch=OVSSwitch, link=TCLink)
net.start()
```

### 建立衛星節點
```
# Dictionary to hold the Mininet hosts
hosts = {}
new_hosts = {}

dummy_host = net.addHost('dummy11')

# Create Mininet hosts for each satellite in the path
for sat_name in path:
    sat_name_ = naming_conversion_xeoverse_mininet(sat_name)
    host = net.addHost(sat_name_)
    hosts[sat_name_] = host

# Create Mininet hosts for the neighbours of the satellites in the path
for host_name in hosts:
    neighbours = get_neighbour_satellites(
        naming_conversion_mininet_xeoverse(host_name), satellites
    )
    for x_sats in neighbours:
        sat_name_ = naming_conversion_xeoverse_mininet(x_sats)
        if sat_name_ not in hosts and sat_name_ not in new_hosts:
            host = net.addHost(sat_name_)
            new_hosts[sat_name_] = host

hosts.update(new_hosts)

```

### 建立鏈路
```
#找 links 並呼叫 create_link_between(外層)
for host_name in hosts:
    linksPerSat = get_available_links_per_sat(
        naming_conversion_mininet_xeoverse(host_name),
        ip_assignments,
        satellites
    )

    for tuples in linksPerSat:
        if naming_conversion_xeoverse_mininet(tuples[0].split("-eth")[0]) in hosts and \
           naming_conversion_xeoverse_mininet(tuples[2].split("-eth")[0]) in hosts:
            create_link_between(
                tuples[0], tuples[2], tuples[1], tuples[3],
                net, satellites,
                timestamp=datetime(2023, 11, 13, 10, 30, 0)
            )



#建立ISL(內層)
link_latency = x_topo.calculate_satellites_latency_(sat1, sat2, timestamp)
link_bw = x_topo.calculate_satellites_bw_(
    naming_conversion_mininet_xeoverse(host1_name),
    naming_conversion_mininet_xeoverse(host2_name),
    timestamp
)

net.addLink(
    host1, host2,
    intfName1=intf1_name, intfName2=intf2_name,
    cls=TCLink,
    params1={'ip': ip1 + '/30'}, params2={'ip': ip2 + '/30'},
    bw=link_bw, delay=(str(link_latency) + 'ms')
)

```

### 加入地面段
```
#建立地面使用者 / gateway
config = read_config_(config_file)
end1 = config['experiment']['end1']
end2 = config['experiment']['end2']

host_end1 = net.addHost(end1.replace(" ", ""))
host_end2 = net.addHost(end2.replace(" ", ""))

terminal1_ip = xEO_network.find_the_ip_of_interface(end1+"-eth0", ip_assignments)
sat_intf, sat_ip = xEO_network.find_matching_network_interface(terminal1_ip, ip_assignments)
value = ip_assignments.pop(sat_intf, None)

#把地面使用者和衛星接起來
net.addLink(
    host_end1,
    hosts[naming_conversion_xeoverse_mininet(sat_intf.split("-eth")[0])],
    intfName1=end1+"-eth0",
    intfName2=sat_intf.replace("STARLINK", "STL"),
    cls=TCLink,
    params1={'ip': terminal1_ip + '/30'},
    params2={'ip': value + '/30'},
    bw=130, delay='5ms'
)
host_end1.cmd(f"route add default gw {value}")
```

### 套用routing
```
net = apply_routing_commands_in_mininet(net, routing_dict)
for satellite, commands in routing_dict.items():
    m_satellite = naming_conversion_xeoverse_mininet(satellite)
    node = net.getNodeByName(m_satellite)
    if node:
        for cmd in commands:
            node.cmd(cmd)

```

### mininet測量
#### ping
```
command = f"ping -c {config['experiment']['duration_seconds']} {terminal2_ip} >> results_..._.log"
result = host_end1.cmd(command)
print(result)
```
#### iperf
```
command2 = f"iperf -s &"
command1 = f"iperf -c {terminal2_ip} -C {config['experiment']['cc']} -i1 -t {config['experiment']['duration_seconds']} >> results_..._.log 2>&1 &"
host_end2.cmd(command2)
host_end1.cmd(command1)
```




## Routing演算法

Xeoverse採用 Dijkstra shortest path 演算法進行 routing 計算  
在x_routing中有一個定義dijkstra的函式用來算shortest_path  
*Dijkstra Algorithm 是用來找出 Graph 上兩個頂點之間的最短路徑。  

```
def dijkstra_shortest_path(graph, start_idx, end_idx, criteria):
#graph:用adjacency matrix建立的圖
#start_idx end_idx 表示起終點
#criteria 表示成本計算方式(latency/throughput)
#edge_info表示那一條連線的資訊(latency,throughput)
    #初始化部分
    priority_queue = [(0, start_idx)]
    #預設距離設為 ∞
    distances = {node: float('infinity') for node in graph}
    distances[start_idx] = 0
    previous_nodes = {node: None for node in graph}
		
		#有尚未處理的點就繼續
    while priority_queue:
        #每次選目前離起點最近的點
        current_distance, current_node = heapq.heappop(priority_queue)
        #是否到達終點
        if current_node == end_idx:
            break

        # Error handling for missing nodes
        if current_node not in graph:
            raise ValueError(f"Node {current_node} not found in graph")

        #探索現在連街的鄰居 + 計算成本
        for neighbor, edge_info in graph[current_node].items():
            latency, throughput = edge_info
            distance = calculate_distance(current_distance, latency, throughput, criteria)

            #更新最短路徑
            if distance < distances[neighbor]:
                distances[neighbor] = distance
                previous_nodes[neighbor] = current_node
                heapq.heappush(priority_queue, (distance, neighbor))

    path = []
    current = end_idx
	 
	  #回推 path
	  while current is not None:
        path.append(current)
        current = previous_nodes[current]
    path.reverse()
   #previous_nodes是因為終點往回數，所以要再reverse就會變成從起點開始的path
    return path if path[0] == start_idx else []

```
-dijkstra函示之流程圖
<img width="1411" height="301" alt="image" src="https://github.com/user-attachments/assets/0cc91143-f470-4e60-a7cb-457b8d95dab9" />  

*Priority Queue（優先佇列）是一種資料結構，雖然是佇列但**每次取出的不是最早放進去的，而是優先度最高的**

e.g.Dijkstra示範圖
<img width="561" height="273" alt="image" src="https://github.com/user-attachments/assets/b0816ea4-212e-4cf6-979a-406d60bc5159" />
  
step0.先設距離表 A:0 BCD=infinite  
step1.以最小距離的點去更新鄰居點(A距離為0,B距離為4 距離C為2 距離D為1)  
step2.找出距離最短的(D點 距離1)  
step3.以D當更新鄰居的點  
step4.用D更新鄰居：  
A~D~B=1+5=6(但這樣比原本的4大 所以不更新)  
A~D~C=1+3=4(但這樣比原本的2大 所以不更新)  
step5.以C當更新鄰居的點：  
A~C~D=2+3=5(但這樣比原本的1大 所以不更新)  
即可算出最短距離  

