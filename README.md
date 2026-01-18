# Xeoverse


<img width="897" height="224" alt="image" src="https://github.com/user-attachments/assets/b9b80bc9-da6e-4919-8096-4c40ef2de90e" />


##  short-term target
- [ ] 完成輸出routing Table的csv檔(done)
- [ ] 完成上次報告的修正
- [ ] 整理 xeoverse 筆記
- [ ] 閱讀sns3 建立衛星程式碼




## 一、Constellation Geometry (IV.A)
會藉由所輸入的TLE和config.yaml來進行計算，算出每一顆衛星當下的位置及角度

輸入：[TLE](https://github.com/AvisHuang/xeoverse/blob/main/tle.txt)、[config.yaml](https://github.com/AvisHuang/xeoverse/blob/main/config.yaml)

### 1.TLE（Two-Line Element Set，雙行軌道要素）

TLE用兩行文字描述一顆人造衛星在某一時間點的軌道狀態的標準格式，可搭配SGP4計算衛星在任意時間的空間位置與速度

*SPG4是一個軌道推進模型，會考慮大氣阻力、空氣擾動考慮地球不是完美球體用來把 TLE 裡的軌道參數，推算成 某一時間點的衛星實際空間位置與速度。
```
STARLINK-1007           
1 44713U 19074A   23314.42416486  .00012364  00000+0  84661-3 0  9991
2 44713  53.0550  43.6089 0001326  94.7939 265.3201 15.06437851220768
```

| 欄位名稱 (Line 1) | 原始數值 | 欄位名稱 (Line 2) | 原始數值 |
| :--- | :--- | :--- | :--- |
| **NORAD 衛星編號** | 44713 | **NORAD 衛星編號** | 44713 |
| **Classification** | U | **軌道平面與地球赤道的夾角** | 53.0550 |
| **發射年份 + 第幾次發射 + 分離物件代碼** | 19074A | **軌道平面在地球周圍的方向角** | 43.6089 |
| **TLE 的參考時間點** | 23314.42416486 | **偏心率** | 0001326 |
| **空氣阻力參數** | 84661-3 | **平均運動** | 15.06437851 |
| **用來確認兩行是同一顆衛星** | (備註) | **用來確認兩行是同一顆衛星** | (備註) |
| **軍事/民用分類用** | (備註) | **決定衛星能飛到哪些緯度** | (備註) |
| **(國際編號空欄)** | | **影響衛星在地球上方的位置** | (備註) |
| **2023年第314天 的小數時間** | (備註) | **軌道的橢圓程度** | (備註) |
| **描述大氣阻力效應** | (備註) | **每天繞地球幾圈** | (備註) |


### 2.config.yaml

描述時間(simulation函式)、衛星怎麼互連(parameters函式)、無線通道假設(rf-parameters函式)、資料來源在哪、實驗要做什麼(experiment函式)

## 二、Constellation_topology(IV.B)

會藉由所輸入的衛星及地面站資訊,利用[constellation.py](https://github.com/AvisHuang/xeoverse/blob/main/constellation_topology.py)來算出每秒拓樸的連接狀態，及上下左右的鄰居並輸出connectivity matrix

輸入：satellite,ground segment 輸出：[connectivity_matrix](https://github.com/AvisHuang/xeoverse/blob/main/adjacency_matrix_20231113_103000.json)

### 鄰居判別

前後上下鄰居：同軌道連線

左右鄰居：跨軌道連線(隔壁條軌道)，會透過角度來判斷左右鄰居(左:0~180,右$180~360)

### 1.connectivity matrix

Xeoverse 會於每一個模擬時間點輸出一份adjacency matrix（鄰接矩陣），其矩陣大小為N*N(N為衛星數量)，用以表示該時間點衛星節點之間的連線關係。以 adjacency_matrix_20231113_103000.json 為例，該檔案描述 2023/11/13 10:30:00 時刻之衛星連線狀態。

<img width="564" height="1008" alt="image" src="https://github.com/user-attachments/assets/451f63da-1c0b-4020-82d7-49729f9739c1" />

這只是衛星index,如果要知道衛星名字要去constellation_ip_addresses_20231113_103000.json對照

## 三、Constellation link characteristics(IV.C)
Constellation Link Characteristics (IV.C) 是將「拓樸結構」轉化為「網路參數」的關鍵橋樑。它負責為拓樸中的每一條連線賦予真實的物理屬性

轉換目的：因為IV.B所產生的adjacency matrix只能得知是否相連，無法得知距離 延遲 容量，當經過數據計算後就可以輸出latency matrix和capacity matrix做routing去計算出最短的路徑

Constellation link characteristics會藉由輸入connectivity matrix到[Constellation_preprocessing.py](https://github.com/AvisHuang/xeoverse/blob/main/constellation_preprocessing.py)進行調度，然後就會去constellation_topology.py及x_net/constellation_network.py計算邏輯並輸出latency matrix和capacity matrix

輸入：Connectivity Matrix
輸出：latency matrix和capacity matrix

因為latency matrix和capacity matrix產生輸出後是直接交給routing做使用,所以沒有存成json檔

### 1.latency matrix
是由輸入的adjacency matrix去看哪顆衛星有連接，接著去tle的到每顆衛星的實際位置，然後才去topology.py中的函示calculate_satellites_latency_算出延遲
$$Latency = \frac{Distance \times 1000 (\text{米})}{3 \times 10^8 (\text{光速})} \times 1000 (\text{轉毫秒})$$
### 2.capacity matrix
在某一個時間點，每一對節點之間最多能傳多少資料，它有分成GSL和ISL
,ISL的頻寬是直接在config.yaml定義的,GSL則是動態計算，是引用衛星位置與地面站位置，計算出訊號強度，再利用香農定理計算出該時刻的最大容量。

## 四、Constellation Routing(IV.D)

在經過[Constellation Routing](constellation_routing.py)IV.D 計算後([用Dijkstra演算法](https://github.com/AvisHuang/xeoverse/blob/main/README.md#dilkstra%E6%BC%94%E7%AE%97%E6%B3%95))所產生的ISL及GSL路由

在result會儲存每一秒衛星的路由表並轉呈ip route指令


<img width="552" height="700" alt="image" src="https://github.com/user-attachments/assets/ca15a244-5619-4d21-bc1a-4199e1336cf8" />

每一顆衛星為一個router，
內部就是每一顆衛星的routing table指令



### *Dilkstra演算法

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






## Xeoverse做完模擬產生的OUTPUT

Xeoverse 在模擬過程中，於 routing 計算相關流程中輸出多項中間與最終結果，包含 connectivity_matrices、routing_configs、constellation_ip_addresses 與 path.json 等檔案，作為後續 Mininet 網路模擬之輸入與設定依據


### 1.1 connectivity_matrices  
connectivity_matrices描述各時間點衛星之間是否存在可用連線，用以表示當下的網路拓樸狀態   ，並作為後續 routing 計算之基礎輸入資料
<img width="960" height="777" alt="image" src="https://github.com/user-attachments/assets/6c09b286-eb2d-4939-8c83-e34ca1f4497a" />   
Xeoverse 會於每一個模擬時間點輸出一份 adjacency matrix（鄰接矩陣），用以表示該時間點衛星節點之間的連線關係。以 adjacency_matrix_20231113_103000.json 為例，該檔案描述 2023/11/13 10:30:00 時刻之衛星連線狀態。


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

*Congestion control 是 TCP 用來根據網路狀況動態調整傳輸速率的機制，在 iperf 實驗中透過 -C 指定不同演算法，可以觀察在高延遲的 NTN 環境下對吞吐量的影響。

## Routing演算法

Xeoverse採用 Dijkstra shortest path 演算法進行 routing 計算  
在x_routing中有一個定義dijkstra的函式用來算shortest_path  

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
#sat_intf, sat_ip:衛星的介面名稱 IP
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
	#轉名字(xeoverse轉mininet)
    hosts[naming_conversion_xeoverse_mininet(sat_intf.split("-eth")[0])],

    intfName1=end1 + "-eth0",
    intfName2=sat_intf.replace("STARLINK", "STL"),
    cls=TCLink,
#指定這條link使用TCLink類型
    params1={'ip': terminal1_ip + '/30'},
    params2={'ip': value + '/30'},
    bw=130,
    delay='5ms'
)
```






## Xeoverse與sns3資料對比

XEO 負責網路層（L3）的拓樸與路由，而 SNS3 負責實體層（L1）與 MAC 層（L2）的模擬
| xeoverse資料 | 對應sns3部分 | 目的 |
|------|------|------|
| connectivity_matrix | Channel / Propagation | 決定哪些衛星與地面站之間存在物理鏈路（L1/L2 通道建立） | 
| satellites_...json (座標) | SatGeoHelper | 提供衛星動態經緯度與高度，用以計算都卜勒頻移與路徑損耗。 | 
| path.json | Scenario / Example Layer | 在 SNS3 中手動配置特定的「跳轉序列」，模擬端對端（E2E）資料流。 | 
| routing_configs |MAC / PHY Stack | 參考 XEO 的路由決策，在 SNS3 中設定靜態路由或時槽排程基準。 | 
| constellation_ip_...json |ns-3 Network / Internet | 雖然兩套系統位址管理不同，但可用來統一節點的 ID 映射關係。 | 

## 轉換routing table給sns3

https://github.com/AvisHuang/xeoverse/blob/main/sns3_dynamic_routing_60s.csv

https://github.com/AvisHuang/xeoverse/blob/main/sns3_final_routing_with_source_ip.csv

(ver.2有source_sat ip)

<img width="425" height="146" alt="image" src="https://github.com/user-attachments/assets/1503c0ee-7951-45ca-b24d-fb0a83213858" />

| Timestamp | Source_Sat | Destination_Network | Next_Hop_IP |
|------|------|------|------|
| 時間戳記 | 來源衛星 (起點) | 目的網段 (終點) | 下一跳 IP (轉發對象) |

因為routing_table的用途是知道下一跳的位置，所以xeoverse所產出的routing_table沒有把source_sat的ip寫出來，如果要找對應ip要去constellation裡找，但在ver2.裡有把source_sat ip加上去

<img width="614" height="798" alt="image" src="https://github.com/user-attachments/assets/89c44347-9066-4224-ae09-84d2be361245" />

xeoverse所產生的routing table
<img width="953" height="394" alt="image" src="https://github.com/user-attachments/assets/a35a6011-a4e6-4fe3-b68b-0def4c37a908" />

ip route add <目的子網> via <下一跳IP> dev <出口介面>


轉換程式
```
import os
import csv
import glob
import re

def extract_dynamic_routing():
    # 1. 直接鎖定你的結果主資料夾
    main_dir = "results_20231113_103000"
    if not os.path.exists(main_dir):
        # 如果主資料夾名稱會變，改用自動搜尋
        main_folders = sorted(glob.glob('results_*'))
        if not main_folders:
            print("找不到 results 資料夾")
            return
        main_dir = main_folders[-1]
    
    print(f"分析目標：{main_dir}")
    output_file = "sns3_dynamic_routing_60s.csv"

    # 2. 獲取所有秒數資料夾
    # 這裡的路徑改為直接在 main_dir 下搜尋
    config_dirs = sorted(glob.glob(os.path.join(main_dir, 'routing_configs_*')))
    config_dirs = [d for d in config_dirs if os.path.isdir(d) and not d.endswith('_NOM')]

    if not config_dirs:
        print("錯誤：在資料夾內找不到 routing_configs 子資料夾")
        return

    print(f"找到 {len(config_dirs)} 秒的資料，開始寫入...")

    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Timestamp', 'Source_Sat', 'Destination_Network', 'Next_Hop_IP'])

        for config_dir in config_dirs:
            # 提取 6 位數時間戳記 (例如 103000)
            timestamp = os.path.basename(config_dir).split('_')[-1]
            
            # 獲取該秒內所有 .sh
            sh_files = glob.glob(os.path.join(config_dir, "*.sh"))
            for sh_file in sh_files:
                sat_name = os.path.basename(sh_file).replace(".sh", "")
                
                with open(sh_file, 'r') as f:
                    for line in f:
                        if "ip route add" in line and "via" in line:
                            parts = line.split()
                            # 欄位索引：ip(0) route(1) add(2) dest(3) via(4) next_hop(5)
                            dest_net = parts[3]
                            next_hop = parts[5]
                            writer.writerow([timestamp, sat_name, dest_net, next_hop])

    print(f"----------------------------------------")

if __name__ == "__main__":
    extract_dynamic_routing()
```
