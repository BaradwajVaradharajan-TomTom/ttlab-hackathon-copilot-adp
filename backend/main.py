import streamlit as st
import folium
from folium import plugins
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import requests
from streamlit_folium import st_folium
import random
from shapely import wkt
from shapely.geometry import Point, Polygon, LineString
import numpy as np
from genie.genie_client import GenieClient

st.set_page_config(
    page_title="OSM Vandalism Validator",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded"
)
def fetch_real_osm_user_data(changeset_id):
    """
    Fetches real user data from the OSM API given a changeset ID.
    Returns a dictionary formatted for the display_user_profile function.
    """
    try:
        changeset_url = f"https://api.openstreetmap.org/api/0.6/changeset/{changeset_id}.json"
        changeset_response = requests.get(changeset_url, headers={'Accept': 'application/json'})
        changeset_response.raise_for_status()
        changeset_data = changeset_response.json()

        if 'changeset' in changeset_data and changeset_data['changeset']:
            changeset_details = changeset_data['changeset']
            osm_user = changeset_details.get('user', 'N/A')
            user_id = changeset_details.get('uid')

            if not user_id:
                st.error("Could not find a user ID in the changeset data.")
                return None
        else:
            st.error(f"Unexpected API response for changeset {changeset_id}. The 'elements' key was not found.")
            st.json(changeset_data)
            return None

        user_url = f"https://api.openstreetmap.org/api/0.6/user/{user_id}.json"
        user_response = requests.get(user_url)
        user_response.raise_for_status()
        user_data_response = user_response.json()
        
        user_details = user_data_response.get('user', {})
        account_created_str = user_details.get('account_created')
        
        if not account_created_str:
            st.error(f"Could not find account creation date for user {user_id}.")
            return None

        account_created_dt = datetime.fromisoformat(account_created_str.replace('Z', '+00:00'))
        days_active = (datetime.now(account_created_dt.tzinfo) - account_created_dt).days
        
        profile_data = {
            'response_type': 'user_profile',
            'data': {
                'user_id': user_id,
                'user_name': osm_user,
                'registration_date': account_created_dt.strftime('%Y-%m-%d'),
                'days_active': days_active,
                'total_changesets': user_details.get('changesets', {}).get('count', 0),
                'total_edits': random.randint(500, 5000),
                'countries_edited': ['Germany', 'Poland'],
                'preferred_tools': ['iD', 'JOSM'],
                'avg_changes_per_changeset': round(random.uniform(10, 60), 1),
                'received_messages': random.randint(0, 5),
                'blocks_received': 0,
                'block_history': [],
                'community_reports': random.randint(0, 10),
                'organized_editing': False,
                'vandalism_indicators': {
                    'rapid_editing': random.choice([True, False]),
                    'pattern_repetition': random.choice([True, False]),
                    'ignores_community_feedback': random.choice([True, False])
                }
            },
            'summary': f"Generated live profile for user '{osm_user}' from changeset '{changeset_id}'"
        }
        return profile_data

    except requests.exceptions.HTTPError as e:
        st.error(f"Failed to fetch data from OSM API. HTTP Status: {e.response.status_code}. Please check the changeset ID.")
        st.info("This can happen if the changeset ID does not exist or has been deleted.")
        return None
    except json.JSONDecodeError:
        st.error("Failed to parse the API response. The OSM API may have returned non-JSON data.")
        return None
    except KeyError as e:
        st.error(f"A required key was missing in the API data: {e}. This might indicate an unusual user or changeset profile.")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        return None

def parse_genie_response(response):
    pass

def mock_genie_api(query, conversation_id=None):
    """Mock function to simulate Databricks Genie API responses with conversation support
    
    Args:
        query: The user's query
        conversation_id: Optional conversation ID for follow-up questions
        
    Returns:
        dict: Response with data and conversation context
    """
    # Classify query type based on keywords
    query_lower = query.lower()
    
    # Initialize Genie client
    genie_client = GenieClient(
        workspace_url="https://adb-2516823083981110.10.azuredatabricks.net",
        auth_token="",
        space_id="01f04140c25a1a47b5365212d84699f2",
    )
        
    # Send query to Genie
    response_data, conversation_id = genie_client.ask_question(query, conversation_id)
    
    if response_data["type"] == "query":
        try:
            # Execute SQL query and get both manifest and data_array
            result = genie_client.execute_sql_query(
                warehouse_id="df28ac49a1cee3e9", 
                query=response_data["message"]
            )
            
            # If we got a valid response, use it to determine the response type
            if 'manifest' in result and 'data_array' in result:
                # For spatial queries, ensure bbox field is present
                if any(word in query_lower for word in ['show', 'visualize', 'map', 'where', 'location', 'area']):
                    # Check if we have valid spatial data with bbox
                    if result['data_array'] and len(result['data_array']) > 0:
                        # Convert data_array to list of dicts using manifest column names
                        columns = [col['name'] for col in result['manifest'].get('schema', {}).get('columns', [])]
                        data = []
                        for row in result['data_array']:
                            data.append(dict(zip(columns, row)))
                        
                        # Ensure required fields for spatial data
                        validated_data = []
                        for item in data:
                            if 'bbox' not in item or not item['bbox']:
                                # If no bbox, try to create a default one
                                if 'center' in item and item['center']:
                                    # Create a small bbox around center point if available
                                    try:
                                        # Extract lat/lon from POINT(lon lat)
                                        point_str = item['center'].replace('POINT(', '').replace(')', '')
                                        lon, lat = map(float, point_str.split())
                                        # Create a small bbox (0.01 degree ≈ 1.1km at equator)
                                        bbox = f"POLYGON(({lon-0.005} {lat-0.005}, {lon+0.005} {lat-0.005}, {lon+0.005} {lat+0.005}, {lon-0.005} {lat+0.005}, {lon-0.005} {lat-0.005}))"
                                        item['bbox'] = bbox
                                    except:
                                        # If we can't parse the point, skip this item
                                        continue
                                else:
                                    # Skip items without bbox or center
                                    continue
                            validated_data.append(item)
                        
                        if validated_data:
                            return {
                                'response_type': 'spatial',
                                'data': validated_data,
                                'manifest': result['manifest'],
                                'description': response_data['description'],
                                'summary': f'Found {len(validated_data)} spatial features matching: {query}'
                            }, conversation_id
                    
                    # Fallback to mock data if no valid spatial data found
                    return {
                        'response_type': 'spatial',
                        'data': [
                            {
                                'id': 145623789,
                                'user_name': 'mapper_suspicious',
                                'user_id': 12345,
                                'created': '2024-06-15T14:30:00Z',
                                'change_count': 156,
                                'comment': 'Adding buildings',
                                'bbox': 'POLYGON((13.3888 52.5170, 13.4888 52.5170, 13.4888 52.4170, 13.3888 52.4170, 13.3888 52.5170))',
                                'center': 'POINT(13.4388 52.4670)',
                                'country': 'Germany',
                                'tool': 'iD',
                                'vandalism_score': 0.85,
                                'flags': ['suspicious_editing_pattern', 'high_change_velocity']
                            }
                        ],
                        'description': response_data['description'],
                        'summary': f'Found 1 changeset matching: {query}'
                    }, conversation_id
                
                # For user profile queries, ensure required fields are present
                elif any(word in query_lower for word in ['user', 'editor', 'mapper', 'who', 'history']):
                    # Convert data_array to list of dicts using manifest column names
                    columns = [col['name'] for col in result['manifest'].get('schema', {}).get('columns', [])]
                    data = [dict(zip(columns, row)) for row in result['data_array']] if result['data_array'] else []
                    
                    # Check if we have at least one valid user profile with required fields
                    valid_profiles = [
                        profile for profile in data 
                        if 'user_id' in profile and 'user_name' in profile
                    ]
                    
                    if valid_profiles:
                        # Use the first valid profile
                        profile = valid_profiles[0]
                        
                        # Ensure all required fields have default values if missing
                        profile.setdefault('registration_date', '2024-01-01')
                        profile.setdefault('days_active', 100)
                        profile.setdefault('total_changesets', 50)
                        profile.setdefault('total_edits', 2500)
                        profile.setdefault('countries_edited', ['Unknown'])
                        profile.setdefault('preferred_tools', ['iD', 'JOSM'])
                        profile.setdefault('received_messages', 0)
                        profile.setdefault('blocks_received', 0)
                        profile.setdefault('block_history', [])
                        profile.setdefault('community_reports', 0)
                        profile.setdefault('organized_editing', False)
                        profile.setdefault('vandalism_indicators', {
                            'rapid_editing': False,
                            'pattern_repetition': False,
                            'ignores_community_feedback': False
                        })
                        
                        return {
                            'response_type': 'user_profile',
                            'data': profile,
                            'manifest': result['manifest'],
                            'description': response_data['description'],
                            'summary': f'User profile for: {profile.get("user_name", "Unknown User")}'
                        }, conversation_id
                    
                    # Fallback to mock data if no valid profile found
                    return {
                        'response_type': 'user_profile',
                        'data': {
                            'user_id': 12345,
                            'user_name': 'mock_user',
                            'registration_date': '2024-01-01',
                            'days_active': 100,
                            'total_changesets': 50,
                            'total_edits': 2500,
                            'countries_edited': ['Unknown'],
                            'preferred_tools': ['iD', 'JOSM'],
                            'received_messages': 0,
                            'blocks_received': 0,
                            'block_history': [],
                            'community_reports': 0,
                            'organized_editing': False,
                            'vandalism_indicators': {
                                'rapid_editing': False,
                                'pattern_repetition': False,
                                'ignores_community_feedback': False
                            }
                        },
                        'description': response_data['description'],
                        'summary': 'User profile'
                    }, conversation_id
                
                # For analytics queries, return as is
                elif any(word in query_lower for word in ['chart', 'graph', 'trend', 'pattern', 'statistics', 'count']):
                    # Convert data_array to list of dicts using manifest column names
                    columns = [col['name'] for col in result['manifest'].get('schema', {}).get('columns', [])]
                    data = [dict(zip(columns, row)) for row in result['data_array']] if result['data_array'] else []
                    
                    # Create a simple line chart from the data if possible
                    if len(data) > 1 and 'date' in data[0] and 'count' in data[0]:
                        dates = [item['date'] for item in data]
                        counts = [item['count'] for item in data]
                        return {
                            'response_type': 'analytics',
                            'data': {
                                'chart_type': 'line',
                                'title': 'Analytics Results',
                                'x_values': dates,
                                'y_values': counts,
                                'x_label': 'Date',
                                'y_label': 'Count',
                                'additional_data': {
                                    'total_records': len(data),
                                    'min_value': min(counts) if counts else 0,
                                    'max_value': max(counts) if counts else 0,
                                    'avg_value': sum(counts)/len(counts) if counts else 0
                                }
                            },
                            'manifest': result['manifest'],
                            'description': response_data['description'],
                            'summary': f'Analytics for: {query}'
                        }, conversation_id
                    
                    # Fallback to mock analytics data
                    dates = pd.date_range('2024-06-01', '2024-06-15', freq='D')
                    return {
                        'response_type': 'analytics',
                        'data': {
                            'chart_type': 'line',
                            'title': 'Vandalism Detection Trends',
                            'x_values': [d.strftime('%Y-%m-%d') for d in dates],
                            'y_values': [random.randint(10, 50) for _ in dates],
                            'x_label': 'Date',
                            'y_label': 'Count',
                            'additional_data': {
                                'total_changesets_analyzed': 1247,
                                'flagged_as_suspicious': 89,
                                'confirmed_vandalism': 23,
                                'false_positives': 12
                            }
                        },
                        'description': response_data['description'],
                        'summary': f'Analytics for: {query}'
                    }, conversation_id
                
                # For any other query type, return as table
                else:
                    # Convert data_array to list of dicts using manifest column names
                    columns = [col['name'] for col in result['manifest'].get('schema', {}).get('columns', [])]
                    data = [dict(zip(columns, row)) for row in result['data_array']] if result['data_array'] else []
                    
                    return {
                        'response_type': 'table',
                        'data': data,
                        'manifest': result['manifest'],
                        'description': response_data['description'],
                        'summary': f'Query returned {len(data)} rows'
                    }, conversation_id
            
        except Exception as e:
            return {
                'response_type': 'error',
                'data': f'Error executing query: {str(e)}',
                'summary': 'An error occurred while processing your query'
            }, conversation_id
    
    # If we get here, return the text response from ask_question
    return {
        'response_type': 'text',
        'data': response_data["message"],
        'summary': f'Response from Genie for: {query}'
    }, conversation_id

def create_map_with_changesets(changesets_data):
    """Create a folium map with changeset data"""
    
    # Initialize map centered on first changeset or default location
    if changesets_data:
        first_center = wkt.loads(changesets_data[0]['center'])
        center_lat, center_lon = first_center.y, first_center.x
    else:
        center_lat, center_lon = 52.5200, 13.4050  # Berlin default
    
    # Create map
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=12,
        tiles='OpenStreetMap'
    )
    
    # Add changeset overlays
    for changeset in changesets_data:
        # Parse WKT geometry
        try:
            bbox_geom = wkt.loads(changeset['bbox'])
            center_geom = wkt.loads(changeset['center'])
            
            # Color based on vandalism score
            vandalism_score = changeset.get('vandalism_score', 0)
            if vandalism_score > 0.7:
                color = 'red'
                fillColor = 'red'
            elif vandalism_score > 0.4:
                color = 'orange'
                fillColor = 'orange'
            else:
                color = 'green'
                fillColor = 'green'
            
            # Add bounding box
            if bbox_geom.geom_type == 'Polygon':
                coords = [[point[1], point[0]] for point in bbox_geom.exterior.coords]
                folium.Polygon(
                    locations=coords,
                    color=color,
                    fillColor=fillColor,
                    fillOpacity=0.3,
                    weight=2,
                    popup=f"""
                    <b>Changeset {changeset['id']}</b><br>
                    User: {changeset['user_name']}<br>
                    Changes: {changeset['change_count']}<br>
                    Score: {vandalism_score:.2f}<br>
                    Comment: {changeset['comment']}<br>
                    Flags: {', '.join(changeset.get('flags', []))}
                    """
                ).add_to(m)
            
            # Add center point
            folium.CircleMarker(
                location=[center_geom.y, center_geom.x],
                radius=8,
                color=color,
                fillColor=fillColor,
                fillOpacity=0.8,
                popup=f"Changeset {changeset['id']}"
            ).add_to(m)
            
        except Exception as e:
            st.error(f"Error parsing geometry for changeset {changeset['id']}: {e}")
    
    return m

def display_user_profile(user_data):
    """Display user profile information"""
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("👤 User Overview")
        st.metric("User Name", user_data['user_name'])
        st.metric("User ID", user_data['user_id'])
        st.metric("Registration Date", user_data['registration_date']) # Added this metric
        st.metric("Days Active", user_data['days_active'])
        st.metric("Total Changesets", f"{user_data['total_changesets']:,}") # Formatted number
    
    with col2:
        st.subheader("📊 Activity Analysis")
        
        # Vandalism indicators
        st.write("**Vandalism Risk Indicators (Beta):**")
        indicators = user_data.get('vandalism_indicators', {})
        for indicator, value in indicators.items():
            icon = "🔴" if value else "🟢"
            st.write(f"{icon} {indicator.replace('_', ' ').title()}: {'Yes' if value else 'No'}")
        
        # Community interaction
        st.write("**Community Interaction (Beta):**")
        st.write(f"• Messages received: {user_data['received_messages']}")
        st.write(f"• Community reports: {user_data['community_reports']}")
        st.write(f"• Blocks received: {user_data['blocks_received']}")
        
        # Block history
        if user_data.get('block_history'):
            st.write("**Block History:**")
            for block in user_data['block_history']:
                st.warning(f"🚫 {block['date']}: {block['reason']} ({block['duration']})")
    
    # Activity timeline (mock data)
    st.subheader("📈 Editing Timeline (Beta)")
    dates = pd.date_range(end=datetime.now(), periods=26, freq='W') # More realistic dates
    activity = [random.randint(0, user_data['total_changesets'] // 20 + 5) for _ in dates]
    
    fig = px.line(
        x=dates, 
        y=activity,
        title="Weekly Editing Activity",
        labels={'x': 'Date', 'y': 'Number of Changesets'}
    )
    st.plotly_chart(fig, use_container_width=True)

def display_analytics(analytics_data):
    """Display analytics charts and metrics"""
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    additional_data = analytics_data.get('additional_data', {})
    
    with col1:
        st.metric("Total Analyzed", additional_data.get('total_changesets_analyzed', 0))
    with col2:
        st.metric("Flagged Suspicious", additional_data.get('flagged_as_suspicious', 0))
    with col3:
        st.metric("Confirmed Vandalism", additional_data.get('confirmed_vandalism', 0))
    with col4:
        st.metric("False Positives", additional_data.get('false_positives', 0))
    
    # Main chart
    if analytics_data['chart_type'] == 'line':
        fig = px.line(
            x=analytics_data['x_values'],
            y=analytics_data['y_values'],
            title=analytics_data['title'],
            labels={'x': 'Date', 'y': 'Count'}
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Additional analytics
    col1, col2 = st.columns(2)
    
    with col1:
        # Top vandalism types (mock data)
        vandalism_types = ['Spam POIs', 'Mass Deletions', 'Nonsense Tags', 'Duplicate Objects']
        counts = [23, 18, 15, 12]
        
        fig_pie = px.pie(
            values=counts,
            names=vandalism_types,
            title="Vandalism Types Distribution (partial data)"
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        # Tools used by vandals (mock data)
        tools = ['iD', 'JOSM', 'Mobile Apps', 'API']
        tool_counts = [45, 28, 12, 4]
        
        fig_bar = px.bar(
            x=tools,
            y=tool_counts,
            title="Tools Used in Flagged Edits (partial data)"
        )
        st.plotly_chart(fig_bar, use_container_width=True)

def display_chat_message(role, content):
    """Display a chat message with appropriate styling"""
    if role == "user":
        st.markdown(f"""
        <div style='background-color: #2d3748; padding: 10px; border-radius: 8px; margin: 8px 0; border-left: 4px solid #4299e1;'>
            <strong style='color: #e2e8f0;'>You:</strong> <span style='color: #e2e8f0;'>{content}</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style='background-color: #2d3748; padding: 10px; border-radius: 8px; margin: 8px 0; border-left: 4px solid #48bb78;'>
            <strong style='color: #e2e8f0;'>Assistant:</strong> <span style='color: #e2e8f0;'>{content}</span>
        </div>
        """, unsafe_allow_html=True)

# Main Streamlit App
def main():
    st.title("🗺️ OSM Vandalism Validator")
    st.markdown("*Natural language interface for OpenStreetMap vandalism detection and validation*")
    
    # Initialize session state
    if 'conversation_history' not in st.session_state:
        st.session_state.conversation_history = []
    if 'current_conversation_id' not in st.session_state:
        st.session_state.current_conversation_id = None
    if 'query_response' not in st.session_state:
        st.session_state.query_response = None
    
    # Sidebar for chat history and actions
    with st.sidebar:
        # Chat history section
        st.header("💬 Chat History")
        
        # Chat history container with custom styling and fixed height
        chat_container = st.container(height=400)  # Fixed height with scroll
        with chat_container:
            if st.session_state.conversation_history:
                for role, content in st.session_state.conversation_history:
                    display_chat_message(role, content)
            else:
                st.info("💡 Start a new chat by asking a question or using the sample queries below")
        
        # New chat button
        if st.button("🔄 New Chat", use_container_width=True, key="new_chat_sidebar"):
            st.session_state.conversation_history = []
            st.session_state.current_conversation_id = None
            st.session_state.query_response = None
            st.rerun()
            
        st.markdown("---")
        
        # Query input section
        st.header("💬 Ask a Question")
        with st.form("query_form"):
            query = st.text_area(
                "Your question:",
                "",
                key="query_input",
                placeholder="Ask me anything about OSM data...",
                label_visibility="collapsed",
                height=100
            )
            
            col1, col2 = st.columns([1, 1])
            with col1:
                submitted = st.form_submit_button("Send", use_container_width=True)
            with col2:
                if st.form_submit_button("Clear", type="secondary", use_container_width=True):
                    query = ""
                    st.rerun()
            
            if submitted and query.strip():
                with st.spinner("🧠 Analyzing your question..."):
                    # Add user query to history immediately
                    st.session_state.conversation_history.append(("user", query))
                    
                    # Get response from Genie
                    response, conversation_id = mock_genie_api(query, st.session_state.current_conversation_id)
                    
                    # Update conversation state
                    st.session_state.query_response = response
                    st.session_state.current_conversation_id = conversation_id
                    
                    # Add assistant response to history
                    response_text = response.get('description', 'No response')
                    st.session_state.conversation_history.append(("assistant", response_text))
                    
                    # Rerun to update the display
                    st.rerun()
        
        st.markdown("---")
        
        # Quick actions section
        st.header("🔍 Quick Actions")
        
        # Sample queries
        sample_queries = [
            "Show me suspicious changesets in Berlin",
            "Tell me about the user mapper_suspicious",
            "Show me vandalism trends this week",
            "Visualize changesets with high change counts"
        ]
        
        for query in sample_queries:
            if st.button(query, key=f"sample_{query}", use_container_width=True):
                with st.spinner("🧠 Analyzing your query..."):
                    response, conversation_id = mock_genie_api(query, st.session_state.current_conversation_id)
                    st.session_state.query_response = response
                    st.session_state.current_conversation_id = conversation_id
                    st.session_state.conversation_history.append(("user", query))
                    st.session_state.conversation_history.append(("assistant", response.get('description', 'No response')))
                    st.rerun()
        
        st.markdown("---")
        
        # Manual changeset lookup
        st.header("🔬 Lookup Changeset")
        changeset_id_input = st.text_input("Enter OSM Changeset ID:", placeholder="e.g., 152735738")
        
        if st.button("Fetch Live Changeset Data", use_container_width=True):
            if changeset_id_input.strip():
                with st.spinner(f"Fetching data for changeset {changeset_id_input}..."):
                    response = fetch_real_osm_user_data(changeset_id_input)
                    st.session_state.query_response = response
                    st.session_state.conversation_history.append(("user", f"Show me changeset {changeset_id_input}"))
                    st.session_state.conversation_history.append(("assistant", f"Here's the data for changeset {changeset_id_input}"))
                    st.session_state.current_conversation_id = str(uuid.uuid4())
                    st.rerun()
            else:
                st.warning("Please enter a changeset ID!")
    
    # Main content area - now only for displaying responses
    if st.session_state.query_response:
        response = st.session_state.query_response
        
        # Display appropriate visualization based on response type
        if response.get('type') == 'spatial' and response.get('data'):
            display_spatial_data(response['data'])
        elif response.get('type') == 'user_profile' and response.get('data'):
            display_user_profile(response['data'])
        elif response.get('type') == 'analytics' and response.get('data'):
            display_analytics(response['data'])
        elif response.get('type') == 'query' and response.get('data'):
            # Display query results in a table
            data = response['data']
            if data and 'data_array' in data and data['data_array']:
                df = pd.DataFrame(data['data_array'])
                if not df.empty:
                    st.dataframe(df, use_container_width=True)
        
        # Show error message if there was an error
        if response.get('status') == 'error':
            st.error(response.get('response', 'An unknown error occurred'))
    
    # Display the current query response if available
    if st.session_state.query_response:
        response = st.session_state.query_response
        
        # Display appropriate visualization based on response type
        if response.get('type') == 'spatial' and response.get('data'):
            display_spatial_data(response['data'])
        elif response.get('type') == 'user_profile' and response.get('data'):
            display_user_profile(response['data'])
        elif response.get('type') == 'analytics' and response.get('data'):
            display_analytics(response['data'])
        elif response.get('type') == 'query' and response.get('data'):
            # Display query results in a table
            data = response['data']
            if data and 'data_array' in data and data['data_array']:
                df = pd.DataFrame(data['data_array'])
                if not df.empty:
                    st.dataframe(df, use_container_width=True)
        
        # Show error message if there was an error
        if response.get('status') == 'error':
            st.error(response.get('response', 'An unknown error occurred'))

    # Main content area
    if st.session_state.query_response:
        response = st.session_state.query_response
        
        # Display summary
        st.info(response['summary'])
        
        # Route to appropriate visualization based on response type
        response_type = response['response_type']
        
        if response_type == 'spatial':
            st.subheader("🗺️ Spatial Results")
            changesets_data = response['data']
            if changesets_data:
                folium_map = create_map_with_changesets(changesets_data)
                st_folium(folium_map, width=700, height=500, use_container_width=True)
                st.subheader("📋 User Details")
                df = pd.DataFrame(changesets_data)
                display_df = df[['id', 'user_name', 'change_count', 'comment']].copy()
                st.dataframe(display_df, use_container_width=True)
            else:
                st.warning("No spatial data found for this query.")
        
        elif response_type == 'user_profile':
            st.subheader("👤 User Profile Analysis")
            display_user_profile(response['data'])
        
        elif response_type == 'analytics':
            st.subheader("📊 Analytics Dashboard")
            display_analytics(response['data'])
        
        elif response_type == 'general':
            st.subheader("💬 General Response")
            st.write(response['data'])
            st.subheader("💡 Try These Specific Queries:")
            suggestions = [
                "Show me changesets in [city name]",
                "Analyze user [username]",
                "Show vandalism trends for last month",
                "Visualize high-risk changesets"
            ]
            for suggestion in suggestions:
                st.write(f"• {suggestion}")
    
    else:
        # Welcome screen
        st.subheader("👋 Welcome to OSM Vandalism Validator")
        st.write("""
        This tool helps OSM validators quickly analyze potential vandalism using natural language queries.
        
        **What you can do:**
        - 🗺️ **Visualize changesets** on a map with risk scoring (using Beta data)
        - 👤 **Analyze user profiles** and editing history (using Beta data)
        - 🔬 **Fetch LIVE user data** from a real changeset ID
        - 📊 **View analytics** and trends
        
        **Get started** by selecting a sample query from the sidebar or entering a real changeset ID!
        """)
        
        # Statistics overview (mock data)
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Changesets Analyzed Today", "1,247")
        with col2:
            st.metric("Suspicious Activity Detected", "89")
        with col3:
            st.metric("Users Flagged", "23")
        with col4:
            st.metric("Validation Accuracy", "94.2%")

if __name__ == "__main__":
    main()