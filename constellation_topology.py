from skyfield.api import load, Topos, EarthSatellite
import skyfield.sgp4lib
import numpy as np
import json
import math
import requests
import itur
from datetime import datetime

class Satellite:
    def __init__(self, name, index, earth_satellite_obj=None, orbit=None):
        self._name = name
        self._index = index
        self._earth_satellite_obj = earth_satellite_obj
        self._orbit = orbit
        self._east_neighbors = []
        self._west_neighbors = []
        self._in_orbit_neighbors = []
        self._associated_ground_segment = []
        self._east_counter = 0
        self._west_counter = 0
        self._neighbors_ip = []
        self._intf_count = 0

    # Getters
    @property
    def name(self):
        return self._name

    @property
    def index(self):
        return self._index

    @property
    def earth_satellite_obj(self):
        return self._earth_satellite_obj

    @property
    def orbit(self):
        return self._orbit
    
    @property
    def east_neighbors(self):
        return self._east_neighbors

    @property
    def west_neighbors(self):
        return self._west_neighbors

    @property
    def in_orbit_neighbors(self):
        return self._in_orbit_neighbors
    
    @property
    def associated_ground_segment(self):
        return self._associated_ground_segment
    
    @property
    def east_counter(self):
        return self._east_counter

    @property
    def west_counter(self):
        return self._west_counter

    @property
    def neighbors_ip(self):
        return self._neighbors_ip
    
    @property
    def intf_count(self):
        return self._intf_count

    # Setters
    @name.setter
    def name(self, value):
        self._name = value

    @index.setter
    def index(self, value):
        self._index = value
    
    @earth_satellite_obj.setter
    def earth_satellite_obj(self, value):
        self._earth_satellite_obj = value

    @orbit.setter
    def orbit(self, value):
        self._orbit = value

    # Methods
    def can_add_east_neighbor(self, num_links):
        return self._east_counter < num_links

    def can_add_west_neighbor(self, num_links):
        return self._west_counter < num_links

    def add_east_neighbor(self, neighbor):
        self._east_neighbors.append(neighbor)
        self._east_counter += 1

    def add_west_neighbor(self, neighbor):
        self._west_neighbors.append(neighbor)
        self._west_counter += 1
    
    def add_in_orbit_neighbor(self, neighbor_satellite):
        if neighbor_satellite not in self._in_orbit_neighbors:
            self._in_orbit_neighbors.append(neighbor_satellite)
    
    def add_ground_segment(self, ground_segment):
        if ground_segment not in self._associated_ground_segment:
            self._associated_ground_segment.append(ground_segment)
    
    def remove_ground_segment(self, ground_segment):
        if ground_segment in self._associated_ground_segment:
            self._associated_ground_segment.remove(ground_segment)

    def remove_neighbors_ip(self, ip):
        if ip in self._neighbors_ip:
            self._neighbors_ip.remove(ip)
            self._intf_count -= 1
        
    def add_neighbors_ip(self, ip):
        self._neighbors_ip.append(ip)
        self._intf_count += 1
    
    def to_dict(self):
        return {
            "name": self._name,
            "index": self._index,
            "orbit": self._orbit,
            "east_neighbors": self._east_neighbors,
            "west_neighbors": self._west_neighbors,
            "in_orbit_neighbors": self._in_orbit_neighbors,
            "neighbors_ip": self._neighbors_ip,
            "ground_segment": self._associated_ground_segment,
            "east_counter": self._east_counter,
            "west_counter": self._west_counter,
            "intf_count": self._intf_count
        }


def convert_to_skyfield_time(timestamp):
    ts = load.timescale()
    return ts.utc(timestamp.year, timestamp.month, timestamp.day, timestamp.hour, timestamp.minute, timestamp.second)

def is_adjacent_orbit(value, target, diff_in_raan):
    return ((((value + diff_in_raan) % 360) == target) or (((value - diff_in_raan) % 360) == target))

def within_inclination_tolerance(inclination, target_inclination, inclination_tolerance):
    return abs(inclination - target_inclination) <= inclination_tolerance

def filter_satellites_by_inclination(tle_data, inclination_tolerance, target_inclination):
    lines = tle_data.strip().split('\n')
    satellites = {}
    ts = load.timescale()
    for i in range(0, len(lines), 3):
        name = lines[i].strip()
        line1 = lines[i + 1]
        line2 = lines[i + 2]
        inclination = float(line2.split()[2])

        if within_inclination_tolerance(inclination, target_inclination, inclination_tolerance) and "FALCON" not in name:
            earth_satellite_obj = skyfield.sgp4lib.EarthSatellite(line1, line2, name, ts)
            satellites[name] = Satellite(name, index=None, earth_satellite_obj=earth_satellite_obj)  # index will be set later

    return satellites

def satellite_distance(sat1, sat2, t):
    geocentric1 = sat1.at(t)
    geocentric2 = sat2.at(t)

    # Get the difference in the positions
    difference = geocentric1 - geocentric2

    # Compute the distance in kilometers
    distance = np.linalg.norm(difference.position.km)
    return distance

def group_satellites_by_orbit(tle_data, inclination_tolerance, target_inclination, raan_tolerance, raan_step):
    lines = tle_data.strip().split('\n')
    orbits = {}
    for i in range(2, len(lines), 3):
        line2 = lines[i].split()
        inclination = float(line2[2])
        raan = float(line2[3])

        # Generate a unique key for orbits by rounding RAAN within the tolerance
        if within_inclination_tolerance(inclination, target_inclination, inclination_tolerance):
            orbit_key = (round(raan / raan_step) * raan_step) % 360

            if orbit_key not in orbits:
                orbits[orbit_key] = []
            
            if "FALCON" not in lines[i-2].strip():
                orbits[orbit_key].append((lines[i-2].strip(), inclination, raan))  # Tuple: (satellite_name, inclination, raan)
        
    return orbits

def calculate_relative_position(sat1, sat2, t):
    # Calculate the geocentric position of each satellite
    pos1 = sat1.at(t).position.km
    pos2 = sat2.at(t).position.km

    # Calculate the relative position of sat2 from sat1
    relative_pos = pos2 - pos1
    return relative_pos

def is_satellite_east_or_west(sat1, sat2, t):
   
    relative_pos = calculate_relative_position(sat1.earth_satellite_obj, sat2.earth_satellite_obj, t)

    # Calculate the angle of the relative position vector in the equatorial plane
    angle = np.arctan2(relative_pos[1], relative_pos[0])  # Y-component, X-component
    angle_deg = np.degrees(angle) % 360

    if 0 <= angle_deg < 180:
        return 'west'
    else:
        return 'east'

def load_satellite_data(tle_data, inclination_tolerance, target_inclination, raan_tolerance, raan_step, timestamp):
    ts = load.timescale()
    t = ts.utc(timestamp.year, timestamp.month, timestamp.day, timestamp.hour, timestamp.minute, timestamp.second)

    satellites = filter_satellites_by_inclination(tle_data, inclination_tolerance, target_inclination)
    orbits_grouped = group_satellites_by_orbit(tle_data, inclination_tolerance, target_inclination, raan_tolerance, raan_step)
    orbits = dict(sorted(orbits_grouped.items()))

    # Create a name to index mapping
    name_to_index = create_name_to_index_mapping(orbits)
    # Update each satellite's orbit information
    for orbit_key, orbit_data in orbits.items():
        for sat_name, _, _ in orbit_data:
            if sat_name in satellites:
                satellites[sat_name].orbit = orbit_key
                satellites[sat_name].index = name_to_index[sat_name]

    return satellites, t

def create_name_to_index_mapping(orbits):
    return {name: idx for idx, (name, _, _) in enumerate(sat for orbit in orbits.values() for sat in orbit)}

def initialize_adjacency_matrix(n):
    return np.zeros((n, n), dtype=int)

class TopologyStrategy:
    def generate_matrix(self, satellites, orbits, t, name_to_index, max_distance):
        raise NotImplementedError

class DefaultTopology(TopologyStrategy):
    def generate_matrix(self, satellites, t, max_distance, num_links):
        adjacency_matrix = initialize_adjacency_matrix(len(satellites))

        for sat1 in satellites.values():
            closest_satellite = None
            min_distance = float('inf')

            for sat2 in satellites.values():
                if sat1.name != sat2.name and sat1.orbit == sat2.orbit:  # Check for in-orbit satellites
                    dist = satellite_distance(sat1.earth_satellite_obj, sat2.earth_satellite_obj, t)
                    if dist < min_distance:
                        min_distance = dist
                        closest_satellite = sat2

            if closest_satellite and min_distance <= max_distance:
                adjacency_matrix[sat1.index][closest_satellite.index] = 1
                adjacency_matrix[closest_satellite.index][sat1.index] = 1

                # Update the in-orbit neighbors list
                sat1.add_in_orbit_neighbor(closest_satellite.name)
                closest_satellite.add_in_orbit_neighbor(sat1.name)

        return adjacency_matrix
    
class CrossOrbitTopology(TopologyStrategy):
    def generate_matrix(self, satellites, t, max_distance, num_links, raan_step):
        # Initialize the adjacency matrix using the DefaultTopology
        default_topology = DefaultTopology()
        adjacency_matrix = default_topology.generate_matrix(satellites, t, max_distance, num_links)

        # Process each satellite for cross-orbit connections
        for sat in satellites.values():
            self.process_satellite(sat, satellites, t, max_distance, num_links, adjacency_matrix, raan_step)

        return adjacency_matrix

    def process_satellite(self, satellite, all_satellites, t, max_distance, num_links, adjacency_matrix, raan_step):
        # Find potential cross-orbit connections and sort them by distance
        potential_connections = self.find_potential_connections(satellite, all_satellites, t, max_distance, raan_step)
        potential_connections.sort(key=lambda x: x[1])

        # Establish connections considering east and west neighbors
        for target_sat, distance in potential_connections:
            if sum(adjacency_matrix[satellite.index]) >= num_links:
                break  # Max links reached for the satellite

            position = is_satellite_east_or_west(satellite, target_sat, t)
            if position == 'east' and satellite.can_add_east_neighbor(num_links) and target_sat.can_add_west_neighbor(num_links):
                adjacency_matrix[satellite.index][target_sat.index] = 1
                adjacency_matrix[target_sat.index][satellite.index] = 1
                satellite.add_east_neighbor(target_sat.name)
                target_sat.add_west_neighbor(satellite.name)
            elif position == 'west' and satellite.can_add_west_neighbor(num_links) and target_sat.can_add_east_neighbor(num_links):
                adjacency_matrix[satellite.index][target_sat.index] = 1
                adjacency_matrix[target_sat.index][satellite.index] = 1
                satellite.add_west_neighbor(target_sat.name)
                target_sat.add_east_neighbor(satellite.name)

    def find_potential_connections(self, satellite, all_satellites, t, max_distance, raan_step):
        # Find potential connections for cross-orbit neighbors within max distance and adjacent orbits
        potential_connections = []
        for other_sat in all_satellites.values():
            if is_adjacent_orbit(satellite.orbit, other_sat.orbit, raan_step):
                distance = satellite_distance(satellite.earth_satellite_obj, other_sat.earth_satellite_obj, t)
                if distance <= max_distance:
                    potential_connections.append((other_sat, distance))
        return potential_connections


def generate_connectivity_matrix(tle_data, topology_structure, num_links, max_distance, inclination_tolerance, target_inclination, raan_tolerance, raan_step, timestamp):
    satellites, t = load_satellite_data(tle_data, inclination_tolerance, target_inclination, raan_tolerance, raan_step, timestamp)
    
    adjacency_matrix = initialize_adjacency_matrix(len(satellites))

    # Strategy Pattern for Topologies
    topology_strategies = {
        "default": DefaultTopology(),
        "cross-orbit": CrossOrbitTopology(),
        # Additional topologies can be added here
    }
    topology_strategy = topology_strategies.get(topology_structure, DefaultTopology())
    adjacency_matrix = topology_strategy.generate_matrix(satellites, t, max_distance, num_links, raan_step)

    return {"matrix": adjacency_matrix, "satellites": satellites}


class TerminalConnectionStrategy:
    def connect(self, terminals, satellites, t):
        raise NotImplementedError

class NearestSatelliteStrategy(TerminalConnectionStrategy):
    def connect(self, terminals, satellites, t):
        terminal_connections = {}
        for terminal_name, terminal_topos in terminals.items():
            nearest_satellite = None
            min_distance = float('inf')

            for sat_name, satellite in satellites.items():
                distance = np.linalg.norm((satellite.earth_satellite_obj - terminal_topos).at(t).position.km)
                # print(sat_name, distance, min_distance)
                if distance < min_distance:
                    min_distance = distance
                    nearest_satellite = sat_name
                    # print(sat_name, distance, min_distance)

            terminal_connections[terminal_name] = (nearest_satellite, min_distance)

        return terminal_connections

def calculate_satellites_latency_(sat1, sat2, timestamp):
    speed_of_light = 3 * 10**8  # Speed of light in meters per second
    t = convert_to_skyfield_time(timestamp)
    distance = satellite_distance(sat1.earth_satellite_obj, sat2.earth_satellite_obj, t)*1000
    return (distance / speed_of_light)*1000  # one way

def calculate_satellites_bw_(sat1, sat2, timestamp):
    return 500  # Mbps

def get_weather_data(api_key, lat, lon, timeof):
    response = requests.get(f"https://api.openweathermap.org/data/3.0/onecall/timemachine?lat={lat}&lon={lon}&dt={timeof}&appid={api_key}&units=metric")
    if response.status_code == 200:
        output = response.json()
        
        data = output['data'][0]  # Assuming we need the first item in the 'data' list
        temperature = data['temp']
        pressure = data['pressure']
        humidity = data['humidity']
        weather_description = data['weather'][0]['description']  # Accessing the first item in the 'weather' list

        estimated_r = next((value for key, value in {
            ("Drizzle", "drizzle"): 0.25,
            ("light rain",): 2.5,
            ("moderate rain",): 12.5,  # medium rain
            ("light intensity shower rain", "very heavy rain"): 25.0,  # heavy rain
            ("shower rain", "freezing rain"): 50,  # Downpour
            ("heavy intensity rain",): 100,  # Tropical
            ("extreme rain",): 150  # Monsoon
        }.items() if any(k in weather_description for k in key)), None)

        return temperature, pressure, humidity, estimated_r
    else:
        raise Exception("Error fetching weather data")

def calculate_atmospheric_attenuation(frequency, elevation, lat, lon, api_key, dt):
    temperature, pressure, humidity, r001 = get_weather_data(api_key, lat, lon, dt)
    D = 0.58 * itur.u.m
    attenuation = itur.atmospheric_attenuation_slant_path(lat, lon, frequency, elevation, 0.01, D, R001=r001, T=temperature, H=humidity, P=pressure)
    return attenuation.value

def calculate_received_signal_stregth(direction, config, terminal_lat, terminal_log, distance, elevation, t):
    api_key         = config["weather-api"]["api_key"]
    include_weather = config["weather-api"]["include_weather"]
    weather_related_losses = 0

    if direction == "downlink": 
        frequency   = config["rf-parameters"]["downlink"]["frequency"]

        if include_weather == "yes":
            weather_related_losses = calculate_atmospheric_attenuation(frequency, elevation, terminal_lat, terminal_log, api_key, t)
            
        fspl = calculate_fspl(distance, frequency)
        
        RSS = (
                (config["rf-parameters"]["satellite"]["tx_power_eirp"] + 30)
                - fspl 
                - config["rf-parameters"]["other_losses"]["polarization_loss"]  
                - config["rf-parameters"]["other_losses"]["misalignment_attenuation_losses"]   
                - weather_related_losses 
                - 3 
                + config["rf-parameters"]["terminal"]["rx_gain"]
        )

        return pow(10,((RSS - 30)/10))

    elif direction == "uplink": 
        frequency   = config["rf-parameters"]["uplink"]["frequency"]

        if include_weather == "yes":
            weather_related_losses = calculate_atmospheric_attenuation(frequency, elevation, terminal_lat, terminal_log, api_key, t)

        fspl = calculate_fspl(distance, frequency)

        RSS = (
                (config["rf-parameters"]["terminal"]["tx_power"] + config["rf-parameters"]["terminal"]["tx_gain"] )
                - fspl 
                - config["rf-parameters"]["other_losses"]["polarization_loss"]  
                - config["rf-parameters"]["other_losses"]["misalignment_attenuation_losses"]   
                - weather_related_losses 
                - 3 
                + config["rf-parameters"]["satellite"]["rx_gain"]
        )

        return pow(10,((RSS - 30)/10))
    

def calculate_gs_satellite_bw_(satellite, terminal, config, timestamp, direction):
    t = convert_to_skyfield_time(timestamp)
    distance = np.linalg.norm((satellite.earth_satellite_obj - terminal).at(t).position.km) 
    elevation = ((satellite.earth_satellite_obj - terminal).at(t)).altaz()[0].degrees

    dt = datetime_to_unix_timestamp(timestamp)

    if direction == "downlink":
        rss_watt = calculate_received_signal_stregth(direction, config, terminal.latitude.degrees, terminal.longitude.degrees, distance, elevation, dt)
        noise_watt = 200 * 1.38064852 * pow(10, -23) * 250*pow(10, 6);        #ktB channnel_bandwidth_downlink
        SNR = rss_watt/noise_watt

        return round((config["rf-parameters"]["downlink"]["bandwidth"]*(math.log(1+SNR)/math.log(2))),2)
    
    if direction == "uplink":
        rss_watt = calculate_received_signal_stregth(direction, config, terminal.latitude.degrees, terminal.longitude.degrees, distance, elevation, dt)
        noise_watt = 200 * 1.38064852 * pow(10, -23) * 250*pow(10, 6);        #ktB channnel_bandwidth_downlink
        SNR = rss_watt/noise_watt

        return round((config["rf-parameters"]["uplink"]["bandwidth"]*(math.log(1+SNR)/math.log(2))),2)


def connect_terminals_to_satellites(terminals, satellites, timestamp, connection_strategy='nearest'):
    t = convert_to_skyfield_time(timestamp)

    # Strategy Pattern for Terminal Connections
    connection_strategies = {
        "nearest": NearestSatelliteStrategy(),
        # Add new strategies here
    }
    connection_strategy = connection_strategies.get(connection_strategy, NearestSatelliteStrategy())
    return connection_strategy.connect(terminals, satellites, t)

def calculate_terminal_latency_(satellite, terminal, timestamp):
    speed_of_light = 3 * 10**8  # Speed of light in meters per second
    t = convert_to_skyfield_time(timestamp)
    distance = np.linalg.norm((satellite.earth_satellite_obj - terminal).at(t).position.km)*1000
    return (distance / speed_of_light) * 2  # RTT

def calculate_total_latency(path, satellites, terminals, timestamp):
    speed_of_light = 3 * 10**8  # Speed of light in meters per second
    t = convert_to_skyfield_time(timestamp)

    # Helper function to calculate latency for satellite-to-satellite links
    def calculate_satellite_latency(sat1, sat2):
        distance = satellite_distance(sat1.earth_satellite_obj, sat2.earth_satellite_obj, t)*1000
        return (distance / speed_of_light) * 2  # RTT

    # Helper function to calculate latency for satellite-to-terminal links
    def calculate_terminal_latency(satellite, terminal):
        distance = np.linalg.norm((satellite.earth_satellite_obj - terminal).at(t).position.km)*1000
        return (distance / speed_of_light) * 2  # RTT

    total_latency = 0
    for i in range(len(path) - 1):
        if path[i] in satellites and path[i + 1] in satellites:
            # Satellite-to-satellite link
            total_latency += calculate_satellite_latency(satellites[path[i]], satellites[path[i + 1]])
        elif path[i] in satellites and path[i + 1] in terminals:
            # Satellite-to-terminal link
            total_latency += calculate_terminal_latency(satellites[path[i]], terminals[path[i + 1]])
        elif path[i] in terminals and path[i + 1] in satellites:
            # Terminal-to-satellite link
            total_latency += calculate_terminal_latency(satellites[path[i + 1]], terminals[path[i]])

    return round(total_latency*1000,2)

def calculate_fspl(distance, frequency):
    return 20 * np.log10(distance) + 20 * np.log10(frequency) + 92.45


################ helper functions

def datetime_to_unix_timestamp(dt_obj):
    timestamp = (dt_obj - datetime(1979, 1, 1)).total_seconds()
    return int(timestamp)

def find_satellite(tle_data, satellite_name):
    lines = tle_data.strip().split('\n')
    # Iterate over the lines and find the satellite
    for i in range(0, len(lines), 3):
        name = lines[i].strip()
        line1 = lines[i + 1].strip()
        line2 = lines[i + 2].strip()

        if name == satellite_name:
            ts = load.timescale()
            earth_satellite_obj = EarthSatellite(line1, line2, name, ts)
            return earth_satellite_obj

    # Return None if the satellite is not found
    return None

def reconstruct_satellite_dict(json_file, tle_data):
    with open(json_file, 'r') as file:
        satellites_data = json.load(file)
    
    satellite_dict = {}
    for sat_data in satellites_data:
        satellite_name = sat_data['name']
        earth_satellite_obj = find_satellite(tle_data, satellite_name)

        if earth_satellite_obj:
            satellite = Satellite(
                name=satellite_name,
                index=sat_data['index'],
                earth_satellite_obj=earth_satellite_obj,
                orbit=sat_data['orbit']
            )
            
            satellite_dict[satellite_name] = satellite

    for sat_data in satellites_data:
        satellite = satellite_dict[sat_data['name']]

        # Assuming 'east_neighbors' is a list of names of east neighbors in sat_data
        for neighbor_name in sat_data.get('east_neighbors', []):
            satellite.add_east_neighbor(neighbor_name)
        
        for neighbor_name in sat_data.get('west_neighbors', []):
            satellite.add_west_neighbor(neighbor_name)

        for neighbor_name in sat_data.get('in_orbit_neighbors', []):
            satellite.add_in_orbit_neighbor(neighbor_name)

        for ips in sat_data.get('neighbors_ip', []):
            satellite.add_neighbors_ip(ips)

        for gd_segment in sat_data.get('ground_segment', []):
            satellite.add_ground_segment(gd_segment)

    return satellite_dict

def count_links_in_connectivity_matrix(connectivity_matrix):
    n = len(connectivity_matrix)  # Assuming it's a square matrix
    link_count = 0

    for i in range(n):
        for j in range(i+1, n):  # Only consider elements above the diagonal
            if connectivity_matrix[i][j] == 1:
                link_count += 1

    return link_count

def print_indices_of_ones(connectivity_matrix, index_to_name):
    name_to_index = {v: k for k, v in index_to_name.items()}

    for row_index, row in enumerate(connectivity_matrix):
        # Find indices in the row where the element is 1
        one_indices = np.where(row == 1)[0]

        # Get the satellite name for the row
        satellite_name = name_to_index.get(row_index, "Unknown Satellite")

        # Print satellite name, row index, and indices of ones
        print(f"Satellite {satellite_name} (Row {row_index}): Ones at indices {one_indices}")

def find_satellite_by_index(satellites, index_to_find):
    
    for satellite in satellites.values():
        if satellite.index == int(index_to_find):
            return satellite
    return None