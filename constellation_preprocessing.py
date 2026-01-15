import time
from datetime import datetime, timedelta
import json
import numpy as np
import os
import shutil
from skyfield.api import Topos
import re

import x_topology.constellation_topology as xEO_topology
import x_routing.constellation_routing as xEO_route
import x_net.constellation_network as xEO_network
import x_substrate.constellation_mininet as xEO_mini

import yaml

def does_path_change(directory, timestamp):
    formatted_previous_time =  (timestamp - timedelta(seconds=1)).strftime("%Y%m%d_%H%M%S")
    formatted_current_time = timestamp.strftime("%Y%m%d_%H%M%S")

    file_path_path = os.path.join(directory, f"path_{formatted_current_time}.json")
    with open(file_path_path, 'r') as file:
        path_current = json.load(file)
    
    file_path_path = os.path.join(directory, f"path_{formatted_previous_time}.json")
    with open(file_path_path, 'r') as file:
        path_prev = json.load(file)

    changes = [item for item in path_current if item not in path_prev]

    return changes


def extract_required_data(timestamp, start_time):
    f = open("./tle.txt")
    tle_data = f.read()
    formatted_start_time = start_time.strftime("%Y%m%d_%H%M%S")
    formatted_timestamp = timestamp.strftime("%Y%m%d_%H%M%S")
    routing_r = {}

    directory = f"results_{formatted_start_time}"
    directory_satellites = f"results_{formatted_start_time}/satellites_{formatted_start_time}"
    # directory_routing = f"results_{formatted_start_time}/routing_configs_{formatted_start_time}"


    directory_routing = f"routing_configs_{formatted_timestamp}"
    directory_path = [os.path.join(root, d) for root, dirs, _ in os.walk(directory) for d in dirs if directory_routing in d]
    directory_path = directory_path[0]
    satellites_file = os.path.join(directory_satellites, f'satellites_{formatted_timestamp}.json')
    file_path_ips = os.path.join(directory, f"constellation_ip_addresses_{formatted_timestamp}.json")
    file_path_path = os.path.join(directory, f"path_{formatted_timestamp}.json")

    with open(file_path_ips, 'r') as file:
        ip_assignment = json.load(file)

    with open(file_path_path, 'r') as file:
        path = json.load(file)

    reconstructed_satellites_dict = xEO_topology.reconstruct_satellite_dict(satellites_file, tle_data)
    reconstructed_satellites_dict = xEO_network.read_ips_from_file_to_satellite(reconstructed_satellites_dict, ip_assignment)

    for filename in os.listdir(directory_path):
        if filename.endswith('.sh'):
            satellite_name = filename.replace('.sh', '')

            # Read the contents of the file
            with open(os.path.join(directory_path, filename), 'r') as file:
                commands = [line.strip() for line in file if 'ip route add' in line or 'ip route delete' in line]
            
            # Add the commands to the dictionary
            routing_r[satellite_name] = commands

    return {"satellites": reconstructed_satellites_dict,
            "path": path,
            "ip_assignment": ip_assignment,
            "routing": routing_r
    }

def copy_data_with_new_timestamp(prev_timestamp, current_timestamp, directory):
    # File names for the previous timestamp
    prev_file_path_ips = os.path.join(directory, f"constellation_ip_addresses_{prev_timestamp}.json")
    prev_file_path_path = os.path.join(directory, f"path_{prev_timestamp}.json")

    # File names for the current timestamp
    current_file_path_ips = os.path.join(directory, f"constellation_ip_addresses_{current_timestamp}.json")
    current_file_path_path = os.path.join(directory, f"path_{current_timestamp}.json")

    # Copy data for IP addresses
    with open(prev_file_path_ips, 'r') as file:
        ip_data = json.load(file)
    with open(current_file_path_ips, 'w') as file:
        json.dump(ip_data, file, indent=4)

    # Copy data for path
    with open(prev_file_path_path, 'r') as file:
        path_data = json.load(file)
    with open(current_file_path_path, 'w') as file:
        json.dump(path_data, file, indent=4)

    print(f"Data copied to new files with timestamp {current_timestamp}")

def copy_folder_with_new_timestamp(prev_folder, new_timestamp, base_directory):
    # Construct the new folder name with the new timestamp
    new_folder_name = f"{prev_folder}_{new_timestamp}"
    new_folder_path = os.path.join(base_directory, new_folder_name)

    # Copy the entire contents of the old folder to the new folder
    shutil.copytree(os.path.join(base_directory, prev_folder), new_folder_path)

    print(f"Folder '{prev_folder}' copied to '{new_folder_name}'")

def create_routing_configs(satellite_dict, parent_directory, timestamp):
    # Create the directory for routing configs if it doesn't exist
    directory = f"routing_configs_{timestamp}"
    directory_path = os.path.join(parent_directory, directory)
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)
    else:
        shutil.rmtree(directory_path)
        os.makedirs(directory_path)
        print(f"This {directory_path} directory already exists. So it is deleted and recreated.")

    # Iterate through the satellite dictionary
    for satellite, commands in satellite_dict.items():
        # Create a bash file for each satellite
        file_path = os.path.join(directory_path, f"{satellite}.sh")
        with open(file_path, 'w') as file:
            file.write("#!/bin/bash\n\n")
            # Write each command to the bash file
            for command in commands:
                file.write(command + "\n")

def read_terminals(file_path):
    terminals = {}
    with open(file_path, 'r') as file:
        for line in file:
            parts = line.strip().split(',')
            if len(parts) == 4:
                city, lat, lon, el = parts[0], float(parts[1]), float(parts[2]), float(parts[3])
                terminals[city] = Topos(latitude_degrees=lat, longitude_degrees=lon, elevation_m=el)
    return terminals

def read_config(config_file):
    # Load configuration from YAML file
    with open(config_file, 'r') as file:
        config = yaml.safe_load(file)

    return config

def compare_adjacency_matrices(file_path1, file_path2):
    # Load the first adjacency matrix
    with open(file_path1, 'r') as file:
        adjacency_matrix_list1 = json.load(file)

    adjacency_matrix1 = np.array(adjacency_matrix_list1)

    # Load the second adjacency matrix
    with open(file_path2, 'r') as file:
        adjacency_matrix_list2 = json.load(file)

    adjacency_matrix2 = np.array(adjacency_matrix_list2)

    # Check if the matrices have the same shape
    if adjacency_matrix1.shape != adjacency_matrix2.shape:
        print("The adjacency matrices have different shapes and cannot be compared.")
        return

    # Initialize a list to record the indexes where the matrices differ
    differing_indexes = []

    # Compare the two matrices and record differing indexes
    for i in range(adjacency_matrix1.shape[0]):
        for j in range(adjacency_matrix1.shape[1]):
            if adjacency_matrix1[i, j] != adjacency_matrix2[i, j]:
                differing_indexes.append((i, j, adjacency_matrix1[i, j]))

    # Print results
    if not differing_indexes:
        print("The adjacency matrices are identical.")
    else:
        print("The adjacency matrices are not identical.")
        print("Differing indexes:", differing_indexes)

    return differing_indexes

def preprocessing_main(config_file):
    config = read_config(config_file)

    # Parse the simulation parameters
    start_time = datetime.strptime(config['simulation']['start_time'], '%Y-%m-%d %H:%M:%S')
    # print(start_time)
    step_seconds = config['simulation']['step_seconds']
    simulation_length_seconds = config['simulation']['simulation_length_seconds']
    end_time = start_time + timedelta(seconds=simulation_length_seconds)

    # Other parameters
    num_links = config['parameters']['isl_links']
    topology_structure = config['parameters']['topology_structure']
    max_distance = config['parameters']['isl_max_distance_km']
    inclination_tolerance = config['parameters']['inclination_tolerance']
    target_inclination = config['parameters']['target_inclination']
    raan_tolerance = config['parameters']['raan_tolerance']
    raan_step = config['parameters']['raan_step']

    f = open(config['tle_data']['path'])
    tle_data = f.read()

    print(f"Simulation Parameters:\n"
      f"  Start Time: {start_time}\n"
      f"  Step Seconds: {step_seconds}\n"
      f"  Simulation Length (seconds): {simulation_length_seconds}\n"
      f"  End Time: {end_time}\n\n"
      f"Other Parameters:\n"
      f"  Number of ISL Links: {num_links}\n"
      f"  Topology Structure: {topology_structure}\n"
      f"  Maximum ISL Distance (km): {max_distance}\n"
      f"  Inclination Tolerance: {inclination_tolerance}\n"
      f"  Target Inclination: {target_inclination}\n"
      f"  RAAN Tolerance: {raan_tolerance}\n"
      f"  RAAN Step: {raan_step}\n\n"
      f"TLE Data Path: {config['tle_data']['path']}")
    # exit()
    directory_result = config['simulation']['directory_results']

    # Format start time and replace in directory pattern
    formatted_start_time = start_time.strftime("%Y%m%d_%H%M%S")
    directory = directory_result.replace('{date}', formatted_start_time)
    if not os.path.exists(directory):
        os.makedirs(directory)
    else:
        shutil.rmtree(directory)
        os.makedirs(directory)
        print(f"This {directory} directory already exists. So it is deleted and recreated.")

    # Define the parent directory and the child directory
    child_directory1 = f"connectivity_matrices_{formatted_start_time}"
    child_directory2 = f"satellites_{formatted_start_time}"
    # Combine the parent and child directories to form the complete path
    directory_c1 = os.path.join(directory, child_directory1)
    if not os.path.exists(directory_c1):
        os.makedirs(directory_c1)
    else:
        shutil.rmtree(directory_c1)
        os.makedirs(directory_c1)
        print(f"This {directory_c1} directory already exists. So it is deleted and recreated.")
    
    directory_c2 = os.path.join(directory, child_directory2)
    if not os.path.exists(directory_c2):
        os.makedirs(directory_c2)
    else:
        shutil.rmtree(directory_c2)
        os.makedirs(directory_c2)
        print(f"This {directory_c2} directory already exists. So it is deleted and recreated.")

    # Simulation loop
    current_time = start_time
    while current_time < end_time:
        formatted_timestamp = current_time.strftime("%Y%m%d_%H%M%S")
        result = xEO_topology.generate_connectivity_matrix(tle_data, topology_structure, num_links, max_distance, inclination_tolerance, target_inclination, raan_tolerance, raan_step, current_time)

        adjacency_matrix = result["matrix"]
        satellites = result["satellites"]
        # Convert the numpy array to a list of lists for JSON serialization
        adjacency_matrix_list = adjacency_matrix.tolist()
        # Save the adjacency matrix to a file
        with open(os.path.join(directory_c1, f'adjacency_matrix_{formatted_timestamp}.json'), 'w') as file:
            json.dump(adjacency_matrix_list, file)

        satellites_data = [satellites[sat].to_dict() for sat in satellites]
        # print(len(satellites_data))
        with open(os.path.join(directory_c2, f'satellites_{formatted_timestamp}.json'), 'w') as file:
            json.dump(satellites_data, file)
        
        # Print a confirmation message
        print(f"Data saved for timestamp {formatted_timestamp} in directory '{directory}'")

        # Increment time for next iteration
        current_time += timedelta(seconds=step_seconds)
        time.sleep(step_seconds)  # Sleep for step_seconds

def copy_file(src, dst):
    with open(src, 'rb') as fsrc:
        with open(dst, 'wb') as fdst:
            fdst.write(fsrc.read())

def no_changes_in_topology(timestamp, directory, gsl_changed):
    # Convert the timestamp string to a datetime object
    previous_timestamp = timestamp - timedelta(seconds=1)

    current_timestamp = timestamp.strftime('%Y%m%d_%H%M%S')
    formatted_previous_timestamp = previous_timestamp.strftime('%Y%m%d_%H%M%S')

    file_path_ips = os.path.join(directory, f"constellation_ip_addresses_{current_timestamp}.json")
    file_path_ips_previous = os.path.join(directory, f"constellation_ip_addresses_{formatted_previous_timestamp}.json")

    file_path_path = os.path.join(directory, f"path_{current_timestamp}.json")
    file_path_path_previous = os.path.join(directory, f"path_{formatted_previous_timestamp}.json")

    if gsl_changed == -1:
        copy_file(file_path_ips_previous, file_path_ips)
        copy_file(file_path_path_previous, file_path_path)


    directory_r_n = f"routing_configs_{current_timestamp}_NOM"
    directory_path_new = os.path.join(directory, directory_r_n)
    directory_r_o = f"routing_configs_{formatted_previous_timestamp}"

    for item in os.listdir(directory):
        item_path = os.path.join(directory, item)
        if os.path.isdir(item_path) and directory_r_o in item:
            # Copy the entire contents of the old directory to the new directory
            shutil.copytree(item_path, directory_path_new)
            print(f"Copied contents of '{item}' to '{directory_path_new}'")
            break


def check_changes_in_gsl(timestamp, directory, current_path):
    
    previous_timestamp = timestamp - timedelta(seconds=1)

    formatted_previous_timestamp = previous_timestamp.strftime('%Y%m%d_%H%M%S')
    file_path_path_previous = os.path.join(directory, f"path_{formatted_previous_timestamp}.json")

    with open(file_path_path_previous, 'r') as f:
        old_path = json.load(f)

    # Check if either the first or last satellites are different
    if old_path[0] != current_path[0]:
        return 0
    elif old_path[-1] != current_path[-1]:
        return len(current_path)
    
    return -1

def precompute_routing(config_file):
    config = read_config(config_file)

     # Parse the simulation parameters
    start_time = datetime.strptime(config['simulation']['start_time'], '%Y-%m-%d %H:%M:%S')
    step_seconds = config['simulation']['step_seconds']
    simulation_length_seconds = config['simulation']['simulation_length_seconds']
    end_time = start_time + timedelta(seconds=simulation_length_seconds)

    
    f = open(config['tle_data']['path'])
    tle_data = f.read()

    directory_result = config['simulation']['directory_results']

    # Format start time and replace in directory pattern
    formatted_start_time = start_time.strftime("%Y%m%d_%H%M%S")
    directory = directory_result.replace('{date}', formatted_start_time)
    if not os.path.exists(directory):
        xEO_mini.debug_print(f"There is no topology data, generate the topology data first before you can pre-compute the routing tables.", "red")
        

    # start_time = start_time + timedelta(seconds=30) # REMOVE IMMED
    child_directory1 = f"connectivity_matrices_{formatted_start_time}"
    child_directory2 = f"satellites_{formatted_start_time}"
    
    directory_c1 = os.path.join(directory, child_directory1)
    if not os.path.exists(directory_c1):
        xEO_mini.debug_print(f"There is no topology data, generate the topology data first before you can pre-compute the routing tables. {directory_c1} does not exist", "red")
   
    directory_c2 = os.path.join(directory, child_directory2)
    if not os.path.exists(directory_c2):
        xEO_mini.debug_print(f"There is no topology data, generate the topology data first before you can pre-compute the routing tables. {directory_c2} does not exist", "red")
    
    # Simulation loop
    current_time = start_time
    directory_result = config['simulation']['directory_results']
    formatted_start_time = start_time.strftime("%Y%m%d_%H%M%S")
    directory = directory_result.replace('{date}', formatted_start_time)
    terminals = read_terminals(config['terminal_data']['path'])

    previous_adjacency_matrix = 0
    previous_path = 0
    xEO_mini.debug_print("Pre-processing is started", "green")
    while current_time < end_time:
        formatted_timestamp = current_time.strftime("%Y%m%d_%H%M%S")

        satellites_file = os.path.join(directory_c2, f'satellites_{formatted_timestamp}.json')
        reconstructed_satellites_dict = xEO_topology.reconstruct_satellite_dict(satellites_file, tle_data)
        
        # this if-condition is for the first iteration only.
        if (current_time == start_time):
            xEO_mini.debug_print(f"The current timestamp is {current_time}", "green")
            
            # 1.1 read the topology
            adjacency_matrix_file = os.path.join(directory_c1, f'adjacency_matrix_{formatted_timestamp}.json')
            with open(adjacency_matrix_file, 'r') as file:
                adjacency_matrix_list = json.load(file)
        
            # Convert the list of lists back into a numpy array
            adjacency_matrix = np.array(adjacency_matrix_list)
            previous_adjacency_matrix = adjacency_matrix

            total_links = xEO_topology.count_links_in_connectivity_matrix(adjacency_matrix)
            subnet_mask = xEO_network.find_smallest_subnet_mask_for_subnets((2*total_links))
            ip_subnet = f"192.168.0.0/{subnet_mask}"
            new_reconstructed_satellites_dict = xEO_network.distribute_ip_addresses(adjacency_matrix, reconstructed_satellites_dict, ip_subnet)
            
            xEO_mini.debug_print(f" >>>> Total number of links of this topology is {total_links}", "green")

            # 1.2 find the route between ground segments
            path = xEO_route.find_shortest_path_between_terminals(adjacency_matrix, terminals, config['experiment']['end1'], config['experiment']['end2'], reconstructed_satellites_dict, current_time)
            previous_path = path

            xEO_mini.debug_print(f" >>>> Path between {config['experiment']['end1']} and {config['experiment']['end2']} found and of length = {len(path)}", "green")
            xEO_mini.debug_print(f" >>>> The new path between {config['experiment']['end1']} and {config['experiment']['end2']} is {path}", "green")
            # 1.3 assignment ips to the gsl links
            output_ip_assignment_terminals = xEO_network.ip_assignment_terminals_satellites([config['experiment']['end1'], config['experiment']['end2']], [path[0], path[len(path)-1]], "10.10.10.0/24", new_reconstructed_satellites_dict)
            new_reconstructed_satellites_dict = output_ip_assignment_terminals["updated_satellites"]
            terminals_ips = output_ip_assignment_terminals["termianls_ips"]

            # 1.4 pre-compute routing commands (ip route linux command)
            ip_assignment = xEO_network.extract_ips(new_reconstructed_satellites_dict, terminals_ips)
            routing_r = xEO_network.recursive_generate_routing_commands_(path, new_reconstructed_satellites_dict, ip_assignment)
            xEO_mini.debug_print(f" >>>> Routing commands between {config['experiment']['end1']} and {config['experiment']['end2']} is created", "green")
            
             # 1.5 Save to files (1) The ip route commands, (2) ip address assignments, (3) the path.
            create_routing_configs(routing_r, directory, formatted_timestamp)
            file_path_ips = os.path.join(directory, f"constellation_ip_addresses_{formatted_timestamp}.json")
            with open(file_path_ips, 'w') as file:
                json.dump(ip_assignment, file, indent=4)

            file_path_path = os.path.join(directory, f"path_{formatted_timestamp}.json")
            with open(file_path_path, 'w') as file:
                json.dump(path, file, indent=4)

            xEO_mini.debug_print(f" >>>> Route calculated and meta-data is saved to files for timestamp {formatted_timestamp}", "green")
            xEO_mini.debug_print(f" ------------------------------------------------------------------------------------- ", "yellow")
            current_time += timedelta(seconds=step_seconds)
            time.sleep(step_seconds)  # Sleep for step_seconds

        # this else-condition is for the consecutive iteration.
        else:
            xEO_mini.debug_print(f"The current timestamp is {current_time}", "green")
            adjacency_matrix_file = os.path.join(directory_c1, f'adjacency_matrix_{formatted_timestamp}.json')
            with open(adjacency_matrix_file, 'r') as file:
                adjacency_matrix_list = json.load(file)

            adjacency_matrix = np.array(adjacency_matrix_list)
            previous_timestamp = current_time - timedelta(seconds=1)
            formatted_previous_timestamp = previous_timestamp.strftime('%Y%m%d_%H%M%S')
            adjacency_matrix_file_prev = os.path.join(directory_c1, f'adjacency_matrix_{formatted_previous_timestamp}.json')
            
            ## this if-condition is for the case that there is no change in ISL links
            ##### No need to recompute the routing - Just copy routing old files (from previous iteration)
            ##
            if len(compare_adjacency_matrices(adjacency_matrix_file, adjacency_matrix_file_prev)) == 0:
                file_path_ips = os.path.join(directory, f"constellation_ip_addresses_{formatted_previous_timestamp}.json")
                with open(file_path_ips, 'r') as file:
                    ip_assignment = json.load(file)

                reconstructed_satellites_dict = xEO_network.read_ips_from_file_to_satellite(reconstructed_satellites_dict, ip_assignment)
                # expected_date = datetime(2023, 11, 13, 10, 30, 48)
                # if current_time == expected_date:
                #     for sat_name, satellite in reconstructed_satellites_dict.items():
                #         print(sat_name, reconstructed_satellites_dict[sat_name].intf_count, len(reconstructed_satellites_dict[sat_name]._neighbors_ip))

                xEO_mini.debug_print(f" >>>> There is no changes in the ISL Links", "green")
                previous_adjacency_matrix = adjacency_matrix
                path = xEO_route.find_shortest_path_between_terminals(adjacency_matrix, terminals, config['experiment']['end1'], config['experiment']['end2'], reconstructed_satellites_dict, current_time)
                
                xEO_mini.debug_print(f" >>>> Path between {config['experiment']['end1']} and {config['experiment']['end2']} found and of length = {len(path)}", "green")

                # if there are changes in the gsl links
                gsl_changed = check_changes_in_gsl(current_time, directory, path)

                ## this if-condition is for the case that there is changes in GSL links
                ##### No need to recompute the routing - All required is to change the IPs of the gsl links
                ##
                if gsl_changed != -1:
                    xEO_mini.debug_print(f" >>>> There are changes in the GSL Links", "yellow")
                    xEO_mini.debug_print(f" >>>> The new path between {config['experiment']['end1']} and {config['experiment']['end2']} is {path}", "green")
                    previous_timestamp = current_time - timedelta(seconds=1)

                    formatted_previous_timestamp = previous_timestamp.strftime('%Y%m%d_%H%M%S')
                    file_path_ips_previous = os.path.join(directory, f"constellation_ip_addresses_{formatted_previous_timestamp}.json")
                    file_path_path_previous = os.path.join(directory, f"path_{formatted_previous_timestamp}.json")

                    with open(file_path_ips_previous, 'r') as file:
                        previous_ip_assignment = json.load(file)
                    
                    with open(file_path_path_previous, 'r') as file:
                        previous_path = json.load(file)
                    
                    updated_gsl_ips_ = xEO_network.update_gsl_ips(previous_ip_assignment, previous_path, gsl_changed, path, [config['experiment']['end1'], config['experiment']['end2']], reconstructed_satellites_dict)
                    ip_assignment = updated_gsl_ips_["ip_assignment"]
                    file_path_ips = os.path.join(directory, f"constellation_ip_addresses_{formatted_timestamp}.json")
                    with open(file_path_ips, 'w') as file:
                        json.dump(ip_assignment, file, indent=4)

                    file_path_path = os.path.join(directory, f"path_{formatted_timestamp}.json")
                    with open(file_path_path, 'w') as file:
                        json.dump(path, file, indent=4)

                    reconstructed_satellites_dict = xEO_network.read_ips_from_file_to_satellite(reconstructed_satellites_dict, ip_assignment)
                    routing_r = xEO_network.recursive_generate_routing_commands_(path, new_reconstructed_satellites_dict, ip_assignment)

                    directory_routing = f"routing_configs_{formatted_previous_timestamp}"
                    # directory_path = os.path.join(directory, directory_routing)

                    directory_path = [os.path.join(root, d) for root, dirs, _ in os.walk(directory) for d in dirs if directory_routing in d]
                    print(directory_path)
                    missing = xEO_network.compare_routes_with_files(directory_path[0], routing_r)
                    # print(missing)
                    for satellite, commands in missing.items():
                        # print(f"Configuration for {satellite}:\n")
                        for command in commands:
                            if "bash" not in command.strip():  # To avoid printing empty lines
                                # print(command.strip())
                                modified_command = command.replace('add', 'delete')
                                modified_command = re.sub(r' via .*', '', modified_command)
                                # print(modified_command.strip())
                                if satellite in routing_r:
                                    routing_r[satellite].append(modified_command.strip())
                                else: 
                                    routing_r[satellite] = []
                                    routing_r[satellite].append(modified_command.strip())

                        # print("\n---------------------------\n")
                    create_routing_configs(routing_r, directory, formatted_timestamp)
                else:
                    no_changes_in_topology(current_time, directory, gsl_changed)

                xEO_mini.debug_print(f" >>>> Route calculated and meta-data is saved to files for timestamp {formatted_timestamp}", "green")
                xEO_mini.debug_print(f" ------------------------------------------------------------------------------------- ", "yellow")
                 # Increment time for next iteration

            ## this if-condition is for the case that there are changes in ISL links
            ##### Recompute the routing
            ##
            else:
                xEO_mini.debug_print(f" >>>> There are changes in the ISL links", "yellow")
                total_links = xEO_topology.count_links_in_connectivity_matrix(adjacency_matrix)
                subnet_mask = xEO_network.find_smallest_subnet_mask_for_subnets((2*total_links))
                ip_subnet = f"192.168.0.0/{subnet_mask}"
                ####################
                test_diff = compare_adjacency_matrices(adjacency_matrix_file, adjacency_matrix_file_prev)
                new_links = []
                for val in test_diff:
                    sat1 = xEO_topology.find_satellite_by_index(reconstructed_satellites_dict, val[0])
                    sat2 = xEO_topology.find_satellite_by_index(reconstructed_satellites_dict, val[1])
                    if sat1 and sat2:
                        if val[2] == 1:
                            new_links.append((sat1.name, sat2.name, val[2]))
                        print(f"The changes in ISL are between {sat1.name} and {sat2.name} and the change is {val[2]}")
                
                file_path_ips = os.path.join(directory, f"constellation_ip_addresses_{formatted_previous_timestamp}.json")
                with open(file_path_ips, 'r') as file:
                    ip_assignment = json.load(file)
                
                reconstructed_satellites_dict = xEO_network.read_ips_from_file_to_satellite(reconstructed_satellites_dict, ip_assignment)
                new_ips = xEO_network.assign_ips_for_new_links(remove_duplicates_in_list_tuples(new_links), ip_assignment, reconstructed_satellites_dict, ip_subnet)
                ip_assignment.update(new_ips)
                ####################
                # new_reconstructed_satellites_dict = xEO_network.distribute_ip_addresses(adjacency_matrix, reconstructed_satellites_dict, ip_subnet)
                print(total_links)

                # 3.1 find the route between ground segments
                path = xEO_route.find_shortest_path_between_terminals(adjacency_matrix, terminals, config['experiment']['end1'], config['experiment']['end2'], reconstructed_satellites_dict, current_time)
                previous_path = path
                xEO_mini.debug_print(f" >>>> Path between {config['experiment']['end1']} and {config['experiment']['end2']} found and of length = {len(path)}", "green")
                xEO_mini.debug_print(f" >>>> The new path between {config['experiment']['end1']} and {config['experiment']['end2']} is {path}", "green")
                # 3.2 assignment ips to the gsl links
                output_ip_assignment_terminals = xEO_network.ip_assignment_terminals_satellites([config['experiment']['end1'], config['experiment']['end2']], [path[0], path[len(path)-1]], "10.10.10.0/24", new_reconstructed_satellites_dict)
                new_reconstructed_satellites_dict = output_ip_assignment_terminals["updated_satellites"]
                terminals_ips = output_ip_assignment_terminals["termianls_ips"]
                for terminal_intf, ip in terminals_ips.items():
                    ip_assignment[terminal_intf] = ip
                ### 3.3 pre-compute routing commands (ip route linux command)
                # ip_assignment = xEO_network.extract_ips(new_reconstructed_satellites_dict, terminals_ips)
                print(len(ip_assignment))
                routing_r = xEO_network.recursive_generate_routing_commands_(path, new_reconstructed_satellites_dict, ip_assignment)
                xEO_mini.debug_print(f" >>>> Routing commands between {config['experiment']['end1']} and {config['experiment']['end2']} is created", "green")
            
                # 1.5 Save to files (1) The ip route commands, (2) ip address assignments, (3) the path.
                create_routing_configs(routing_r, directory, formatted_timestamp)
                file_path_ips = os.path.join(directory, f"constellation_ip_addresses_{formatted_timestamp}.json")
                print(len(ip_assignment))
                with open(file_path_ips, 'w') as file:
                    json.dump(ip_assignment, file, indent=4)

                file_path_path = os.path.join(directory, f"path_{formatted_timestamp}.json")
                with open(file_path_path, 'w') as file:
                    json.dump(path, file, indent=4)

                xEO_mini.debug_print(f" >>>> Route calculated and meta-data is saved to files for timestamp {formatted_timestamp}", "green")
                xEO_mini.debug_print(f" ------------------------------------------------------------------------------------- ", "yellow")
        
            current_time += timedelta(seconds=step_seconds)
            time.sleep(step_seconds)  # Sleep for step_seconds
       

def find_satellite_with_ip(ip_target, ip_assignment):
    for iface, ip in ip_assignment.items():
        if ip == ip_target:
            parts = iface.split("-")
            return parts[0]+"-"+parts[1]
    
    return -1

def add_other_nets_to_routing(routing_dict, ip_assignment):
    new_routes = {}
    for satellite, routes in routing_dict.items():
        target_ips = []
        for route in routes:
            # print(route)
            if "via" in route and "add" in route:
                destination_net = route.split(" ")[3]
                next_hop = route.split(" ")[5]
                out_dev = route.split(" ")[7]
                target_ips = xEO_network.get_host_addresses(destination_net)
                for ips in target_ips:
                    sat = find_satellite_with_ip(ips, ip_assignment)
                    if sat != -1:
                        associated_ips = [ip for iface, ip in ip_assignment.items() if sat in iface]
                        for ip in associated_ips:
                            net_add = xEO_network.get_network_address(ip, 30)
                            command = f"ip route add {net_add} via {next_hop} dev {out_dev}"
                            if satellite not in new_routes:
                                new_routes[satellite] = []
                                new_routes[satellite].append(command)
                            else:
                                new_routes[satellite].append(command)
                            # print(destination_net, next_hop, out_dev, target_ips, sat, ip, command)
            if "via" not in route and "add" in route:
                # print(route)
                destination_net = route.split(" ")[3]
                out_dev = route.split(" ")[5]
                target_ips = [destination_net]
                for ips in target_ips:
                    sat = find_satellite_with_ip(ips, ip_assignment)
                    if sat != -1:
                        associated_ips = [ip for iface, ip in ip_assignment.items() if sat in iface]
                        for ip in associated_ips:
                            net_add = ip
                            command = f"ip route add {net_add} dev {out_dev}"
                            if satellite not in new_routes:
                                new_routes[satellite] = []
                                new_routes[satellite].append(command)
                            else:
                                new_routes[satellite].append(command)

                            # print(destination_net, out_dev, target_ips, sat, ip, command)

    return combine_dictionaries(routing_dict, new_routes)
       
def combine_dictionaries(dict1, dict2):
    combined_dict = {}

    # Get all unique keys from both dictionaries
    all_keys = set(dict1.keys()) | set(dict2.keys())

    for key in all_keys:
        # print(dict2.get(key, []))
        # print(dict1.get(key, []))
        combined_list = dict1.get(key, []) + dict2.get(key, [])
        combined_dict[key] = combined_list

    return combined_dict

def remove_duplicates_in_list_tuples(tuples):
    # Using a set to store unique tuples
    unique_tuples = set()

    for t in tuples:
        # Normalizing each tuple
        normalized = (min(t[0], t[1]), max(t[0], t[1]), t[2])
        unique_tuples.add(normalized)

    # Converting the set back to a list
    result = list(unique_tuples)

    return result