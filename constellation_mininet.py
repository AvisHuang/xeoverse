from mininet.net import Mininet
from mininet.node import Controller, OVSSwitch
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel
import random
from datetime import datetime, timedelta

import yaml
import x_net.constellation_network as xEO_network
import x_topology.constellation_topology as x_topo
import x_scullery.constellation_preprocessing as x_pre

DEBUG_MODE = True  # Set this to False to turn off debug prints

def delete_existing_link(net, host, intf_name):
    link_target = ""
    for link in net.links:
        if link.intf1 is None or link.intf2 is None:
            continue
        
        # print(host, intf_name)
        if link.intf1.node == host and link.intf1.name == intf_name or link.intf2.node == host and link.intf2.name == intf_name:
            # print(host, intf_name, link.intf1, link.intf2 , "------------")
            print("delete >", link.intf1.node, link.intf2.node)
            link_target = link
            break
    
    if link_target != "":
        net.delLink(link_target)

    return net

def add_routing_for_ground_segments(net, host_end1, host_end2, end1, end2, ip_assignments, routing_dict, hosts, path):
    terminal1_ip = xEO_network.find_the_ip_of_interface(end1+"-eth0", ip_assignments)
    sat_intf, sat_ip = xEO_network.find_matching_network_interface(terminal1_ip, ip_assignments)
    value = ip_assignments.pop(sat_intf, None)
    net = delete_existing_link(net, host_end1, end1 + "-eth0")

    net.addLink(host_end1, hosts[naming_conversion_xeoverse_mininet(sat_intf.split("-eth")[0])], intfName1=end1+"-eth0", intfName2=sat_intf.replace("STARLINK", "STL"), cls=TCLink, params1={'ip': terminal1_ip + '/30'}, params2={'ip': value + '/30'}, bw=140, delay='5ms')  # Example bandwidth and delay
    host_end1.cmd(f"route add default gw {value}")

    terminal2_ip = xEO_network.find_the_ip_of_interface(end2+"-eth0", ip_assignments)
    sat_intf, sat_ip = xEO_network.find_matching_network_interface(terminal2_ip, ip_assignments)
    value = ip_assignments.pop(sat_intf, None)
    net = delete_existing_link(net, host_end2, end2 + "-eth0")

    net.addLink(host_end2, hosts[naming_conversion_xeoverse_mininet(sat_intf.split("-eth")[0])], intfName1=end2+"-eth0", intfName2=sat_intf.replace("STARLINK", "STL"), cls=TCLink, params1={'ip': terminal2_ip + '/30'}, params2={'ip': value + '/30'}, bw=140, delay='5ms')  # Example bandwidth and delay
    host_end2.cmd(f"route add default gw {value}")

    sat1_ips = xEO_network.find_all_ips_of_sat(path[0], ip_assignments)
    sat2_ips = xEO_network.find_all_ips_of_sat(path[len(path)-1], ip_assignments)
    
    # print(path[0], sat1_ips)
    # print(path[len(path)-1], sat2_ips)

    for satellite, commands in routing_dict.items():
        for cmd in commands:
            for ip in sat1_ips:
                net_ip = xEO_network.get_network_address(ip, 30)
                if net_ip in cmd or ip in cmd:
                    commandParts = cmd.split("dev")
                    # print(net_ip, ip, cmd, commandParts)
                    if "via" in commandParts[0]:
                        sub_command = commandParts[0].split("via")[1]
                        # print(sub_command)
                        if satellite in path:
                            routes = hosts[naming_conversion_xeoverse_mininet(satellite)].cmd('ip route')
                            if xEO_network.get_network_address(terminal1_ip, 30) in routes:
                                routing_dict[satellite].append(f"ip route change {xEO_network.get_network_address(terminal1_ip, 30)} via{sub_command}dev{commandParts[1]}")    
                            else:
                                routing_dict[satellite].append(f"ip route add {xEO_network.get_network_address(terminal1_ip, 30)} via{sub_command}dev{commandParts[1]}")
                        else:
                            debug_print(f"We do not need to update this satellite {satellite} because any way it is not in the path", "yellow")
                    else:
                        if satellite in path:
                            routes = hosts[naming_conversion_xeoverse_mininet(satellite)].cmd('ip route')
                            if xEO_network.get_network_address(terminal1_ip, 30) in routes:
                                routing_dict[satellite].append(f"ip route change {xEO_network.get_network_address(terminal1_ip, 30)} dev{commandParts[1]}")
                            else:
                                routing_dict[satellite].append(f"ip route add {xEO_network.get_network_address(terminal1_ip, 30)} dev{commandParts[1]}")
                        else:
                            debug_print(f"We do not need to update this satellite {satellite} because any way it is not in the path", "yellow")

            for ip in sat2_ips:
                net_ip = xEO_network.get_network_address(ip, 30)
                if net_ip in cmd or ip in cmd:
                    commandParts = cmd.split("dev")
                    if "via" in commandParts[0]:
                        sub_command = commandParts[0].split("via")[1]
                        if satellite in path:
                            routes = hosts[naming_conversion_xeoverse_mininet(satellite)].cmd('ip route')
                            if xEO_network.get_network_address(terminal2_ip, 30) in routes:
                                routing_dict[satellite].append(f"ip route change {xEO_network.get_network_address(terminal2_ip, 30)} via{sub_command}dev{commandParts[1]}")
                            else:
                                routing_dict[satellite].append(f"ip route add {xEO_network.get_network_address(terminal2_ip, 30)} via{sub_command}dev{commandParts[1]}")
                        else:
                            debug_print(f"We do not need to update this satellite {satellite} because any way it is not in the path", "yellow")
                    else:
                        if satellite in path:
                            routes = hosts[naming_conversion_xeoverse_mininet(satellite)].cmd('ip route')
                            if xEO_network.get_network_address(terminal2_ip, 30) in routes:
                                routing_dict[satellite].append(f"ip route change {xEO_network.get_network_address(terminal2_ip, 30)} dev{commandParts[1]}")
                            else:
                                routing_dict[satellite].append(f"ip route add {xEO_network.get_network_address(terminal2_ip, 30)} dev{commandParts[1]}")
                        else:
                            debug_print(f"We do not need to update this satellite {satellite} because any way it is not in the path", "yellow")

    return {"routing_r": routing_dict, 
            "net": net
            }

def read_config_(config_file):
    # Load configuration from YAML file
    with open(config_file, 'r') as file:
        config = yaml.safe_load(file)

    return config

def debug_print(message, color='green'):
    """Print the message in color if DEBUG_MODE is True."""
    if DEBUG_MODE:
        color_codes = {
            'red': '\033[91m',
            'green': '\033[92m',
            'yellow': '\033[93m',
            'blue': '\033[94m',
            'magenta': '\033[95m',
            'cyan': '\033[96m',
            'white': '\033[97m',
            'end_color': '\033[0m'
        }
        color_code = color_codes.get(color, color_codes['green'])
        print(f"{color_code}{message}{color_codes['end_color']}")

def naming_conversion_mininet_xeoverse(satname):
    if "STARLINK" in satname:
        index = satname.find("STARLINK")
        x_satname = satname[:index + len("STARLINK")] + "-" + satname[index + len("STARLINK"):]
        return x_satname

def naming_conversion_xeoverse_mininet(satname):
    return satname.replace("-", "", 1)

def check_link_exists(net, host1_name, host2_name, intf1, intf2):
    host1 = net.get(host1_name)
    host2 = net.get(host2_name)
    intf1_obj, intf2_obj = "", ""
    if any(intf1 == intf.name for intf in host1.intfList()):
        intf1_obj = host1.intf(intf1)
    if any(intf2 == intf.name for intf in host2.intfList()):
        intf2_obj = host2.intf(intf2)

    if intf1_obj == "" or intf2_obj == "":
        return False
    
    for link in net.links:
        if (link.intf1 == intf1_obj and link.intf2 == intf2_obj) or (link.intf1 == intf2_obj and link.intf2 == intf1_obj):
            return True

    return False

def generate_random_ip():
    return "10.{}.{}.{}".format(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))

def delete_link_of_interface(net, host_name, interface_name, dummy_hostname):
    host = net.get(host_name)
    dummy_h = net.get(dummy_hostname)
    
    interface = host.intf(interface_name)

    for link in net.links:
        if interface in [link.intf1, link.intf2]:
            other_intf = link.intf1 if interface == link.intf2 else link.intf2
                
            if other_intf.node == dummy_h:
                if (link.intf1 == interface and link.intf2 == other_intf) or (link.intf1 == other_intf and link.intf2 == interface):
                    link.delete()
                    debug_print(f"{interface_name} with the dummy host is deleted", color='yellow')

            for intf in host.intfList():
                debug_print(f"after delete - > Interface: {intf.name}, IP: {intf.IP()}", color='red')
    return net

def create_link_between(intf1, intf2, ip1, ip2, net, satellites, timestamp): #net:mininet,satellite:星座物理資料庫

    dummy_h = net.get("dummy11")
    for intf, ip in [(intf1, ip1), (intf2, ip2)]:
        parts = intf.split('-')
        #判斷length=3
        if len(parts) != 3:
            raise ValueError(f"Invalid interface format: {intf}")
        
        host_name, interface = parts[0]+parts[1], parts[2] #把切割完的再合成 ('starlink''1234''eth0')
        x_host_name = naming_conversion_mininet_xeoverse(host_name)  
        host = net.get(host_name) # 透過名稱從 Mininet網路物件中抓取已建立的主機實體
        
        # Ensure previous interfaces exist 用for去檢查前面的介面是否存在(eth0)
        for prev_intf_num in range(int(interface.replace('eth', ''))):
            prev_intf_name = f"{x_host_name}-eth{prev_intf_num}".replace("STARLINK", "STL")
            interfaces = host.intfList()
            if not any(prev_intf_name == intf.name for intf in interfaces):
                net.addLink(host, dummy_h, intfName1=prev_intf_name, cls=TCLink, params1={'ip': generate_random_ip() + '/30'}, params2={'ip': generate_random_ip() + '/30'}, bw=10, delay='5ms')  # Example bandwidth and delay
                #host, dummy_h:把衛星主機先接到dummy
                #intfName1=prev_intf_name:強制將衛星端的網卡命名為我們剛才組裝好的名字
                #連線指定:用 TCLink
                # params1={'ip': generate_random_ip() + '/30'}, params2={'ip': generate_random_ip() + '/30'},為這條連線的兩端隨機產生一個/30的IP。他是假連線但必須有IP才能讓網卡狀態顯示為已啟用
                debug_print(f"{prev_intf_name} interface is added with IP= {host.IP(prev_intf_name)}", color='yellow')


    host1_name, intf1_name = intf1.split('-')[0]+intf1.split('-')[1], intf1.replace("STARLINK", "STL")#名字拆開才能得到mininet的host id
    host2_name, intf2_name = intf2.split('-')[0]+intf2.split('-')[1], intf2.replace("STARLINK", "STL")
    host1 = net.get(host1_name)#呼叫net拿到已經建好的host1,使HOST1變為實體主機
    host2 = net.get(host2_name)

    if len(host1.intfList()) > 0 and any(intf1_name == intf.name for intf in host1.intfList()):#檢查host1身上是否已經有任何網卡,先回傳host1物件到intf,再去判斷intf的內容是否和intf1_name一樣;如果有的話代表intf還接在dummy上 要刪除
        delete_link_of_interface(net, host1_name, intf1_name, "dummy11")#呼叫刪除連線(主機插在dummy上的連線)
    
    if len(host2.intfList()) > 0 and  any(intf2_name == intf.name for intf in host2.intfList()):
        delete_link_of_interface(net, host2_name, intf2_name, "dummy11")
    
    if check_link_exists(net, host1_name, host2_name, intf1_name, intf2_name) == False:
        sat1 = satellites[naming_conversion_mininet_xeoverse(host1_name)]
        sat2 = satellites[naming_conversion_mininet_xeoverse(host2_name)]
        link_latency = x_topo.calculate_satellites_latency_(sat1, sat2, timestamp)#計算link延遲
        link_bw = x_topo.calculate_satellites_bw_(naming_conversion_mininet_xeoverse(host1_name), naming_conversion_mininet_xeoverse(host2_name), timestamp)#計算bw
        net.addLink(host1, host2, intfName1=intf1_name, intfName2=intf2_name, cls=TCLink, params1={'ip': ip1 + '/30'}, params2={'ip': ip2 + '/30'}, bw=link_bw, delay=(str(link_latency)+'ms'))#把實際ISL連線建起來
        #host1, host2:雙方的節點
        #intfName1=intf1_name, intfName2=intf2_name:分別連線的介面
        #params1={'ip': ip1 + '/30'}, params2={'ip': ip2 + '/30'}:分別端點 IP 分配
        debug_print(f"Link between {intf1_name} and {intf2_name} is created with two IP={ip1} and {ip2}")
    else:
        debug_print(f"Link between {intf1_name} and {intf2_name} is already exists with two IP={ip1} and {ip2}", color='yellow')

    # debug_print(f"after add - > {host1.intfList()}", color='yellow')
    # debug_print(f"after add - > {host2.intfList()}", color='yellow')

    for intf in host1.intfList():
        debug_print(f"after add - > Interface: {intf.name}, IP: {intf.IP()}", color='yellow')
    
    for intf in host2.intfList():
        debug_print(f"after add - > Interface: {intf.name}, IP: {intf.IP()}", color='yellow')

    return net

def update_link_parameters(net, satellites, terminals, timestamp, config):
    for link in net.links:
        # Extracting host names and interface names from the link
        if link.intf1 is None or link.intf2 is None:
            continue

        intf1_name = link.intf1.name
        intf2_name = link.intf2.name

        if "dummy" in intf1_name or  "dummy" in intf2_name:
            continue

        host1_name = (intf1_name.split('-eth')[0]).replace("STL-", "STARLINK")
        host2_name = (intf2_name.split('-eth')[0]).replace("STL-", "STARLINK")

        # print(host1_name, host2_name, intf1_name, intf2_name)
        # new_bw, new_latency = 0 , 0

        if host1_name in terminals and "STARLINK" in host2_name:
            # print(">>>>>>", host1_name, host2_name)
            sat2 = satellites[naming_conversion_mininet_xeoverse(host2_name)]
            new_latency = x_topo.calculate_terminal_latency_(sat2, terminals[host1_name], timestamp)
            new_bw_dl = x_topo.calculate_gs_satellite_bw_(sat2, terminals[host1_name], config, timestamp, "downlink")
            new_bw_ul = x_topo.calculate_gs_satellite_bw_(sat2, terminals[host1_name], config, timestamp, "uplink")
            # print("sat2 - downlink", new_bw_dl)
            # print("sat2 - uplink", new_bw_ul)
            new_latency = new_latency/2
            cmd = "tc qdisc change dev {} root netem delay {}ms rate {}mbit".format(intf1_name, new_latency, new_bw_ul)
            link.intf1.node.cmd(cmd)
            cmd = "tc qdisc change dev {} root netem delay {}ms rate {}mbit".format(intf2_name, new_latency, new_bw_dl)
            link.intf2.node.cmd(cmd)

        elif "STARLINK" in host1_name and host2_name in terminals:
            # print(">>>>>>2", host1_name, host2_name)
            sat1 = satellites[naming_conversion_mininet_xeoverse(host1_name)]
            new_latency = x_topo.calculate_terminal_latency_(sat1, terminals[host2_name], timestamp)
            new_bw_dl = x_topo.calculate_gs_satellite_bw_(sat1, terminals[host2_name], config, timestamp, "downlink")
            new_bw_ul = x_topo.calculate_gs_satellite_bw_(sat1, terminals[host2_name], config, timestamp, "uplink")
            # print("sat1 - downlink", new_bw_dl)
            # print("sat1 - uplink", new_bw_ul)
            new_latency = new_latency/2
            cmd = "tc qdisc change dev {} root netem delay {}ms rate {}mbit".format(intf1_name, new_latency, new_bw_dl)
            link.intf1.node.cmd(cmd)
            cmd = "tc qdisc change dev {} root netem delay {}ms rate {}mbit".format(intf2_name, new_latency, new_bw_ul)
            link.intf2.node.cmd(cmd)

        elif "STARLINK" in host1_name and "STARLINK" in host2_name:
            # Calculate new latency and bandwidth for the link
            sat1 = satellites[naming_conversion_mininet_xeoverse(host1_name)]
            sat2 = satellites[naming_conversion_mininet_xeoverse(host2_name)]
            new_latency = x_topo.calculate_satellites_latency_(sat1, sat2, timestamp)
            new_bw = x_topo.calculate_satellites_bw_(naming_conversion_mininet_xeoverse(host1_name), naming_conversion_mininet_xeoverse(host2_name), timestamp)
            new_latency = new_latency/2
            cmd = "tc qdisc change dev {} root netem delay {}ms rate {}mbit".format(intf1_name, new_latency, new_bw)
            link.intf1.node.cmd(cmd)
            cmd = "tc qdisc change dev {} root netem delay {}ms rate {}mbit".format(intf2_name, new_latency, new_bw)
            link.intf2.node.cmd(cmd)
        else:
            print("There is something wrong in the update link paramters function")
            exit()
        
       
        # net.configLinkStatus(host1_name, host2_name, 'down')
        # link.intf1.config(bw=new_bw, delay=f'{new_latency}ms')
        # link.intf2.config(bw=new_bw, delay=f'{new_latency}ms')
        # net.configLinkStatus(host1_name, host2_name, 'up')
        
        # Update link parameters
        # new_latency = new_latency/2
        # cmd = "tc qdisc change dev {} root netem delay {}ms rate {}mbit".format(intf1_name, new_latency, new_bw)
        # link.intf1.node.cmd(cmd)
        # cmd = "tc qdisc change dev {} root netem delay {}ms rate {}mbit".format(intf2_name, new_latency, new_bw)
        # link.intf2.node.cmd(cmd)
        # debug_print(f"Updated link between {intf1_name} and {intf2_name} with BW={new_bw} and Latency={new_latency}ms", color='yellow')
        # if "London" in intf2_name:
        #     cmd = "tc qdisc change dev {} root netem delay {}ms rate {}mbit".format(intf2_name, 400, 30)
        #     link.intf2.node.cmd(cmd)
        # if "London" in intf1_name:
        #     cmd = "tc qdisc change dev {} root netem delay {}ms rate {}mbit".format(intf1_name, 400, 30)
        #     link.intf1.node.cmd(cmd)

        
    return net

def get_available_links_per_sat(sat_name, ip_assignments, satellites):
    links_per_sat = []
    current_sat_ips = satellites[sat_name].neighbors_ip  #先找到鄰居ip

    for ips in current_sat_ips:
        neigh_intf, neigh_ip = xEO_network.find_matching_network_interface(ips, ip_assignments) #利用鄰居ip去ip_assignment找對方的介面
        links_per_sat.append((xEO_network.find_interface_by_ip(ips, ip_assignments), ips, neigh_intf, neigh_ip)) #把本機網卡 本機ip 對向網卡 對向ip 存回link per sat
    
    return links_per_sat

def get_neighbour_satellites(sat_name, satellites):
    neighbours = []
    for sats in satellites[sat_name].east_neighbors:
        neighbours.append(sats)
    for sats in satellites[sat_name].west_neighbors:
        neighbours.append(sats)
    for sats in satellites[sat_name].in_orbit_neighbors:
        neighbours.append(sats)
    
    return neighbours

def apply_routing_commands_in_mininet(net, routing_dict):
    """
    Applies routing commands to corresponding satellite nodes in a Mininet network.

    :param net: The Mininet network instance
    :param routing_dict: Dictionary with satellite nodes as keys and routing commands as values
    """
    for satellite, commands in routing_dict.items():
        m_satellite = naming_conversion_xeoverse_mininet(satellite)
        node = net.getNodeByName(m_satellite)
        if node:
            for cmd in commands:
                node.cmd(cmd)
                # print(f"Applied command to {satellite}: {cmd}")
        else:
            print(f"Satellite node {satellite} not found in the network")
    
    return net

def setup_mininet_topology(satellites, path, ip_assignments, routing_dict, config_file):
    net = Mininet(controller=None, switch=OVSSwitch, link=TCLink)  #初始化 Mininet 物件，設定link使用TCLink
    net.start()
    # Dictionary to hold the Mininet hosts
    hosts = {}   ##原本的衛星
    new_hosts = {}  ##鄰居衛星 
    
    dummy_host = net.addHost(f'dummy11') ##建立虛擬主機 用來暫時連接那些還沒找到對向節點的孤立網卡
    debug_print(path, color='red')
    # Create Mininet hosts for each satellite in the path
    ##用已知的path.json檔內的路徑衛星在mininet裡建起來後存到host{}
    for sat_name in path:
        current_sat_ips = satellites[sat_name].neighbors_ip
        sat_name_ = naming_conversion_xeoverse_mininet(sat_name)
        host = net.addHost(sat_name_)
        hosts[sat_name_] = host
    
    # Create Mininet hosts for the neighbours of the satellites in the path
    for host_name in hosts:  
        neighbours = get_neighbour_satellites(naming_conversion_mininet_xeoverse(host_name), satellites)#這邊會呼叫topology函式中的get_neighbour_satellites
        for x_sats in neighbours:
            sat_name_ = naming_conversion_xeoverse_mininet(x_sats)
            if sat_name_ not in hosts and sat_name_ not in new_hosts:  # Check if the host is not already in the dictionaries
                host = net.addHost(sat_name_)
                new_hosts[sat_name_] = host  ##會被存進新主機中與核心路徑衛星區分開
    
    hosts.update(new_hosts)  ##new host整合進host裡

    # debug_print(hosts)

    #把ISL建起來
    for host_name in hosts:
        debug_print(f"Satellite: {naming_conversion_mininet_xeoverse(host_name)}") #把名字轉到xeoverse板後在終端機印出來)
        linksPerSat = get_available_links_per_sat(naming_conversion_mininet_xeoverse(host_name), ip_assignments, satellites)#呼叫函式去資料庫中抓取這顆衛星所有的連線資訊(衛星名字,ip表,整個衛星的集合)
    #回傳本機網卡 ip 另外一節點的網卡 ip
        for tuples in linksPerSat:#從回傳可用的連線去找
            if naming_conversion_xeoverse_mininet(tuples[0].split("-eth")[0]) in hosts and naming_conversion_xeoverse_mininet(tuples[2].split("-eth")[0]) in hosts: #先把網卡名字切割 檢查發起端衛星與接收端衛星是否都已經被建立在 hosts 字典裡了。
                debug_print(f"Neighbours details: \n \t >> Link-end-1:{tuples[0]} \n \t >> Link-end-2:{tuples[2]} \n \t >> IP 1: {tuples[1]} \n \t >> IP 2: {tuples[3]}") #檢查通過印出連線資訊
                create_link_between(tuples[0], tuples[2], tuples[1], tuples[3], net, satellites, timestamp = datetime(2023, 11, 13, 10, 30, 0)) #開始拉線
            else:
                if naming_conversion_xeoverse_mininet(tuples[0].split("-eth")[0]) not in hosts:
                    debug_print(f"{naming_conversion_xeoverse_mininet(tuples[0].split('-eth')[0])} is not in the path and not directly related to the path .. ignore it", color='red')
                if naming_conversion_xeoverse_mininet(tuples[2].split("-eth")[0]) not in hosts:
                    debug_print(f"{naming_conversion_xeoverse_mininet(tuples[2].split('-eth')[0])} is not in the path and not directly related to the path .. ignore it", color='red')
        debug_print(f"-------------------------------------------------------------------------------------------------", color='white')
        debug_print(f"-------------------------------------------------------------------------------------------------", color='white')

    ########################### Add the ground segments configurations ##########################
    ground_segments = {} #建一個放關於地面站的dict
    config = read_config_(config_file) 
    end1 = config['experiment']['end1'] #讀出config裡的london
    end2 = config['experiment']['end2'] #讀出config裡的Sanfranci

    host_end1 = net.addHost(end1.replace(" ", ""))#建立一個名為host_end1主機
    host_end2 = net.addHost(end2.replace(" ", ""))#建立一個名為host_end1主機
    ground_segments[end1] = host_end1  #把建好的主機存回dict
    ground_segments[end2] = host_end2  #把建好的主機存回dict

    terminal1_ip = xEO_network.find_the_ip_of_interface(end1+"-eth0", ip_assignments) #去ip_assignment找地面站1的ip並存回terminal1_ip;eth0是因為地面站通往衛星只需要一個介面
    sat_intf, sat_ip = xEO_network.find_matching_network_interface(terminal1_ip, ip_assignments)#去呼叫函式搜尋誰跟terminal1_ip位在同一個子網路
    value = ip_assignments.pop(sat_intf, None)#把ip從assignment提取出後刪掉
    net.addLink(host_end1, hosts[naming_conversion_xeoverse_mininet(sat_intf.split("-eth")[0])], intfName1=end1+"-eth0", intfName2=sat_intf.replace("STARLINK", "STL"), cls=TCLink, params1={'ip': terminal1_ip + '/30'}, params2={'ip': value + '/30'}, bw=130, delay='5ms') #跟上面的ISL一樣只是其中一端的link變地面站
    host_end1.cmd(f"route add default gw {value}")#以地面端1去執行加路由規則add route##上行路徑

    terminal2_ip = xEO_network.find_the_ip_of_interface(end2+"-eth0", ip_assignments)
    sat_intf, sat_ip = xEO_network.find_matching_network_interface(terminal2_ip, ip_assignments)
    value = ip_assignments.pop(sat_intf, None)
    net.addLink(host_end2, hosts[naming_conversion_xeoverse_mininet(sat_intf.split("-eth")[0])], intfName1=end2.replace(" ", "")[:-3]+"-eth0", intfName2=sat_intf.replace("STARLINK", "STL"), cls=TCLink, params1={'ip': terminal2_ip + '/30'}, params2={'ip': value + '/30'}, bw=140, delay='5ms')  # Example bandwidth and delay
    host_end2.cmd(f"route add default gw {value}")#指定下行出口

    sat1_ips = xEO_network.find_all_ips_of_sat(path[0], ip_assignments)#找出起點衛星
    sat2_ips = xEO_network.find_all_ips_of_sat(path[len(path)-1], ip_assignments)#找出終點衛星
    for satellite, commands in routing_dict.items():#去routing dict找相對應的指令(ip route add 192.168.26.84/30 via 192.168.1.10 dev STL-1054-eth0)
        for cmd in commands:#cmd是指很多command所組成
            for ip in sat1_ips:#逐一檢查起點衛星(sat1)的ip
                net_ip = xEO_network.get_network_address(ip, 30)#將IP轉換成/30網段地址(因為routing table的目的地主要是以網段儲存但這個ip是具體的位置 所以要先轉網段)
                if net_ip in cmd or ip in cmd:#判斷cmd中的指令是否能匹配ip網段或ip
                    commandParts = cmd.split("dev")#從dev切割開
                    if "via" in commandParts[0]:#(commandParts[0]儲存的是原始指令中目的地網段以及下一跳路徑的部分,eg:ip route add 192.168.26.84/30 via 192.168.1.10)
                        #有via就是靠別人轉發
                        sub_command = commandParts[0].split("via")[1]#( 192.168.1.10:即是中繼衛星的ip)
                        routing_dict[satellite].append(f"ip route add {xEO_network.get_network_address(terminal1_ip, 30)} via{sub_command}dev{commandParts[1]}")#{xEO_network.get_network_address(terminal1_ip, 30)}:將地面站ip轉為網段,讓衛星知道要去哪
                    else:#如果沒有via
                        routing_dict[satellite].append(f"ip route add {xEO_network.get_network_address(terminal1_ip, 30)} dev{commandParts[1]}")#如果沒有via那指令就沒變

            for ip in sat2_ips:
                net_ip = xEO_network.get_network_address(ip, 30)
                if net_ip in cmd or ip in cmd:
                    commandParts = cmd.split("dev")
                    if "via" in commandParts[0]:
                        sub_command = commandParts[0].split("via")[1]
                        routing_dict[satellite].append(f"ip route add {xEO_network.get_network_address(terminal2_ip, 30)} via{sub_command}dev{commandParts[1]}")
                    else:
                        routing_dict[satellite].append(f"ip route add {xEO_network.get_network_address(terminal2_ip, 30)} dev{commandParts[1]}")
    ##############################################################################################
                    
    net = apply_routing_commands_in_mininet(net, routing_dict)
    
    for host in hosts:
        host = net.get(host)
        host.cmd('sysctl net.ipv4.ip_forward=1')
        host.cmd('sysctl -w net.ipv4.conf.all.proxy_arp=1')

    import os
    directory_result   = config['simulation']['directory_results']
    experiment_result  = os.path.join(directory_result, f"results_{config['experiment']['type']}_{config['experiment']['end1']}_config['experiment']['end2']_.log")

    if config['experiment']['type'] == "ping" or config['experiment']['type'] == "Ping":
        end1_s = config['experiment']['end1'].replace(" ","")
        end2_s = config['experiment']['end2'].replace(" ","")
        command = f"ping -c {config['experiment']['duration_seconds']} {terminal2_ip} >> results_{config['experiment']['type']}_{end1_s}_{end2_s}_.log"
        result = host_end1.cmd(command)
        print(result)
    if config['experiment']['type'] == "iperf" or config['experiment']['type'] == "Iperf":
        end1_s = config['experiment']['end1'].replace(" ","")
        end2_s = config['experiment']['end2'].replace(" ","")

        command1 = f"iperf -c {terminal2_ip} -C {config['experiment']['cc']} -i1 -t {config['experiment']['duration_seconds']} >> results_{config['experiment']['type']}_{end1_s}_{end2_s}_.log 2>&1 &"
        command2 = f"iperf -s &"

        result = host_end2.cmd(command2)
        result = host_end1.cmd(command1)
        print(result)
    # else:
    #     print("The experiment type is not supported. xEOVerse only support ping and iperf experiments")
    # Run CLI for interactive commands
    # CLI(net)

    # After CLI - stop the network
    # net.stop()


def _mininet_topology(satellites, path, ip_assignments, routing_dict, config_file):
    net = Mininet(controller=None, switch=OVSSwitch, link=TCLink)
    net.start()
    # Dictionary to hold the Mininet hosts
    hosts = {}
    new_hosts = {}
    
    dummy_host = net.addHost(f'dummy11')
    debug_print(path, color='red')
    # Create Mininet hosts for each satellite in the path
    for sat_name in path:
        current_sat_ips = satellites[sat_name].neighbors_ip
        sat_name_ = naming_conversion_xeoverse_mininet(sat_name)
        host = net.addHost(sat_name_)
        hosts[sat_name_] = host
    
    # Create Mininet hosts for the neighbours of the satellites in the path
    for host_name in hosts:
        neighbours = get_neighbour_satellites(naming_conversion_mininet_xeoverse(host_name), satellites)
        for x_sats in neighbours:
            sat_name_ = naming_conversion_xeoverse_mininet(x_sats)
            if sat_name_ not in hosts and sat_name_ not in new_hosts:  # Check if the host is not already in the dictionaries
                host = net.addHost(sat_name_)
                new_hosts[sat_name_] = host
    
    hosts.update(new_hosts)

    # debug_print(hosts)
    
    for host_name in hosts:
        debug_print(f"Satellite: {naming_conversion_mininet_xeoverse(host_name)}")
        linksPerSat = get_available_links_per_sat(naming_conversion_mininet_xeoverse(host_name), ip_assignments, satellites)

        for tuples in linksPerSat:
            if naming_conversion_xeoverse_mininet(tuples[0].split("-eth")[0]) in hosts and naming_conversion_xeoverse_mininet(tuples[2].split("-eth")[0]) in hosts:
                debug_print(f"Neighbours details: \n \t >> Link-end-1:{tuples[0]} \n \t >> Link-end-2:{tuples[2]} \n \t >> IP 1: {tuples[1]} \n \t >> IP 2: {tuples[3]}")
                create_link_between(tuples[0], tuples[2], tuples[1], tuples[3], net, satellites, timestamp = datetime(2023, 11, 13, 10, 30, 0))
            else:
                if naming_conversion_xeoverse_mininet(tuples[0].split("-eth")[0]) not in hosts:
                    debug_print(f"{naming_conversion_xeoverse_mininet(tuples[0].split('-eth')[0])} is not in the path and not directly related to the path .. ignore it", color='red')
                if naming_conversion_xeoverse_mininet(tuples[2].split("-eth")[0]) not in hosts:
                    debug_print(f"{naming_conversion_xeoverse_mininet(tuples[2].split('-eth')[0])} is not in the path and not directly related to the path .. ignore it", color='red')
        debug_print(f"-------------------------------------------------------------------------------------------------", color='white')
        debug_print(f"-------------------------------------------------------------------------------------------------", color='white')

    ########################### Add the ground segments configurations ##########################
    ground_segments = {}
    config = read_config_(config_file)
    end1 = config['experiment']['end1']
    end2 = config['experiment']['end2']

    host_end1 = net.addHost(end1.replace(" ", ""))
    host_end2 = net.addHost(end2.replace(" ", ""))
    ground_segments[end1] = host_end1
    ground_segments[end2] = host_end2

    routing_output_groundS = add_routing_for_ground_segments(net, host_end1, host_end2, end1, end2, ip_assignments, routing_dict, hosts, path)
    net = routing_output_groundS["net"]
    routing_dict = routing_output_groundS["routing_r"]

    ##############################################################################################
    net = apply_routing_commands_in_mininet(net, routing_dict)
    
    for host in hosts:
        host = net.get(host)
        host.cmd('sysctl net.ipv4.ip_forward=1')
        host.cmd('sysctl -w net.ipv4.conf.all.proxy_arp=1')

    import os
    directory_result   = config['simulation']['directory_results']
    experiment_result  = os.path.join(directory_result, f"results_{config['experiment']['type']}_{config['experiment']['end1']}_config['experiment']['end2']_.log")
    terminal2_ip = xEO_network.find_the_ip_of_interface(end2+"-eth0", ip_assignments)
    if config['experiment']['type'] == "ping" or config['experiment']['type'] == "Ping":
        
        end1_s = config['experiment']['end1'].replace(" ","")
        end2_s = config['experiment']['end2'].replace(" ","")
        command = f"ping -c {config['experiment']['duration_seconds']} {terminal2_ip} >> results_{config['experiment']['type']}_{end1_s}_{end2_s}_.log &"
        result = host_end1.cmd(command)
        print(result)
    if config['experiment']['type'] == "iperf" or config['experiment']['type'] == "Iperf":
        end1_s = config['experiment']['end1'].replace(" ","")
        end2_s = config['experiment']['end2'].replace(" ","")

        command1 = f"iperf -c {terminal2_ip} -i1 -t {config['experiment']['duration_seconds']} >> results_{config['experiment']['type']}_{end1_s}_{end2_s}_.log &"
        command2 = f"iperf -s &"

        result = host_end2.cmd(command2)
        result = host_end1.cmd(command1)
        print(result)
    else:
        print("The experiment type is not supported. xEOVerse only support ping and iperf experiments")
    # Run CLI for interactive commands
    CLI(net)

    # After CLI - stop the network
    net.stop()


    ############################# Mininet Loop ############################
    import os
    config = read_config_(config_file)

    start_time                  = datetime.strptime(config['simulation']['start_time'], '%Y-%m-%d %H:%M:%S')
    step_seconds                = config['simulation']['step_seconds']
    simulation_length_seconds   = config['simulation']['simulation_length_seconds']
    end_time                    = start_time + timedelta(seconds=simulation_length_seconds)
    directory_result            = config['simulation']['directory_results']

    formatted_start_time        = start_time.strftime("%Y%m%d_%H%M%S")
    main_directory              = directory_result.replace('{date}', formatted_start_time)

    connectivity_directory      = os.path.join(main_directory, f"connectivity_matrices_{formatted_start_time}")
    satellite_directory         = os.path.join(main_directory, f"satellites_{formatted_start_time}")

    terminals                   = x_pre.read_terminals(config['terminal_data']['path'])
    print(terminals)
    
    current_time = start_time + timedelta(seconds=1)
    import time
    print(current_time, end_time)
    output = x_pre.extract_required_data(start_time, start_time)
    sss_time = time.time()
    while current_time < end_time:
        s_time = time.time()

        formatted_timestamp         = current_time.strftime("%Y%m%d_%H%M%S")
        dir_routing                 = f"routing_configs_{formatted_timestamp}"
                   
        routing_directory           = [os.path.join(root, d) for root, dirs, _ in os.walk(main_directory) for d in dirs if dir_routing in d]
        routing_directory = routing_directory[0]
        # print(routing_directory, current_time)
        if "NOM" in routing_directory:
            net = update_link_parameters(net, output["satellites"], terminals, current_time, config)

        else:
            # print("there is change in ISL or GSL")
            # print(current_time, start_time)
            output = x_pre.extract_required_data(current_time, start_time)  

            new_nodes = config_new_satellite_to_mininet(net, hosts, output)
            net = new_nodes["net"]
            hosts = new_nodes["hosts"]
            changes_in_path = x_pre.does_path_change(main_directory, current_time)

            if len(changes_in_path) > 0:
                print("this is when the path changes:", changes_in_path)
                routing_output_groundS = add_routing_for_ground_segments(net, host_end1, host_end2, end1, end2, output["ip_assignment"], output["routing"], hosts, output["path"])
                net = routing_output_groundS["net"]
                routing_dict = routing_output_groundS["routing_r"]

            else:
                debug_print(f"No changes in the path between {end1} and {end2} ...", "green")
                routing_dict = output["routing"]

            # print("------------------------------Before------------------------------")
            # for satellite, routes in routing_dict.items():
            #     print(satellite, len(routes))
            routing_dict = x_pre.add_other_nets_to_routing(routing_dict, output["ip_assignment"])
            # print("------------------------------AFTER------------------------------")
            # for satellite, routes in routing_dict.items():
            #     print(satellite, len(routes))
            # print("------------------------------------------------------------")
            net = apply_routing_commands_in_mininet(net, routing_dict)
            
    
        
        # Calculate elapsed time
        elapsed_time = time.time() - s_time
        if elapsed_time < 1:
            time.sleep(1 - elapsed_time)
        
        print(routing_directory, current_time, "this loop time=", time.time()-s_time)
        # print("time is -> ", time.time()-s_time)
        current_time += timedelta(seconds=step_seconds)
        # time.sleep(step_seconds)  # Sleep for step_seconds
    
    # Run CLI for interactive commands
    # CLI(net)

    # After CLI - stop the network
    # net.stop()
    e_time = time.time()
    print("The  time = ", (e_time-sss_time))


def config_new_satellite_to_mininet(net, hosts, output):
    new_hosts1 = {}
    for sat_name in output["path"]:
        sat_name_ = naming_conversion_xeoverse_mininet(sat_name)
        # print(sat_name_)
        if sat_name_ not in hosts:
            # print(sat_name_)
            host = net.addHost(sat_name_)
            hosts[sat_name_] = host
            new_hosts1[sat_name_] = host

    new_hosts2 = {}
    for host_name in new_hosts1:
        neighbours = get_neighbour_satellites(naming_conversion_mininet_xeoverse(host_name), output["satellites"])
        for x_sats in neighbours:
            sat_name_ = naming_conversion_xeoverse_mininet(x_sats)
            if sat_name_ not in hosts and sat_name_ not in new_hosts2:  # Check if the host is not already in the dictionaries
                # print("nei", sat_name_)
                host = net.addHost(sat_name_)
                new_hosts2[sat_name_] = host
    
    hosts.update(new_hosts1)
    hosts.update(new_hosts2)
    new_hosts1.update(new_hosts2)

    for host in hosts:
        host = net.get(host)
        host.cmd('sysctl net.ipv4.ip_forward=1')
        host.cmd('sysctl -w net.ipv4.conf.all.proxy_arp=1')

    for host_name in new_hosts1:
        debug_print(f"Satellite: {naming_conversion_mininet_xeoverse(host_name)}")
        linksPerSat = get_available_links_per_sat(naming_conversion_mininet_xeoverse(host_name), output["ip_assignment"], output["satellites"])

        for tuples in linksPerSat:
            if naming_conversion_xeoverse_mininet(tuples[0].split("-eth")[0]) in hosts and naming_conversion_xeoverse_mininet(tuples[2].split("-eth")[0]) in hosts:
                debug_print(f"Neighbours details: \n \t >> Link-end-1:{tuples[0]} \n \t >> Link-end-2:{tuples[2]} \n \t >> IP 1: {tuples[1]} \n \t >> IP 2: {tuples[3]}")
                create_link_between(tuples[0], tuples[2], tuples[1], tuples[3], net, output["satellites"], timestamp = datetime(2023, 11, 13, 10, 30, 0))
            else:
                if naming_conversion_xeoverse_mininet(tuples[0].split("-eth")[0]) not in hosts:
                    debug_print(f"{naming_conversion_xeoverse_mininet(tuples[0].split('-eth')[0])} is not in the path and not directly related to the path .. ignore it", color='red')
                if naming_conversion_xeoverse_mininet(tuples[2].split("-eth")[0]) not in hosts:
                    debug_print(f"{naming_conversion_xeoverse_mininet(tuples[2].split('-eth')[0])} is not in the path and not directly related to the path .. ignore it", color='red')
        debug_print(f"-------------------------------------------------------------------------------------------------", color='white')
        debug_print(f"-------------------------------------------------------------------------------------------------", color='white')

    return {"hosts": hosts,
            "net": net
            }


setLogLevel('info')
