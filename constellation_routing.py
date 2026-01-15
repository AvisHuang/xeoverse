import heapq
import x_topology.constellation_topology as x_tp

def find_shortest_path(adjacency_matrix, start_sat, end_sat, criteria, satellites, latency_matrix=None, throughput_matrix=None):
    # Verify input types and extract indices
    start_idx = satellites[start_sat].index
    end_idx = satellites[end_sat].index

    # Reverse mapping from indices to satellite names
    index_to_name = {sat_obj.index: name for name, sat_obj in satellites.items()}

    # Convert adjacency matrix to a graph in the form of a dictionary
    num_sats = len(adjacency_matrix)
    graph = {i: {} for i in range(num_sats)}
    for idx1 in range(num_sats):
        for idx2, connected in enumerate(adjacency_matrix[idx1]):
            if connected == 1:
                latency = latency_matrix[idx1][idx2] if latency_matrix else 1
                throughput = throughput_matrix[idx1][idx2] if throughput_matrix else 1
                graph[idx1][idx2] = (latency, throughput)

    # Dijkstra's algorithm
    path_indices = dijkstra_shortest_path(graph, start_idx, end_idx, criteria)
    
    # Convert indices in the path to satellite names
    path_names = [index_to_name[idx] for idx in path_indices]
    return path_names


def dijkstra_shortest_path(graph, start_idx, end_idx, criteria):
    priority_queue = [(0, start_idx)]
    distances = {node: float('infinity') for node in graph}
    distances[start_idx] = 0
    previous_nodes = {node: None for node in graph}

    while priority_queue:
        current_distance, current_node = heapq.heappop(priority_queue)
        if current_node == end_idx:
            break

        # Error handling for missing nodes
        if current_node not in graph:
            raise ValueError(f"Node {current_node} not found in graph")

        for neighbor, edge_info in graph[current_node].items():
            latency, throughput = edge_info
            distance = calculate_distance(current_distance, latency, throughput, criteria)

            if distance < distances[neighbor]:
                distances[neighbor] = distance
                previous_nodes[neighbor] = current_node
                heapq.heappush(priority_queue, (distance, neighbor))

    path = []
    current = end_idx
    while current is not None:
        path.append(current)
        current = previous_nodes[current]
    path.reverse()

    return path if path[0] == start_idx else []

def calculate_distance(current_distance, latency, throughput, criteria):
    if criteria == "Hop":
        return current_distance + 1
    elif criteria == "Latency":
        return current_distance + latency
    elif criteria == "Throughput":
        return max(current_distance, throughput)

def find_shortest_path_between_terminals(adjacency_matrix, terminals, start_terminal, end_terminal, satellites, timestamp):
    # Find the nearest satellites to the start and end terminals
    terminal_connections = x_tp.connect_terminals_to_satellites(terminals, satellites, timestamp)
    start_satellite, _ = terminal_connections[start_terminal]
    end_satellite, _ = terminal_connections[end_terminal]
    # print(start_satellite, end_satellite)
    if start_satellite is None or end_satellite is None:
        raise ValueError("One or both terminals do not have a connected satellite.")

    return find_shortest_path(adjacency_matrix, start_satellite, end_satellite, "Hop", satellites)
