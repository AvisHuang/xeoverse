# Xeoverse

<img width="897" height="224" alt="image" src="https://github.com/user-attachments/assets/b9b80bc9-da6e-4919-8096-4c40ef2de90e" />

## Xeoverse做完模擬產生的OUTPUT

Xeoverse 在模擬過程中，於 routing 計算相關流程中輸出多項中間與最終結果，包含 connectivity_matrices、routing_configs、constellation_ip_addresses 與 path.json 等檔案，作為後續 Mininet 網路模擬之輸入與設定依據

### 1.1 connectivity_matrices  
connectivity_matrices描述各時間點衛星之間是否存在可用連線，用以表示當下的網路拓樸狀態   ，並作為後續 routing 計算之基礎輸入資料
<img width="960" height="777" alt="image" src="https://github.com/user-attachments/assets/6c09b286-eb2d-4939-8c83-e34ca1f4497a" />   
Xeoverse 會於每一個模擬時間點輸出一份 adjacency matrix（鄰接矩陣），用以表示該時間點衛星節點之間的連線關係。以 adjacency_matrix_20231113_103000.json 為例，該檔案描述 2023/11/13 10:30:00 時刻之衛星連線狀態。

<img width="964" height="1008" alt="image" src="https://github.com/user-attachments/assets/451f63da-1c0b-4020-82d7-49729f9739c1" />
adjencency matrix內容
這只是衛星index,如果要知道衛星名子要去constellation_ip_addresses_20231113_103000.json對照

### 1.2 routing_configs

routing_configs 為 Xeoverse routing 計算後之最終輸出，用以將抽象路徑結果轉換為可實際套用之系統設定。  
*每一秒皆有相對應的routing_configs產生  
<img width="467" height="872" alt="image" src="https://github.com/user-attachments/assets/bc120602-b0ef-47d4-9065-c4bb8376aafd" />

*以20231113_103000時刻的routing_configs做解釋
<img width="956" height="191" alt="image" src="https://github.com/user-attachments/assets/4bc35384-244a-4be7-b51b-d736b208202d" />  
在`20231113_103000`的結果中有許多顆衛星(e.g. STARLINK-1054…)，每一顆衛星節點，都有一份獨立的 routing 設定檔

*`.sh` 檔格式是用以將 routing 計算結果轉換為可直接在系統中執行之腳本形式  
*舉其中STARLINK-1054.sh的內容做解釋，會出現很多路由規則
<img width="962" height="481" alt="image" src="https://github.com/user-attachments/assets/843aa072-9dcb-4522-b940-f67e6c7ff879" />  
以ip route add 192.168.26.84/30 via 192.168.30.53 dev STL-1791-eth2做說明，封包的目的地是 192.168.26.84/30，STARLINK-1791會將應該把封包交給192.168.30.53下一跳，並從 STL-1791-eth2 這個介面送出去
*下一跳表示「下一步先丟給誰」


### 1.3 constellation_ip_addresses  
constellation_ip_addresses是在記錄各時間點衛星節點所使用之 IP 位址與介面配置，作為抽象拓樸與實際網路模擬之對應。  
<img width="962" height="293" alt="image" src="https://github.com/user-attachments/assets/a93e050d-5fb8-4130-b95c-5408ed6cf441" />
 
Xeoverse 於模擬過程中，依模擬時間點逐秒輸出各衛星節點之 IP 位址設定檔（constellation_ip_addresses），以反映低軌衛星網路之動態特性。  
舉其中constellation_ip_addresses_20231113_103000.json，其內容為以下(因為太多並未全部列出)
<img width="669" height="918" alt="image" src="https://github.com/user-attachments/assets/e329b278-d2a5-441a-94ef-604e36c1b867" />

會出現很多衛星的連線，以`STARLINK-30816-eth2": "192.168.41.133"`做解釋
`STARLINK-30816`表示衛星節點ID，eth2表示該衛星上的第 2 個網路介面，`192.168.41.133`表示此介面實際使用的 IP 位址
然後最下面的London、SanFranci表示地面端點的網路介面 IP  


### 1.4 path.json
path.json 記錄於特定模擬時間點下，資料自來源端至目的端所經過之衛星節點序列；隨著衛星拓樸與可用連線之變化，不同時間點可能對應不同之路徑結果。  
<img width="930" height="290" alt="image" src="https://github.com/user-attachments/assets/f555529d-c57d-4655-a9c7-1d73100092b2" />

path 會隨模擬時間點變化，於不同時間點可能產生不同之路徑結果
<img width="959" height="455" alt="image" src="https://github.com/user-attachments/assets/a15cb714-4303-41ab-9e98-1b4b9e33830b" />
STARLINK-****表示是由這些衛星節點 ID 組成


## Xeoverse呼叫Mininet
<img width="938" height="254" alt="image" src="https://github.com/user-attachments/assets/60ba7b73-6faa-4e5d-8073-be72a8ed9ebf" />

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
（ host存Mininet 裡的所有衛星節點
  new_hosts暫存「後來補上的鄰居衛星」）

dummy_host = net.addHost('dummy11')
（建一個暫時的節點 當eth2,3還沒用到時 先接到dummy 因為mininet不能跳號）

# Create Mininet hosts for each satellite in the path
for sat_name in path:
	#轉換名字
    sat_name_ = naming_conversion_xeoverse_mininet(sat_name)
	#加了一台虛擬主機
	host = net.addHost(sat_name_)
	把這顆衛星存到host[sat_name]裡
    hosts[sat_name_] = host

# Create Mininet hosts for the neighbours of the satellites in the path
#把剩餘衛星建起來(上面只有建shortes path),會重複去查最短路徑的微星鄰居
for host_name in hosts:
	#依據拓樸結果找出相對應的鄰居
    neighbours = get_neighbour_satellites(
		#再把mininet的名字轉xeo的名字才能去satellite查詢
        naming_conversion_mininet_xeoverse(host_name), satellites
    )
	#補齊path上衛星的鄰居
    for x_sats in neighbours:
		#轉名字
        sat_name_ = naming_conversion_xeoverse_mininet(x_sats)
		#判斷是否為沒被建的鄰居
        if sat_name_ not in hosts and sat_name_ not in new_hosts:
			#建一個新節點
			host = net.addHost(sat_name_)
            new_hosts[sat_name_] = host
#所有host=path_sat+neighbor_sat
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

| 指令 | 參數 | 目標 | 輸出 |
|------|------|------|------|
| ping | -c | terminal2_ip | >> results_..._.log |
| 要做的事情 | 次數 | 對 terminal2 | 回傳 result |

host_end1去使用command指令測量

測量ping結構圖

<img width="699" height="372" alt="image" src="https://github.com/user-attachments/assets/f9c2dba6-2394-4d62-9e02-380f68a33166" />

RTT=GSL1+ISL+GSL2+ICMP回覆

#### iperf
```
command2 = f"iperf -s &"
command1 = f"iperf -c {terminal2_ip} -C {config['experiment']['cc']} -i1 -t {config['experiment']['duration_seconds']} >> results_..._.log 2>&1 &"
host_end2.cmd(command2)
host_end1.cmd(command1)
```
| 參數 | 意義 |
|------|------|
| -s | server mode | 
| & | 背景執行 |

| 參數 | 意義 |
|------|------|
| -c | client mode | 
| terminal2_ip | 目標端 IP |
| -C | congestion control (可以決定傳的快慢 多寡)| 
| -i 1 | 一秒輸出一次統計結果 |
| -t {duration_seconds} | 實驗的時間 |
| >> results_..._.log 2>&1 | 寫入實驗檔(不覆蓋) |
| & | 背景執行 |

*client:主動連線送信號
*server:等別人連線接收信號

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

## GW-SAT建立link

<img width="1172" height="441" alt="image" src="https://github.com/user-attachments/assets/058cda52-1c82-4b7f-9916-280553714da5" />

### 呼叫setup_mininet_topology
```
setup_mininet_topology(
    satellites=satellites,
    path=path,
    ip_assignments=ip_assignments,
    routing_dict=routing_dict,
    config_file=config_file
)
```

### 讀取設定檔 config
```
ground_segments = {}
config = read_config_(config_file)```
```
### 取得 Gateway 名稱 end1 / end2
```
end1 = config['experiment']['end1']
end2 = config['experiment']['end2']
```

### 在 Mininet 建立 Gateway Host
```
host_end1 = net.addHost(end1.replace(" ", ""))
host_end2 = net.addHost(end2.replace(" ", ""))
#把原始名稱對到mininet host物件中
ground_segments[end1] = host_end1
ground_segments[end2] = host_end2
```

### 找出 end1 / end2 的 eth0 IP
```
terminal1_ip = xEO_network.find_the_ip_of_interface(
#用end1-eth0去ip_assignment查出對應的ip
    end1 + "-eth0",
    ip_assignments
)
terminal2_ip = xEO_network.find_the_ip_of_interface(
    end2 + "-eth0",
    ip_assignments
)
```

### 用 GW 的 IP 找到對應衛星介面
```
sat_intf, sat_ip = xEO_network.find_matching_network_interface(
#用 terminal1_ip去反查 ip_assignments，找出另一端衛星介面
	terminal1_ip,
    ip_assignments
)
```

### 取出衛星端 IP
```
#從 ip_assignments 裡把 sat_intf 對應的 IP 拿出來
value = ip_assignments.pop(sat_intf, None)
```

### 建立 end1 的 GW–SAT Link（GSL）
```
net.addLink(
    host_end1,
    hosts[naming_conversion_xeoverse_mininet(sat_intf.split("-eth")[0])],
    intfName1=end1 + "-eth0",
    intfName2=sat_intf.replace("STARLINK", "STL"),
    cls=TCLink,
    params1={'ip': terminal1_ip + '/30'},
    params2={'ip': value + '/30'},
    bw=130,
    delay='5ms'
)
```


## Xeoverse資料傳給sns3

XEO 負責網路層（L3）的拓樸與路由，而 SNS3 負責實體層（L1）與 MAC 層（L2）的模擬
| xeoverse資料 | 對應sns3部分 | 目的 |
|------|------|------|
| connectivity_matrix | Channel / Propagation | 決定哪些衛星與地面站之間存在物理鏈路（L1/L2 通道建立） | 
| satellites_...json (座標) | SatGeoHelper | 提供衛星動態經緯度與高度，用以計算都卜勒頻移與路徑損耗。 | 
| path.json | Scenario / Example Layer | 在 SNS3 中手動配置特定的「跳轉序列」，模擬端對端（E2E）資料流。 | 
| routing_configs |MAC / PHY Stack | 參考 XEO 的路由決策，在 SNS3 中設定靜態路由或時槽排程基準。 | 
| constellation_ip_...json |ns-3 Network / Internet | 雖然兩套系統位址管理不同，但可用來統一節點的 ID 映射關係。 | 


### path.json
### 
### adjacency_matrix

```
import json
import os
import csv
import glob

def safe_convert():
    # 1. 只找資料夾，不刪除任何東西
    folders = sorted(glob.glob('results_*'), reverse=True)
    if not folders:
        print("找不到 results 資料夾！請確認你已經跑過預處理。")
        return
    
    src_folder = folders[0] # 抓取最新的結果
    print(f"讀取來源資料夾：{src_folder}")

    # 從資料夾名稱抓取時間戳記
    parts = src_folder.split('_')
    ts = f"{parts[1]}_{parts[2]}"

    # 定義檔案路徑 (只讀不寫) [cite: 401]
    path_json = os.path.join(src_folder, f"path_{ts}.json")
    sat_json = os.path.join(src_folder, f"satellites_{ts}/satellites_{ts}.json")
    
    # 定義要產出的「新檔案」
    output_file = "xeo_data_for_sns3.csv"

    try:
        # 以「唯讀模式 'r'」開啟，絕對不會弄壞原始資料
        with open(path_json, 'r') as f:
            path_list = json.load(f) # 取得跳轉路徑

        with open(sat_json, 'r') as f:
            all_sats = json.load(f) # 取得座標資料

        # 寫入全新的 CSV 檔
        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Order', 'Sat_ID', 'Lat', 'Lon', 'Alt']) # 標頭
            
            for i, name in enumerate(path_list):
                if name in all_sats:
                    coords = all_sats[name]['coordinates']
                    writer.writerow([i, name, coords[0], coords[1], coords[2]])

        print(f"--- 轉換成功 ---")
        print(f"原始資料夾 '{src_folder}' 保持不變。")
        print(f"已產出新檔案：{output_file}")

    except Exception as err:
        print(f"讀取時發生錯誤：{err}")

if __name__ == "__main__":
    safe_convert()
```


*TLE（Two-Line Element）是一種「用兩行文字描述一顆衛星軌道」的標準格式檔案。
只要有 TLE + 時間，就能用數學模型算出「任一時間點衛星在太空中的座標」。

