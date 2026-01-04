# Xeoverse

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
<img width="1260" height="914" alt="image" src="https://github.com/user-attachments/assets/dfff39a1-d2b5-4254-993d-fa2f810b2daa" />
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

