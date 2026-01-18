import x_topology.constellation_topology as xEO_topology
import x_routing.constellation_routing as xEO_route
import x_net.constellation_network as xEO_network
import x_substrate.constellation_mininet as xEO_mininet

from datetime import datetime
from skyfield.api import Topos
import time 

f = open('/home/linux/xeoverse/tle.txt')
tle_data = f.read()
topology_structure = "cross-orbit"  # or "in-orbit"
num_links = 3  # Number of cross-links
max_distance = 5000  # Maximum link distance in kilometers
inclination_tolerance = 0.06  # Tolerance for inclination
target_inclination = 53.0
raan_tolerance = 1.0  # Tolerance for RAAN
raan_step = 5.0  # Step for RAAN rounding
timestamp = datetime(2023, 11, 13, 10, 30, 0)

terminals = {
    "San Francisco": Topos(latitude_degrees=37.7749, longitude_degrees=-122.4194),  # San Francisco, for example
    "Lagos": Topos(latitude_degrees=9.548318418209965, longitude_degrees=-7.995127754089786),  # Nigeria, for example
    "London": Topos(latitude_degrees=51.5074, longitude_degrees=-0.1278),   # London, for example
    # Add more gateways as needed
}
# start_T = time.time()*1000
# start_t = time.time()*1000
xTP = xEO_topology.generate_connectivity_matrix(tle_data, topology_structure, num_links, max_distance, inclination_tolerance, target_inclination, raan_tolerance, raan_step, timestamp)
# satellites, t = xEO_topology.load_satellite_data(tle_data, inclination_tolerance, target_inclination, timestamp)
total_links = xEO_topology.count_links_in_connectivity_matrix(xTP["matrix"])
# print((xTP["satellites"]["STARLINK-1976"]))\\

# print(len( xTP["satellites"]))
# exit()
satellite_info_list = []

for sat_name, sat_obj in xTP["satellites"].items():
    satellite_info = {
        "name": sat_name,
        "index": sat_obj.index,
        "west_neighbors": ', '.join(sat_obj.west_neighbors) if sat_obj.west_neighbors else 'None',
        "east_neighbors": ', '.join(sat_obj.east_neighbors) if sat_obj.east_neighbors else 'None',
        "in_orbit_neighbors": ', '.join(sat_obj.in_orbit_neighbors) if sat_obj.in_orbit_neighbors else 'None'
    }
    satellite_info_list.append(satellite_info)

satellite_info_list.sort(key=lambda x: x["index"])
for sat_info in satellite_info_list:
    print(f"Satellite Name: {sat_info['name']}")
    print(f"Index: {sat_info['index']}")
    print(f"West Neighbors: {sat_info['west_neighbors']}")
    print(f"East Neighbors: {sat_info['east_neighbors']}")
    print(f"In-Orbit Neighbors: {sat_info['in_orbit_neighbors']}")
    print("------------------------------------------------------")
    
# for sat_name, sat_obj in xTP["satellites"].items():
#     # Assuming sat_obj has attributes like name, index, west_neighbors, east_neighbors, and in_orbit_neighbors
#     print(f"Satellite Name: {sat_name}")
#     print(f"Index: {sat_obj.index}")
#     print(f"West Neighbors: {', '.join(sat_obj.west_neighbors) if sat_obj.west_neighbors else 'None'}")
#     print(f"East Neighbors: {', '.join(sat_obj.east_neighbors) if sat_obj.east_neighbors else 'None'}")
#     print(f"In-Orbit Neighbors: {', '.join(sat_obj.in_orbit_neighbors) if sat_obj.in_orbit_neighbors else 'None'}")
#     print("------------------------------------------------------")

# print(xEO_topology.print_indices_of_ones(xTP["mx"], xTP["name2index"]))

# t = xEO_topology.convert_to_skyfield_time(timestamp)
# print(xEO_topology.is_satellite_east_or_west("STARLINK-1748", "STARLINK-2648", xTP["sats"], t))
# print(xEO_topology.is_satellite_east_or_west("STARLINK-1748", "STARLINK-2649", xTP["sats"], t))
# print(xEO_topology.is_satellite_east_or_west("STARLINK-1748", "STARLINK-1375", xTP["sats"], t))
# print(xEO_topology.is_satellite_east_or_west("STARLINK-1748", "STARLINK-1377", xTP["sats"], t))
# print(xTP["sats"])
# xEO_topology.is_satellite_east_or_west()
# exit()
# print(satellites)
required_ips = 2 * total_links
subnet_mask = xEO_network.find_smallest_subnet_mask_for_subnets(required_ips)
ip_subnet = f"192.168.0.0/{subnet_mask}"

# link_assignments = xEO_network.distribute_ip_addresses(xTP["mx"], xTP["name2index"], ip_subnet)

# ip_assignments = xEO_network.distribute_ip_addresses(xTP["mx"], xTP["name2index"], ip_subnet)

# Output the result
# print(link_assignments)

# print("Total number of links:", total_links)


# satellites, t = xEO_topology.load_satellite_data(tle_data, inclination_tolerance, target_inclination, timestamp)
path = xEO_route.find_shortest_path_between_terminals(xTP["matrix"], terminals, "London", "San Francisco", xTP["satellites"], timestamp)
print(path)
exit()
# print(xEO_topology.calculate_total_latency(path, xTP["satellites"], terminals, timestamp))
# end_T = time.time()*1000
# print(end_T-start_T)
# exit()
# print(path)
# end_t = time.time()*1000
# print("Shortest path:", path, len(path), (end_t-start_t))

new_satellites = xEO_network.distribute_ip_addresses(xTP["matrix"], xTP["satellites"], ip_subnet)
ip_assignment = xEO_network.extract_ips(new_satellites)
# for interface, ip in ip_assignment.items():
#     print(f"Interface: {interface}, IP Address: {ip}")
# routing = xEO_network.generate_routing_commands(path, new_satellites, ip_assignment)
# print(routing)

# routing_r = xEO_network.recursive_generate_routing_commands(path, new_satellites, ip_assignment)
routing_r = xEO_network.recursive_generate_routing_commands_(path, new_satellites, ip_assignment)

for satellite, routes in routing_r.items():
    print(f"{satellite}: {len(routes)} routes")
    

# print(routing_r)

xEO_mininet.setup_mininet_topology(new_satellites, path, ip_assignment, routing_r)
# xEO_network.print_satellite_neighbors_and_ips(new_satellites)
# print(xEO_network.distribute_ip_addresses(xTP["matrix"], xTP["satellites"], ip_subnet))
# (adjacency_matrix, terminals, start_terminal, end_terminal, satellites, timestamp):
# # # Example Usage
# interface_counts = xEO_network.map_satellites_to_interface_counts(xTP["mx"], xTP["name2index"])
# satellite_name = 'STARLINK-30700'  # Example satellite name

# interfaces_info = xEO_network.get_satellite_interfaces(satellite_name, xTP["mx"], xTP["name2index"], link_assignments, interface_counts)
# print(interfaces_info)


