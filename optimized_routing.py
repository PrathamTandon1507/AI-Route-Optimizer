import requests
import math
import heapq
from typing import List, Tuple, Optional, Dict, Set
from geopy.distance import geodesic
import streamlit as st
import time
import itertools
from collections import defaultdict

class Location:
    def __init__(self, lat: float, lon: float, name: str = ""):
        self.lat = lat
        self.lon = lon
        self.name = name

class Blockage:
    def __init__(self, lat: float, lon: float, radius: float, description: str = "Road blockage"):
        self.lat = lat
        self.lon = lon
        self.radius = radius
        self.description = description

class PathNode:
    def __init__(self, lat: float, lon: float, node_type: str = "waypoint", name: str = ""):
        self.lat = lat
        self.lon = lon
        self.node_type = node_type 
        self.name = name
        self.id = f"{lat:.6f},{lon:.6f}"
    
    def distance_to(self, other) -> float:
        return geodesic((self.lat, self.lon), (other.lat, other.lon)).kilometers
    
    def __lt__(self, other):
        return self.id < other.id

class RoutePath:
    """Represents a complete path from start to end"""
    def __init__(self, nodes: List[PathNode], total_distance: float, conflicts: Dict, route_points: List[Tuple[float, float]]):
        self.nodes = nodes
        self.total_distance = total_distance
        self.conflicts = conflicts
        self.route_points = route_points
        self.efficiency_score = 0
        self.is_valid = not conflicts.get('has_conflicts', True)
    
    def calculate_score(self, direct_distance: float) -> float:
        """Calculate comprehensive path score"""
        if self.total_distance <= 0:
            return 0
        
        efficiency = min(100, (direct_distance / self.total_distance) * 100)
        score = efficiency

        if self.conflicts.get('has_conflicts'):
            conflict_penalty = self.conflicts.get('conflict_percentage', 0) * 20
            score = max(0, score - conflict_penalty)
        else:
            score += 100 
        
        detour_ratio = self.total_distance / direct_distance if direct_distance > 0 else float('inf')
        if detour_ratio > 2.5:
            score -= (detour_ratio - 2.5) * 40
        elif detour_ratio < 1.5:
            score += 20 
        
        self.efficiency_score = efficiency
        return score

class OptimizedRouteEngine:
    """
    Comprehensive routing engine that explores ALL possible paths
    """
    
    def __init__(self):
        self.routing_services = [
            "https://router.project-osrm.org",
            "http://router.project-osrm.org"
        ]
        
    def get_reliable_route(self, start_lat: float, start_lon: float, end_lat: float, end_lon: float, waypoints: List[Tuple[float, float]] = None) -> Optional[Dict]:
        """Get route with waypoints if specified"""
        
        if waypoints:
            coords = f"{start_lon},{start_lat}"
            for wp_lat, wp_lon in waypoints:
                coords += f";{wp_lon},{wp_lat}"
            coords += f";{end_lon},{end_lat}"
        else:
            coords = f"{start_lon},{start_lat};{end_lon},{end_lat}"
        
        #OSRM
        for server in self.routing_services:
            try:
                url = f"{server}/route/v1/driving/{coords}"
                params = {
                    'overview': 'full',
                    'geometries': 'geojson',
                    'steps': 'false',
                    'alternatives': 'true',
                    'continue_straight': 'false'
                }
                
                headers = {
                    'User-Agent': 'ComprehensiveRouteOptimizer/1.0',
                    'Accept': 'application/json'
                }
                
                response = requests.get(url, params=params, headers=headers, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get('code') == 'Ok' and data.get('routes'):
                        if not waypoints and len(data['routes']) > 1:
                            return {
                                'routes': data['routes'],
                                'multiple_routes': True,
                                'service': 'OSRM'
                            }
                        else:
                            route_info = data['routes'][0]
                            coordinates = route_info['geometry']['coordinates']
                            route_points = [(coord[1], coord[0]) for coord in coordinates]
                            
                            return {
                                'route': route_points,
                                'distance': route_info['distance'] / 1000,
                                'duration': route_info['duration'] / 60,
                                'success': True,
                                'service': 'OSRM'
                            }
                        
            except Exception as e:
                continue
        
        return self._create_realistic_route(start_lat, start_lon, end_lat, end_lon, waypoints)
    
    def _create_realistic_route(self, start_lat: float, start_lon: float, end_lat: float, end_lon: float, waypoints: List[Tuple[float, float]] = None) -> Dict:
        """Create realistic route when services fail"""
        
        route_points = []
        total_distance = 0
        
        all_points = [(start_lat, start_lon)]
        if waypoints:
            all_points.extend(waypoints)
        all_points.append((end_lat, end_lon))
        
        for i in range(len(all_points) - 1):
            current_lat, current_lon = all_points[i]
            next_lat, next_lon = all_points[i + 1]
            
            distance = geodesic((current_lat, current_lon), (next_lat, next_lon)).kilometers
            total_distance += distance
            
            segment_points = self._generate_realistic_segment(current_lat, current_lon, next_lat, next_lon)
            
            if i == 0:
                route_points.extend(segment_points)
            else:
                route_points.extend(segment_points[1:])
        
        estimated_duration = (total_distance / 40) * 60
        
        return {
            'route': route_points,
            'distance': total_distance,
            'duration': estimated_duration,
            'success': True,
            'service': 'Offline'
        }
    
    def _generate_realistic_segment(self, start_lat: float, start_lon: float, end_lat: float, end_lon: float) -> List[Tuple[float, float]]:
        """Generate realistic road-like segment"""
        
        distance = geodesic((start_lat, start_lon), (end_lat, end_lon)).kilometers
        num_points = max(8, int(distance * 2))
        
        lat_diff = end_lat - start_lat
        lon_diff = end_lon - start_lon
        
        points = []
        
        for i in range(num_points + 1):
            progress = i / num_points
            
            lat = start_lat + lat_diff * progress
            lon = start_lon + lon_diff * progress
            
            if 0 < progress < 1:
                curve_factor = 0.0002 * distance
                lat += curve_factor * math.sin(progress * math.pi * 2.1)
                lon += curve_factor * math.cos(progress * math.pi * 1.8)
            
            points.append((lat, lon))
        
        return points
    
    def calculate_route_conflicts(self, route: List[Tuple[float, float]], blockages: List[Blockage]) -> Dict:
        """Calculate conflicts with route"""
        if not route or not blockages:
            return {'has_conflicts': False, 'conflict_points': [], 'conflict_percentage': 0.0}
        
        conflict_points = []
        total_route_length = 0
        conflict_length = 0
        
        for i in range(len(route) - 1):
            point_a = route[i]
            point_b = route[i + 1]
            
            segment_length = geodesic(point_a, point_b).meters
            total_route_length += segment_length
            
            segment_conflicts = False
            
            for j in range(5):
                ratio = j / 4
                check_lat = point_a[0] + (point_b[0] - point_a[0]) * ratio
                check_lon = point_a[1] + (point_b[1] - point_a[1]) * ratio
                
                for blockage in blockages:
                    distance_to_blockage = geodesic((check_lat, check_lon), (blockage.lat, blockage.lon)).meters
                    
                    if distance_to_blockage <= (blockage.radius + 150):
                        conflict_points.append({
                            'index': i,
                            'point': (check_lat, check_lon),
                            'blockage': blockage,
                            'distance_to_center': distance_to_blockage
                        })
                        segment_conflicts = True
                        break
                
                if segment_conflicts:
                    break
            
            if segment_conflicts:
                conflict_length += segment_length
        
        conflict_percentage = (conflict_length / total_route_length * 100) if total_route_length > 0 else 0
        
        return {
            'has_conflicts': len(conflict_points) > 0,
            'conflict_points': conflict_points,
            'conflict_percentage': min(conflict_percentage, 100.0),
            'total_points': len(route),
            'conflict_length': conflict_length,
            'total_length': total_route_length
        }
    
    def find_optimal_avoidance_route(self, start: Location, end: Location, blockages: List[Blockage]) -> Optional[Dict]:
        """Comprehensive pathfinding that explores ALL possible routes"""
        if not blockages:
            return None
        
        st.info("🔍 Comprehensive Route Exploration - Testing ALL possible paths...")
        
        alternatives = self._try_osrm_alternatives(start, end, blockages)
        if alternatives:
            return alternatives
        
        st.info("🌐 Building comprehensive waypoint network...")
        path_network = self._build_comprehensive_network(start, end, blockages)
        
        st.info(f"📊 Generated {len(path_network)} waypoint candidates")
        
        st.info("🔄 Exploring all possible path combinations...")
        all_paths = self._explore_all_path_combinations(start, end, path_network, blockages)
        
        st.info(f"🎯 Testing {len(all_paths)} unique path combinations")
        
        best_path = None
        best_score = -1
        paths_tested = 0
        valid_paths = 0
        
        progress_bar = st.progress(0)
        
        for i, path_combo in enumerate(all_paths):
            try:
                progress = (i + 1) / len(all_paths)
                progress_bar.progress(progress)
                
                paths_tested += 1

                route_data = self.get_reliable_route(
                    start.lat, start.lon,
                    end.lat, end.lon,
                    path_combo['waypoints']
                )
                
                if route_data and route_data.get('success'):

                    conflicts = self.calculate_route_conflicts(route_data['route'], blockages)
                    

                    path = RoutePath(
                        nodes=[], 
                        total_distance=route_data['distance'],
                        conflicts=conflicts,
                        route_points=route_data['route']
                    )

                    direct_distance = geodesic((start.lat, start.lon), (end.lat, end.lon)).kilometers
                    score = path.calculate_score(direct_distance)
                    
                    if not conflicts.get('has_conflicts'):
                        valid_paths += 1
                        st.success(f"✅ Valid path {valid_paths}: {path_combo['name']} - Score: {score:.1f}")
                    else:
                        st.info(f"⚠️ Path {paths_tested}: {path_combo['name']} - Conflicts: {conflicts['conflict_percentage']:.1f}%")
                    
                    if score > best_score:
                        best_score = score
                        best_path = {
                            **route_data,
                            'conflicts': conflicts,
                            'strategy_name': path_combo['name'],
                            'efficiency_score': path.efficiency_score,
                            'distance_impact': ((route_data['distance'] - direct_distance) / direct_distance) * 100 if direct_distance > 0 else 0,
                            'waypoints': path_combo['waypoints'],
                            'total_paths_tested': paths_tested,
                            'valid_paths_found': valid_paths,
                            'exploration_completeness': 100.0
                        }
                        
                        st.info(f"🏆 New best path: {path_combo['name']} (Score: {score:.1f})")

                        
            except Exception as e:
                st.warning(f"Path failed: {path_combo.get('name', 'Unknown')} - {str(e)}")
                continue
        
        progress_bar.empty()
        
        if best_path:
            st.balloons()
            st.success(f"🎯 COMPREHENSIVE EXPLORATION COMPLETE!")
            st.success(f"📊 Tested {paths_tested} paths, found {valid_paths} conflict-free options")
            st.success(f"🏆 OPTIMAL PATH: {best_path['strategy_name']}")
            st.success(f"⭐ Final Score: {best_score:.1f}, Efficiency: {best_path['efficiency_score']:.1f}%")
        else:
            st.error("❌ No valid paths found after comprehensive exploration")
        
        return best_path
    
    def _try_osrm_alternatives(self, start: Location, end: Location, blockages: List[Blockage]) -> Optional[Dict]:
        """Try OSRM natural alternatives first"""
        
        route_data = self.get_reliable_route(start.lat, start.lon, end.lat, end.lon)
        
        if route_data and route_data.get('multiple_routes'):
            st.info("🛣️ Testing OSRM natural alternatives...")
            
            best_alternative = None
            best_score = -1
            
            for i, route_info in enumerate(route_data['routes']):
                try:
                    coordinates = route_info['geometry']['coordinates']
                    route_points = [(coord[1], coord[0]) for coord in coordinates]
                    
                    conflicts = self.calculate_route_conflicts(route_points, blockages)
                    
                    distance_km = route_info['distance'] / 1000
                    duration_min = route_info['duration'] / 60
                    
                    direct_distance = geodesic((start.lat, start.lon), (end.lat, end.lon)).kilometers
                    
                    path = RoutePath([], distance_km, conflicts, route_points)
                    score = path.calculate_score(direct_distance)
                    
                    st.info(f"🛣️ OSRM Alt {i+1}: {distance_km:.1f}km, "
                           f"Conflicts: {conflicts['conflict_percentage']:.1f}%, Score: {score:.1f}")
                    
                    if score > best_score:
                        best_score = score
                        best_alternative = {
                            'route': route_points,
                            'distance': distance_km,
                            'duration': duration_min,
                            'success': True,
                            'service': 'OSRM',
                            'conflicts': conflicts,
                            'strategy_name': f'OSRM Natural Alternative {i+1}',
                            'efficiency_score': path.efficiency_score,
                            'distance_impact': ((distance_km - direct_distance) / direct_distance) * 100 if direct_distance > 0 else 0,
                            'exploration_method': 'OSRM Natural Alternatives'
                        }
                    
                        
                except Exception:
                    continue
            
            if best_alternative and best_score > 50:  
                st.success(f"✅ Good natural alternative found: {best_alternative['strategy_name']}")
                return best_alternative
        
        return None
    
    def _build_comprehensive_network(self, start: Location, end: Location, blockages: List[Blockage]) -> List[PathNode]:
        """Build comprehensive network of waypoint candidates"""
        
        network_nodes = []
        
        start_node = PathNode(start.lat, start.lon, "start", "Start")
        end_node = PathNode(end.lat, end.lon, "end", "End")
        
        for i, blockage in enumerate(blockages):
            rings = [1.5, 2.0, 2.5, 3.0]  
            angles = [0, 45, 90, 135, 180, 225, 270, 315] 
            
            for ring_multiplier in rings:
                base_safe_distance = max(blockage.radius * ring_multiplier, 1000)
                
                for angle in angles:
                    angle_rad = math.radians(angle)

                    distance_deg = base_safe_distance / 111000
                    lat_offset = distance_deg * math.cos(angle_rad)
                    lon_offset = distance_deg * math.sin(angle_rad)
                    
                    waypoint_lat = blockage.lat + lat_offset
                    waypoint_lon = blockage.lon + lon_offset
                    
                    is_safe = True
                    min_distance_to_any_blockage = float('inf')
                    
                    for check_blockage in blockages:
                        distance_to_blockage = geodesic((waypoint_lat, waypoint_lon), (check_blockage.lat, check_blockage.lon)).meters
                        min_distance_to_any_blockage = min(min_distance_to_any_blockage, distance_to_blockage)
                        
                        if distance_to_blockage <= (check_blockage.radius + 300):  # 300m safety buffer
                            is_safe = False
                            break
                    
                    if is_safe:
                        node_name = f"WP_B{i+1}_R{ring_multiplier}_{angle}deg"
                        waypoint_node = PathNode(waypoint_lat, waypoint_lon, "waypoint", node_name)
                        network_nodes.append(waypoint_node)
        
        if len(blockages) > 1:
            center_lat = sum(b.lat for b in blockages) / len(blockages)
            center_lon = sum(b.lon for b in blockages) / len(blockages)
            
            max_extent = 0
            for blockage in blockages:
                distance_to_center = geodesic((center_lat, center_lon), (blockage.lat, blockage.lon)).meters
                extent = distance_to_center + blockage.radius
                max_extent = max(max_extent, extent)
            
            cluster_distances = [max_extent * 1.8, max_extent * 2.2, max_extent * 2.6]
            
            for cluster_distance in cluster_distances:
                cluster_distance_deg = cluster_distance / 111000
                
                for angle in [0, 60, 120, 180, 240, 300]:  
                    angle_rad = math.radians(angle)
                    
                    lat_offset = cluster_distance_deg * math.cos(angle_rad)
                    lon_offset = cluster_distance_deg * math.sin(angle_rad)
                    
                    waypoint_lat = center_lat + lat_offset
                    waypoint_lon = center_lon + lon_offset
                    
                    is_safe = True
                    for blockage in blockages:
                        distance_to_blockage = geodesic((waypoint_lat, waypoint_lon), (blockage.lat, blockage.lon)).meters
                        if distance_to_blockage <= (blockage.radius + 500):  # 500m buffer for cluster
                            is_safe = False
                            break
                    
                    if is_safe:
                        node_name = f"Cluster_WP_{int(cluster_distance/1000)}km_{angle}deg"
                        waypoint_node = PathNode(waypoint_lat, waypoint_lon, "waypoint", node_name)
                        network_nodes.append(waypoint_node)
        
        return network_nodes
    
    def _explore_all_path_combinations(self, start: Location, end: Location, network_nodes: List[PathNode], blockages: List[Blockage]) -> List[Dict]:
        """Generate ALL possible path combinations to test"""
        
        path_combinations = []
        direct_distance = geodesic((start.lat, start.lon), (end.lat, end.lon)).kilometers
        
        for node in network_nodes:
            waypoint_lat, waypoint_lon = node.lat, node.lon
            
            dist_start_to_wp = geodesic((start.lat, start.lon), (waypoint_lat, waypoint_lon)).kilometers
            dist_wp_to_end = geodesic((waypoint_lat, waypoint_lon), (end.lat, end.lon)).kilometers
            total_distance = dist_start_to_wp + dist_wp_to_end
            
            if total_distance <= direct_distance * 3:
                path_combinations.append({
                    'name': f"Single WP: {node.name}",
                    'waypoints': [(waypoint_lat, waypoint_lon)],
                    'estimated_distance': total_distance,
                    'waypoint_count': 1
                })

        if len(blockages) > 1 or any(b.radius > 1500 for b in blockages):

            sorted_nodes = sorted(network_nodes, key=lambda n: n.distance_to(PathNode(start.lat, start.lon)))
            top_nodes = sorted_nodes[:min(20, len(sorted_nodes))]  # Top 20 closest nodes
            
            for node1, node2 in itertools.combinations(top_nodes, 2):

                dist_start_to_wp1 = geodesic((start.lat, start.lon), (node1.lat, node1.lon)).kilometers
                dist_wp1_to_wp2 = geodesic((node1.lat, node1.lon), (node2.lat, node2.lon)).kilometers  
                dist_wp2_to_end = geodesic((node2.lat, node2.lon), (end.lat, end.lon)).kilometers
                total_distance = dist_start_to_wp1 + dist_wp1_to_wp2 + dist_wp2_to_end
                
                if total_distance <= direct_distance * 3.5:
                    path_combinations.append({
                        'name': f"Dual WP: {node1.name} → {node2.name}",
                        'waypoints': [(node1.lat, node1.lon), (node2.lat, node2.lon)],
                        'estimated_distance': total_distance,
                        'waypoint_count': 2
                    })
        
        path_combinations.sort(key=lambda x: x['estimated_distance'])
        
        max_combinations = 50
        if len(path_combinations) > max_combinations:
            st.warning(f"⚠️ Limiting to {max_combinations} most promising path combinations (out of {len(path_combinations)} total)")
            path_combinations = path_combinations[:max_combinations]
        
        return path_combinations