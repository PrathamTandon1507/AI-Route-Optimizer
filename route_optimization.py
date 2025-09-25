"""
Streamlit application with reliable route optimization
"""
import streamlit as st
import folium
from enhanced_navigation import EnhancedNavigationSystem
from geopy.distance import geodesic

def create_map_visualization(start, end, route_data, blockages, direct_route_data=None):
    """Create interactive map with route visualization"""
    
    # Calculate map center and zoom
    center_lat = (start.lat + end.lat) / 2
    center_lon = (start.lon + start.lon) / 2
    
    distance = geodesic((start.lat, start.lon), (end.lat, end.lon)).kilometers
    zoom = max(11, 15 - int(distance / 5))
    
    # Create map
    m = folium.Map(
        location=[center_lat, center_lon], 
        zoom_start=zoom, 
        tiles='OpenStreetMap'
    )
    
    # Add tile layers
    folium.TileLayer('CartoDB positron', name='Clean').add_to(m)
    folium.TileLayer('CartoDB dark_matter', name='Dark').add_to(m)
    
    # Add start marker
    folium.Marker(
        [start.lat, start.lon],
        popup=f"<b>🚀 START</b><br>{start.name[:60]}",
        tooltip="Starting Point",
        icon=folium.Icon(color='green', icon='play')
    ).add_to(m)
    
    # Add end marker
    folium.Marker(
        [end.lat, end.lon],
        popup=f"<b>🏁 DESTINATION</b><br>{end.name[:60]}",
        tooltip="Destination",
        icon=folium.Icon(color='red', icon='stop')
    ).add_to(m)
    
    # Add direct route (reference) if available
    if direct_route_data and direct_route_data.get('route'):
        folium.PolyLine(
            locations=direct_route_data['route'],
            weight=3,
            color='gray',
            opacity=0.4,
            dashArray='5, 10',
            popup=f"""
            <b>📏 Direct Reference</b><br>
            Distance: {direct_route_data['distance_km']:.1f} km<br>
            Time: {direct_route_data['estimated_time_minutes']:.0f} min
            """,
            tooltip="Direct route (reference)"
        ).add_to(m)
    
    # Add main route
    if route_data.get("success") and route_data.get("route"):
        route = route_data["route"]
        route_type = route_data.get('route_type', '')
        efficiency = route_data.get('efficiency_score', 0)
        has_conflicts = route_data.get('conflicts', {}).get('has_conflicts', False)
        
        # Determine route color and style
        if '🟢' in route_type:
            color = '#27AE60'
            weight = 6
            opacity = 0.8
        elif '🔵' in route_type:
            color = '#3498DB' 
            weight = 6
            opacity = 0.8
        elif '🟡' in route_type:
            color = '#F39C12'
            weight = 5
            opacity = 0.7
        else:
            color = '#E74C3C'
            weight = 5
            opacity = 0.7
        
        # Route style
        route_style = {
            'weight': weight,
            'color': color,
            'opacity': opacity
        }
        
        if has_conflicts:
            route_style['dashArray'] = '8, 4'
        
        # Add route line
        folium.PolyLine(
            locations=route,
            popup=f"""
            <div style='width: 280px;'>
            <h4>{route_data.get('route_type', 'Route')}</h4>
            <b>Service:</b> {route_data.get('service_used', 'Unknown')}<br>
            <b>Distance:</b> {route_data['distance_km']:.2f} km<br>
            <b>Duration:</b> {route_data['estimated_time_minutes']:.1f} min<br>
            <b>Efficiency:</b> {efficiency:.1f}%<br>
            <b>Points:</b> {len(route)} coordinates<br>
            <b>Status:</b> {'⚠️ Has Conflicts' if has_conflicts else '✅ Safe Route'}
            </div>
            """,
            tooltip=f"Route Efficiency: {efficiency:.1f}% • Click for details",
            **route_style
        ).add_to(m)
        
        # Add waypoints if present
        waypoints = route_data.get('waypoints', [])
        if waypoints:
            for i, (wp_lat, wp_lon) in enumerate(waypoints):
                folium.Marker(
                    [wp_lat, wp_lon],
                    popup=f"<b>🎯 Waypoint {i+1}</b><br>{route_data.get('strategy_name', 'Strategic point')}",
                    tooltip=f"Strategic waypoint {i+1}",
                    icon=folium.Icon(color='blue', icon='location-arrow')
                ).add_to(m)
        
        # Highlight conflict areas
        conflicts = route_data.get('conflicts', {})
        if conflicts.get('conflict_points'):
            for i, conflict in enumerate(conflicts['conflict_points'][:8]):  # Limit display
                folium.Circle(
                    location=conflict['point'],
                    radius=200,
                    popup=f"""
                    <b>⚠️ Conflict Zone {i+1}</b><br>
                    Distance to obstacle: {conflict['distance_to_center']:.0f}m<br>
                    Obstacle: {conflict['blockage'].description}
                    """,
                    tooltip=f"Conflict area {i+1}",
                    color='orange',
                    fillColor='orange',
                    fill=True,
                    fillOpacity=0.3,
                    weight=2
                ).add_to(m)
    
    # Add obstacles
    for i, obstacle in enumerate(blockages):
        # Main danger zone
        folium.Circle(
            location=[obstacle.lat, obstacle.lon],
            radius=obstacle.radius,
            popup=f"""
            <div style='width: 220px;'>
            <h4>🚧 Obstacle #{i+1}</h4>
            <b>Type:</b> {obstacle.description}<br>
            <b>Radius:</b> {obstacle.radius}m<br>
            <b>Location:</b> {obstacle.lat:.4f}, {obstacle.lon:.4f}<br>
            <b>Area:</b> {(3.14159 * (obstacle.radius/1000)**2):.2f} km²
            </div>
            """,
            tooltip=f"{obstacle.description} - {obstacle.radius}m radius",
            color='#DC143C',
            fillColor='#DC143C',
            fill=True,
            fillOpacity=0.6,
            weight=3
        ).add_to(m)
        
        # Safety buffer
        folium.Circle(
            location=[obstacle.lat, obstacle.lon],
            radius=obstacle.radius * 1.3,
            popup=f"Safety buffer: {obstacle.description}",
            tooltip="Safety zone",
            color='#FF69B4',
            fillColor='#FF69B4',
            fill=True,
            fillOpacity=0.2,
            weight=1,
            dashArray='4, 4'
        ).add_to(m)
        
        # Center marker
        folium.Marker(
            [obstacle.lat, obstacle.lon],
            popup=f"🚧 {obstacle.description}",
            tooltip=obstacle.description,
            icon=folium.Icon(color='darkred', icon='exclamation-triangle')
        ).add_to(m)
    
    # Add layer control
    folium.LayerControl().add_to(m)
    return m

def main():
    st.set_page_config(
        page_title="🎯 Route Optimizer - Advanced Path Planning",
        page_icon="🎯",
        layout="wide"
    )
    
    # Custom CSS
    st.markdown("""
    <style>
    .big-title {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        background: linear-gradient(135deg, #1e3c72, #2a5298);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 1rem;
    }
    .subtitle {
        text-align: center;
        color: #666;
        font-size: 1.2rem;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #007bff;
        margin: 0.5rem 0;
    }
    .success-card { border-left-color: #28a745; background: #d4edda; }
    .warning-card { border-left-color: #ffc107; background: #fff3cd; }
    .danger-card { border-left-color: #dc3545; background: #f8d7da; }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown('<h1 class="big-title">🎯 Advanced Route Optimizer</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Intelligent Path Planning with Real-Time Obstacle Avoidance</p>', unsafe_allow_html=True)
    
    # Initialize system
    if 'navigation_system' not in st.session_state:
        st.session_state.navigation_system = EnhancedNavigationSystem()
    
    nav_system = st.session_state.navigation_system
    
    # Sidebar
    with st.sidebar:
        st.header("🎯 Configuration Panel")
        
        # Location inputs
        st.subheader("📍 Route Endpoints")
        start_input = st.text_input(
            "Start Location",
            placeholder="e.g., Raheja Ridgewood, Mumbai",
            help="Enter starting point address or landmark"
        )
        end_input = st.text_input(
            "End Location", 
            placeholder="e.g., Mumbai Terminal 2",
            help="Enter destination address or landmark"
        )
        
        # Route options
        st.subheader("⚙️ Route Options")
        direct_mode = st.checkbox(
            "Direct route mode",
            help="Calculate direct route ignoring all obstacles"
        )
        
        st.markdown("---")
        
        # Obstacle management
        st.subheader("🚧 Obstacle Management")
        
        with st.expander("➕ Add New Obstacle"):
            col_a, col_b = st.columns(2)
            
            with col_a:
                obs_lat = st.number_input("Latitude", value=19.110428, format="%.6f")
                obs_radius = st.slider("Radius (meters)", 200, 3000, 1000)
            
            with col_b:
                obs_lon = st.number_input("Longitude", value=72.854088, format="%.6f")
                obs_type = st.selectbox("Type", [
                    "Road construction", "Traffic accident", "Flooding",
                    "Bridge closure", "Event", "Emergency", "Other"
                ])
            
            if st.button("Add Obstacle"):
                nav_system.add_blockage(obs_lat, obs_lon, obs_radius, obs_type)
                st.rerun()
        
        # Current obstacles
        if nav_system.blockages:
            st.subheader(f"Active Obstacles ({len(nav_system.blockages)})")
            
            for idx, obs in enumerate(nav_system.blockages):
                with st.container():
                    st.markdown(f"""
                    **{obs.description}**  
                    📍 {obs.lat:.4f}, {obs.lon:.4f}  
                    📏 {obs.radius}m radius
                    """)
                    
                    if st.button("Remove", key=f"del_{idx}"):
                        nav_system.blockages.pop(idx)
                        st.rerun()
                
                st.markdown("---")
        
        if nav_system.blockages:
            if st.button("Clear All", type="secondary"):
                nav_system.clear_blockages()
                st.rerun()
    
    # Main content
    main_col, control_col = st.columns([2, 1])
    
    with control_col:
        st.subheader("🎯 Route Control")
        
        # Status display
        if start_input and end_input:
            st.markdown('<div class="metric-card success-card">✅ <b>Ready</b><br>Locations configured</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="metric-card warning-card">⚠️ <b>Setup Required</b><br>Enter start and end locations</div>', unsafe_allow_html=True)
        
        # Obstacle status
        obs_count = len(nav_system.blockages)
        if obs_count == 0:
            st.markdown('<div class="metric-card success-card">🟢 <b>No Obstacles</b><br>Direct routing available</div>', unsafe_allow_html=True)
        else:
            if obs_count == 1:
                status_text = "🟡 <b>1 Obstacle</b><br>Avoidance needed"
                card_class = "warning-card"
            else:
                status_text = f"🔴 <b>{obs_count} Obstacles</b><br>Complex avoidance"
                card_class = "danger-card"
            st.markdown(f'<div class="metric-card {card_class}">{status_text}</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Calculate button
        calc_btn = st.button(
            "🎯 Calculate Route",
            type="primary",
            use_container_width=True,
            disabled=not (start_input and end_input)
        )
        
        # Route calculation
        if calc_btn:
            with st.spinner("Calculating optimal route..."):
                # Progress tracking
                progress = st.progress(0)
                
                # Geocode locations
                progress.progress(25)
                start_loc = nav_system.geocode_location(start_input)
                
                if start_loc:
                    progress.progress(50)
                    end_loc = nav_system.geocode_location(end_input)
                    
                    if end_loc:
                        progress.progress(75)
                        
                        # Calculate routes
                        if direct_mode or not nav_system.blockages:
                            route_result = nav_system.calculate_direct_route(start_loc, end_loc)
                            direct_result = None
                        else:
                            direct_result = nav_system.calculate_direct_route(start_loc, end_loc)
                            route_result = nav_system.calculate_optimal_route(start_loc, end_loc)
                        
                        progress.progress(100)
                        
                        # Store results
                        st.session_state.current_route = route_result
                        st.session_state.direct_reference = direct_result
                        st.session_state.start_location = start_loc
                        st.session_state.end_location = end_loc
                        
                        progress.empty()
                        
                        # Display results
                        if route_result.get("success"):
                            efficiency = route_result.get('efficiency_score', 0)
                            service = route_result.get('service_used', 'Unknown')
                            has_conflicts = route_result.get('conflicts', {}).get('has_conflicts', False)
                            
                            # Success message
                            if efficiency >= 80 and not has_conflicts:
                                st.balloons()
                                st.success("🏆 Excellent route calculated!")
                            elif efficiency >= 60:
                                st.success("✅ Good route found!")
                            else:
                                st.info("📊 Route calculated")
                            
                            # Metrics
                            st.markdown("### 📊 Route Summary")
                            
                            met_col1, met_col2 = st.columns(2)
                            with met_col1:
                                st.metric("Distance", f"{route_result['distance_km']:.1f} km")
                                st.metric("Service", service)
                            with met_col2:
                                st.metric("Duration", f"{route_result['estimated_time_minutes']:.0f} min")
                                st.metric("Efficiency", f"{efficiency:.1f}%")
                            
                            # Conflict status
                            if has_conflicts:
                                conflict_pct = route_result.get('conflicts', {}).get('conflict_percentage', 0)
                                st.error(f"⚠️ Route conflicts: {conflict_pct:.1f}%")
                            else:
                                st.success("🛡️ Route is safe!")
                                
                        else:
                            st.error("❌ Route calculation failed")
                            st.error(route_result.get('message', 'Unknown error'))
                    else:
                        st.error("❌ End location not found")
                else:
                    st.error("❌ Start location not found")
    
    with main_col:
        st.subheader("🗺️ Interactive Route Map")
        
        # Display map or instructions
        if hasattr(st.session_state, 'current_route') and st.session_state.current_route.get('success'):
            try:
                route_map = create_map_visualization(
                    st.session_state.start_location,
                    st.session_state.end_location,
                    st.session_state.current_route,
                    nav_system.blockages,
                    st.session_state.get('direct_reference')
                )
                
                st.components.v1.html(route_map._repr_html_(), height=600)
                
                # Route details
                with st.expander("📋 Detailed Analysis"):
                    route_info = st.session_state.current_route
                    
                    detail_col1, detail_col2 = st.columns(2)
                    
                    with detail_col1:
                        st.markdown("**Route Information:**")
                        st.write(f"• Type: {route_info.get('route_type', 'Unknown')}")
                        st.write(f"• Service: {route_info.get('service_used', 'Unknown')}")
                        st.write(f"• Method: {route_info.get('method', 'Unknown')}")
                        st.write(f"• Points: {route_info.get('total_waypoints', 0)} coordinates")
                    
                    with detail_col2:
                        st.markdown("**Performance Metrics:**")
                        st.write(f"• Distance: {route_info['distance_km']:.2f} km")
                        st.write(f"• Duration: {route_info['estimated_time_minutes']:.1f} minutes")
                        st.write(f"• Efficiency: {route_info.get('efficiency_score', 0):.1f}%")
                        st.write(f"• Impact: {route_info.get('blockage_impact', 0):.1f}%")
                    
                    # Conflicts
                    conflicts = route_info.get('conflicts', {})
                    if conflicts.get('has_conflicts'):
                        st.markdown("**⚠️ Conflict Analysis:**")
                        st.warning(f"Conflicts detected in {len(conflicts.get('conflict_points', []))} areas")
                    else:
                        st.success("✅ No conflicts - route is clear")
                        
            except Exception as e:
                st.error(f"Map display error: {str(e)}")
                
        else:
            st.info("""
            ### 🗺️ Route Map
            
            Configure your route to see the interactive map:
            
            1. **📍 Set Locations**: Enter start and end points
            2. **🚧 Add Obstacles**: Define areas to avoid (optional)
            3. **🎯 Calculate**: Click the calculate button
            
            **Map Features:**
            - 🟢 Direct routes (safe paths)
            - 🔵 Avoidance routes (obstacle bypass)
            - 🚧 Obstacle zones with safety buffers
            - 🎯 Strategic waypoints for navigation
            
            The system uses multiple routing services for maximum reliability.
            """)
    
    # Footer
    st.markdown("---")
    st.markdown(f"""
    <div style='text-align: center; color: #888; font-size: 0.9em;'>
    <strong>🎯 Advanced Route Optimizer v3.0</strong><br>
    Multi-Service Routing • Real-Time Conflict Detection • Intelligent Path Planning<br>
    Built by <strong>Pratham Tandon</strong> | VIT Vellore | User: <strong>{st.session_state.get('user_login', 'PratTandon')}</strong>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()