import sqlite3
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime, date, timedelta
import streamlit as st
import base64
from PIL import Image
import plotly.express as px
import openpyxl
import io
import os

# Function to connect to the SQLite database
def connect_to_database():
    db_connection_str = 'sqlite:///energydatabase.db'
    db_connection = create_engine(db_connection_str)
    return db_connection

# Email validation
def validate_email(email):
    return email.endswith('@pdx.edu')

# Page 1: Welcome page
def page1_welcome():
    logo = Image.open("PSU.png")
    st.image(logo, width=300)
    st.title("Energy Usage Database")    
    st.subheader("Please enter your details to proceed.")
    
    name = st.text_input("Name")
    email = st.text_input("Email")
    
    if st.button("Submit"):
        if name and validate_email(email):
            st.session_state['user_name'] = name  # Store name in session state
            st.session_state['user_email'] = email  # Store email in session state
            st.success("Welcome! Click below to proceed to the main dashboard.")
            st.button("Go to Dashboard", on_click=lambda: st.session_state.update({"current_page": "page2_dashboard"}))
        elif not validate_email(email):
            st.error("Please use a valid @pdx.edu email address.")
        else:
            st.error("Name and email are required.")

# Page 2: Main dashboard with sidebar
# Updated Page 2: Main dashboard with sidebar
def page2_dashboard():
    st.title("Energy Data Dashboard")

    # Sidebar for navigation
    st.sidebar.title("Navigation")

    # Use larger buttons for navigation
    if st.sidebar.button("Data Retrieval", use_container_width=True):
        st.session_state.page = "Data Retrieval"
    if st.sidebar.button("Update Entry", use_container_width=True):
        st.session_state.page = "Update Entry"
    if st.sidebar.button("Log Files", use_container_width=True):
        st.session_state.page = "Log Files"
    if st.sidebar.button("Usage Calculation", use_container_width=True):
        st.session_state.page = "Usage Calculation"
    if st.sidebar.button("Data Visualization", use_container_width=True):
        st.session_state.page = "Data Visualization"

    # Initialize session state if not already done
    if 'page' not in st.session_state:
        st.session_state.page = "Data Retrieval"

    # Display selected page based on session state
    if st.session_state.page == "Data Retrieval":
        page_data_retrieval()
    elif st.session_state.page == "Update Entry":
        page_update_entry()
    elif st.session_state.page == "Log Files":
        page_log_files()
    elif st.session_state.page == "Usage Calculation":
        page_usage()
    elif st.session_state.page == "Data Visualization":
        page_data_visualization()

    # Add some space and a divider in the sidebar
    st.sidebar.markdown("---")
    st.sidebar.markdown("## Current Page")
    st.sidebar.info(st.session_state.page)


# Helper function to get buildings and meters
def get_buildings_and_meters(energy_type):
    db_connection = connect_to_database()
    query = f"SELECT DISTINCT Building, Meter FROM {energy_type}_meter_building_map"
    df = pd.read_sql_query(query, con=db_connection)
    buildings = df['Building'].unique().tolist()
    meters_by_building = {building: df[df['Building'] == building]['Meter'].tolist() for building in buildings}
    return buildings, meters_by_building

def get_meter_date_ranges(energy_type, selected_meters):
    db_connection = connect_to_database()
    date_ranges = {}
    for meter in selected_meters:
        query = f"""
        SELECT MIN(DateTime) as min_date, MAX(DateTime) as max_date
        FROM {energy_type}
        WHERE [{meter}] IS NOT NULL
        """
        result = pd.read_sql_query(query, db_connection)
        if not result.empty and result['min_date'].iloc[0] and result['max_date'].iloc[0]:
            date_ranges[meter] = (
                pd.to_datetime(result['min_date'].iloc[0]).date(),
                pd.to_datetime(result['max_date'].iloc[0]).date()
            )
    return date_ranges

# Page: Data Retrieval
def page_data_retrieval():
    st.header("Data Retrieval")
    
    energy_type = st.selectbox("Select energy type", ["Electricity", "Water", "Gas"])
    
    buildings, meters_by_building = get_buildings_and_meters(energy_type)
    selected_building = st.selectbox('Select a building', buildings)
    selected_meters = st.multiselect('Select meters', meters_by_building[selected_building])

    if selected_meters:
        date_ranges = get_meter_date_ranges(energy_type, selected_meters)
        
        # Display date ranges for selected meters
        st.subheader("Available Date Ranges:")
        for meter, (min_date, max_date) in date_ranges.items():
            st.write(f"{meter}: {min_date} to {max_date}")

        # Date selection
        min_date = min(range[0] for range in date_ranges.values())
        max_date = max(range[1] for range in date_ranges.values())
        date_from = st.date_input("Date from", min_date, min_value=min_date, max_value=max_date)
        date_to = st.date_input("Date to", max_date, min_value=min_date, max_value=max_date)

        if st.button("Retrieve Data"):
            # Check if selected dates are within range
            if date_from < min_date or date_to > max_date:
                st.error("Selected date range is outside the available data range.")
            else:
                # Your existing data retrieval code here
                query = f"""SELECT [DateTime], {', '.join([f'[{meter}]' for meter in selected_meters])}, 
                            {', '.join([f'[{meter}_Usage]' for meter in selected_meters])} 
                            FROM {energy_type} WHERE [DateTime] BETWEEN :date_from AND :date_to"""
                
                df = pd.read_sql_query(query, con=connect_to_database(), params={"date_from": date_from, "date_to": date_to})
                st.write(df)

                # Excel download code here (unchanged)
    else:
        st.warning("Please select at least one meter.")

# Page: Update Entry in Database
def page_update_entry():
    st.header("Update Entry in Database")
    
    user_name = st.session_state.get('user_name', '')
    user_email = st.session_state.get('user_email', '')
    if not user_name or not user_email:
        st.error("Please log in first to update entries.")
        return

    st.write(f"Logged in as: {user_name} ({user_email})")

    energy_type = st.selectbox("Select energy type", ["Electricity", "Water", "Gas"])
    
    buildings, meters_by_building = get_buildings_and_meters(energy_type)
    selected_building = st.selectbox('Select a building', buildings)
    selected_meter = st.selectbox('Select a meter', meters_by_building[selected_building])

    db_connection = connect_to_database()
    with db_connection.connect() as conn:
        query = text(f"SELECT DISTINCT [DateTime] FROM {energy_type} WHERE [{selected_meter}] IS NOT NULL ORDER BY [DateTime]")
        result = conn.execute(query)
        datetimes = [row[0] for row in result]

    selected_datetime = st.selectbox("Select Date and Time", datetimes)

    existing_value = get_existing_value(energy_type, selected_datetime, selected_meter)
    if existing_value is not None:
        st.write(f"Current value: {existing_value}")
        new_value = st.number_input("Enter new value", value=float(existing_value))
        if st.button("Update Entry"):
            if abs(new_value - float(existing_value)) < 1e-6:
                st.warning("New value is the same as the existing value. No update needed.")
            else:
                updated_value = update_entry(energy_type, selected_datetime, selected_meter, new_value, user_name, user_email)
                if updated_value is not None:
                    st.success(f"Entry updated successfully. New value: {updated_value}")
                else:
                    st.error("Failed to update entry.")
    else:
        st.error(f"No existing value found for {selected_meter} at {selected_datetime}")

def get_existing_value(table_name, datetime_str, column_name):
    db_connection = connect_to_database()
    with db_connection.connect() as conn:
        query = text(f"SELECT [{column_name}] FROM {table_name} WHERE [DateTime] = :datetime")
        result = conn.execute(query, {"datetime": datetime_str}).fetchone()
    return result[0] if result else None

def update_entry(table_name, datetime_str, column_name, new_value, user_name, user_email):
    db_connection = connect_to_database()

    existing_value = get_existing_value(table_name, datetime_str, column_name)
    
    if existing_value is not None:
        with db_connection.connect() as conn:
            query = text(f"UPDATE {table_name} SET [{column_name}] = :new_value WHERE [DateTime] = :datetime")
            try:
                conn.execute(query, {"new_value": new_value, "datetime": datetime_str})
                conn.commit()

                # Log the update
                log_update(table_name, datetime_str, column_name, existing_value, new_value, user_name, user_email)

                # Verify the update
                updated_value = get_existing_value(table_name, datetime_str, column_name)
                return updated_value
            except Exception as e:
                st.error(f"Error updating entry: {e}")
                return None
    else:
        st.error(f"No existing value found for {table_name}, {datetime_str}, {column_name}")
        return None


def log_update(table_name, datetime_str, column_name, old_value, new_value, user_name, user_email):
    # Determine the correct folder based on the table_name
    if table_name.lower().startswith('electricity'):
        folder = 'electricity'
    elif table_name.lower().startswith('water'):
        folder = 'water'
    elif table_name.lower().startswith('gas'):
        folder = 'gas'
    else:
        st.error(f"Unknown table name: {table_name}")
        return

    log_entry = f"{datetime.now()}: {user_name} - {user_email} - changed - {table_name} - {column_name} - {datetime_str} - from {old_value} to {new_value}\n"
    log_file = os.path.join("log_files", folder, "entry_updates.log")
    
    try:
        # Ensure the directory exists (it should, but just in case)
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        # Append the new log entry to the file
        with open(log_file, 'a') as file:
            file.write(log_entry)
    except IOError as e:
        st.error(f"Error writing to log file: {e}")
        print(f"Failed to write to log file. Log entry: {log_entry}")
# Add this to your existing imports
from sqlalchemy import text

# Page: Log Files

import os

def page_log_files():
    st.header("Log Files")

    # Select energy type
    energy_type = st.selectbox("Select energy type", ["Electricity", "Water", "Gas"])

    # Define log file directory based on energy type
    log_directory = os.path.join("log_files", energy_type.lower())

    # Get all log files (.log and .txt) in the selected directory
    log_files = [f for f in os.listdir(log_directory) if f.endswith(('.log', '.txt'))]

    if log_files:
        selected_log = st.selectbox("Select a log file to view", log_files)
        selected_log_path = os.path.join(log_directory, selected_log)

        log_file_dict = {
            "outliers_log.txt": "Contains information about outliers found in the data and their replacements.",
            "high_usage_log.txt": "Records instances of exceptionally high usage detected in the data.",
            "entry_change_log.txt": "Lists occurrences where text entries were replaced with previous valid numeric values.",
            "column_change_log.txt": "Documents cases where entire columns were converted from text to numeric format.",
            "usage_log.txt": "Records usage calculations for the energy type.",
        }

        if energy_type.lower() == "gas":
            log_file_dict["missing_dates_log.txt"] = "the dates which are missing."

        if selected_log in log_file_dict:
            st.write(f"**Description:** {log_file_dict[selected_log]}")
        else:
            st.write("**Description:** Log file")

        log_content = read_log_file(selected_log_path)
        st.text_area(f"{energy_type} Log Content (Most Recent First)", log_content, height=300)
    else:
        st.warning(f"No log files found for {energy_type}.")

def read_log_file(file_path):
    try:
        with open(file_path, 'r') as file:
            return file.read()
    except FileNotFoundError:
        return f"Log file not found: {file_path}"
    except IOError:
        return f"Error reading log file: {file_path}"

def read_log_file(file_path):
    try:
        with open(file_path, 'r') as file:
            return file.read()
    except FileNotFoundError:
        return "Log file not found."
    except IOError:
        return "Error reading log file."

# Page: Usage Calculation
def page_usage():
    st.header("Usage Calculation")

    energy_type = st.selectbox("Select energy type", ["Electricity", "Water", "Gas"])
    
    buildings, meters_by_building = get_buildings_and_meters(energy_type)
    selected_building = st.selectbox('Select a building', buildings)
    selected_meters = st.multiselect('Select meters', meters_by_building[selected_building])

    if selected_meters:
        date_ranges = get_meter_date_ranges(energy_type, selected_meters)
        
        # Display date ranges for selected meters
        st.subheader("Available Date Ranges:")
        for meter, (min_date, max_date) in date_ranges.items():
            st.write(f"{meter}: {min_date} to {max_date}")

        # Date selection
        min_date = min(range[0] for range in date_ranges.values())
        max_date = max(range[1] for range in date_ranges.values())
        date_from = st.date_input("Date from", min_date, min_value=min_date, max_value=max_date)
        date_to = st.date_input("Date to", max_date, min_value=min_date, max_value=max_date)

        if st.button("Calculate Usage"):
            if date_from < min_date or date_to > max_date:
                st.error("Selected date range is outside the available data range.")
            else:
                query = f"""SELECT [DateTime], {', '.join([f'[{meter}_Usage]' for meter in selected_meters])} 
                            FROM {energy_type} WHERE [DateTime] BETWEEN :date_from AND :date_to"""
                
                df = pd.read_sql_query(query, con=connect_to_database(), params={"date_from": date_from, "date_to": date_to})

                for meter in selected_meters:
                    total_usage = df[f'{meter}_Usage'].sum()
                    st.markdown(f"**Total Usage for {selected_building} - {meter}:**")
                    st.markdown(f"<h2 style='text-align: center; color: #1c6b94;'>{total_usage:.2f}</h2>", unsafe_allow_html=True)

                fig = px.bar(df, x='DateTime', y=[f'{meter}_Usage' for meter in selected_meters], title=f"Usage for {selected_building}")
                st.plotly_chart(fig)
    else:
        st.warning("Please select at least one meter.")

        

# Page: Data Visualization
def page_data_visualization():
    st.header("Data Visualization")

    energy_type = st.selectbox("Select energy type", ["Electricity", "Water", "Gas"])
    
    buildings, meters_by_building = get_buildings_and_meters(energy_type)
    selected_building = st.selectbox('Select a building', buildings)
    selected_meters = st.multiselect('Select meters', meters_by_building[selected_building])

    if selected_meters:
        date_ranges = get_meter_date_ranges(energy_type, selected_meters)
        
        # Display date ranges for selected meters
        st.subheader("Available Date Ranges:")
        for meter, (min_date, max_date) in date_ranges.items():
            st.write(f"{meter}: {min_date} to {max_date}")

        # Date selection
        min_date = min(range[0] for range in date_ranges.values())
        max_date = max(range[1] for range in date_ranges.values())
        date_from = st.date_input("Date from", min_date, min_value=min_date, max_value=max_date)
        date_to = st.date_input("Date to", max_date, min_value=min_date, max_value=max_date)

        if st.button("Visualize Data"):
            if date_from < min_date or date_to > max_date:
                st.error("Selected date range is outside the available data range.")
            else:
                query = f"""SELECT [DateTime], {', '.join([f'[{meter}_Usage]' for meter in selected_meters])} 
                            FROM {energy_type} WHERE [DateTime] BETWEEN :date_from AND :date_to"""
                
                df = pd.read_sql_query(query, con=connect_to_database(), params={"date_from": date_from, "date_to": date_to})
                df['DateTime'] = pd.to_datetime(df['DateTime'])
                df = df.set_index('DateTime')

                fig = px.line(df, x=df.index, y=df.columns, title=f"{energy_type} Usage Over Time for {selected_building}")
                st.plotly_chart(fig)
    else:
        st.warning("Please select at least one meter.")

# Log file reader helper function
def read_log_file(file_path):
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()
        # Reverse the order of lines and join them back into a single string
        return ''.join(reversed(lines))
    except FileNotFoundError:
        return f"Log file not found: {file_path}"
    except IOError:
        return f"Error reading log file: {file_path}"

# Routing logic to manage page navigation
if "current_page" not in st.session_state:
    st.session_state["current_page"] = "page1_welcome"

# Dictionary to map page names to functions
pages = {
    "page1_welcome": page1_welcome,
    "page2_dashboard": page2_dashboard,
}

# Execute the current page function
pages[st.session_state["current_page"]]()