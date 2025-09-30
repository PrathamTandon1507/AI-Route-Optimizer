"""
Enhanced navigation system with robust avoidance
"""
from optimized_routing import OptimizedRouteEngine, Location, Blockage
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import streamlit as st
import time
from typing import List, Optional, Dict

class EnhancedNavigationSystem:
    """Enhanced navigation with robust obstacle avoidance"""
    
    def __init__(self):
        self.route_engine = OptimizedRouteEngine()
        self.blockages: List[Blockage] = []
        self.cache = {}
        self.geocoder = Nominatim(user_agent="RouteOptimizer-Robust-v1.0")
    
    def geocode_location(self, location_name: str) -> Optional[Location]:
        cache_key = location_name.lower().strip()
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        try:
            st.info(f"🔍 Looking up: {location_name}")
            time.sleep(1)
            
            location = self.geocoder.geocode(location_name, timeout=12)
            if location:
                result = Location(
                    lat=float(location.latitude),
                    lon=float(location.longitude),
                    name=location.address
                )
                self.cache[cache_key] = result
                st.success(f"✅ Found: {location.address[:70]}")
                return result
            else:
                st.error(f"❌ Could not find: {location_name}")
                
        except Exception as e:
            st.error(f"❌ Geocoding error: {str(e)}")
        
        return None
    
    def add_blockage(self, lat: float, lon: float, radius: float, description: str):
        """Add blockage with validation"""
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            st.error("❌ Invalid coordinates")
            return
        if radius <= 0:
            st.error("❌ Radius must be positive")
            return
        
        blockage = Blockage(lat, lon, radius, description)
        self.blockages.append(blockage)
        st.success(f"✅ Added obstacle: {description} ({radius}m)")
    
    def clear_blockages(self):
        """Clear all blockages"""
        self.blockages = []
        st.success("🧹 All obstacles cleared")
    
    def calculate_direct_route(self, start: Location, end: Location) -> Dict:
        """Calculate direct route without obstacles"""
        st.info("🛣️ Calculating direct route...")
        
        route_data = self.route_engine.get_reliable_route(start.lat, start.lon, end.lat, end.lon)
        
        if not route_data or not route_data.get('success'):
            return {"success": False, "message": "Could not calculate direct route"}
        
        return {
            "success": True,
            "route": route_data['route'],
            "distance_km": route_data['distance'],
            "estimated_time_minutes": route_data['duration'],
            "total_waypoints": len(route_data['route']),
            "route_type": f"🟢 Direct Route ({route_data.get('service', 'Unknown')})",
            "method": f"Direct routing via {route_data.get('service', 'routing service')}",
            "efficiency_score": 100.0,
            "blockage_impact": 0.0,
            "service_used": route_data.get('service', 'Unknown')
        }
    
    def calculate_optimal_route(self, start: Location, end: Location, show_direct: bool = False) -> Dict:
        """Calculate optimal route with strong obstacle avoidance"""
        if not start or not end:
            return {"success": False, "message": "Invalid start or end location"}
        
        direct_route = self.calculate_direct_route(start, end)
        
        if not direct_route["success"]:
            return direct_route

        if show_direct or not self.blockages:
            if show_direct:
                direct_route["route_type"] = f"🟢 Direct Route - Obstacles Ignored ({direct_route.get('service_used', 'Unknown')})"
            return direct_route

        st.info("🔍 Analyzing route for obstacles...")
        conflicts = self.route_engine.calculate_route_conflicts(direct_route['route'], self.blockages)
        
        if not conflicts['has_conflicts']:
            st.success("✅ Direct route is completely safe!")
            direct_route.update({
                "route_type": f"🟢 Direct Route - Verified Safe ({direct_route.get('service_used', 'Unknown')})",
                "conflicts": conflicts
            })
            return direct_route

        conflict_pct = conflicts['conflict_percentage']
        st.error(f"🚨 MAJOR CONFLICT DETECTED: {conflict_pct:.1f}% of route passes through obstacles!")
        st.info("🛠️ Generating strong avoidance route...")

        avoidance_route = self.route_engine.find_optimal_avoidance_route(start, end, self.blockages)
        
        if avoidance_route:
            avoidance_conflicts = avoidance_route.get('conflicts', {})
            
            if not avoidance_conflicts.get('has_conflicts'):
                st.success("🎯 PERFECT AVOIDANCE ROUTE FOUND!")
                route_type = f"🔵 Perfect Avoidance Route ({avoidance_route.get('service', 'Unknown')})"
            elif avoidance_conflicts.get('conflict_percentage', 100) < conflict_pct / 2:
                st.success("📊 MUCH BETTER ROUTE FOUND!")
                route_type = f"🟡 Improved Avoidance Route ({avoidance_route.get('service', 'Unknown')})"
            else:
                st.warning("⚠️ PARTIAL IMPROVEMENT ACHIEVED")
                route_type = f"🟠 Partial Avoidance Route ({avoidance_route.get('service', 'Unknown')})"
            
            return {
                "success": True,
                "route": avoidance_route['route'],
                "distance_km": avoidance_route['distance'],
                "estimated_time_minutes": avoidance_route['duration'],
                "blockage_impact": abs(avoidance_route['distance_impact']),
                "total_waypoints": len(avoidance_route['route']),
                "route_type": route_type,
                "method": f"Strong avoidance via {avoidance_route.get('service', 'routing service')}",
                "conflicts": avoidance_route['conflicts'],
                "waypoints": avoidance_route.get('waypoints', []),
                "efficiency_score": avoidance_route['efficiency_score'],
                "original_distance": direct_route['distance_km'],
                "original_duration": direct_route['estimated_time_minutes'],
                "strategy_name": avoidance_route['strategy_name'],
                "service_used": avoidance_route.get('service', 'Unknown'),
                "avoidance_success": not avoidance_route['conflicts'].get('has_conflicts', True)
            }

        st.error("❌ CRITICAL: Could not find any viable avoidance route!")
        st.error("🚨 WARNING: Route will pass through obstacle areas - USE EXTREME CAUTION!")
        
        return {
            "success": True,
            "route": direct_route['route'],
            "distance_km": direct_route['distance_km'],
            "estimated_time_minutes": direct_route['estimated_time_minutes'],
            "blockage_impact": conflicts['conflict_percentage'],
            "total_waypoints": len(direct_route['route']),
            "route_type": f"🔴 DANGEROUS ROUTE - OBSTACLES NOT AVOIDED ({direct_route.get('service_used', 'Unknown')})",
            "method": "FALLBACK - Avoidance system failed",
            "conflicts": conflicts,
            "efficiency_score": 0,  
            "warning": f"CRITICAL: Route passes through {len(conflicts['conflict_points'])} obstacle areas",
            "service_used": direct_route.get('service_used', 'Unknown'),
            "avoidance_success": False,
            "danger_level": "HIGH"
        }