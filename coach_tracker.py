import streamlit as st
import pandas as pd
import datetime

# Set up your data files
data_file = 'data.csv'
fields_file = 'fields.csv'
master_list_file = 'master_list.csv'

# Function to read field names from fields.csv
def read_field_names():
    try:
        fields_df = pd.read_csv(fields_file)
        return fields_df['Field Name'].tolist()
    except FileNotFoundError:
        st.error(f'{fields_file} not found. Ensure it exists in the same directory.')
        return []

# Function to load the master list
def load_master_list():
    try:
        return pd.read_csv(master_list_file)
    except FileNotFoundError:
        st.error(f'{master_list_file} not found. Ensure it exists in the same directory.')
        return pd.DataFrame()

# Read field names and master list
field_names = read_field_names()
master_list = load_master_list()

# Define the expected columns for the data DataFrame
expected_columns = ['Date', 'Name', 'Action', 'Time', 'Field Name', 'Status', 'Clock In Time', 'Clock Out Time', 'Hours Spent']

# Try to read existing data, or create a new file if it doesn't exist
try:
    data = pd.read_csv(data_file)
    data['Time'] = pd.to_datetime(data['Time'], errors='coerce')
    data['Clock In Time'] = pd.to_datetime(data['Clock In Time'], errors='coerce')
    data['Clock Out Time'] = pd.to_datetime(data['Clock Out Time'], errors='coerce')
    # Ensure that the data DataFrame contains all necessary columns
    for col in expected_columns:
        if col not in data.columns:
            data[col] = None  # Add missing columns with None values
except FileNotFoundError:
    data = pd.DataFrame(columns=expected_columns)

# Function to record activity and check against the master list
def record_activity_and_check(name, action, field):
    current_time = datetime.datetime.now()

    # Check against the master list for the correct field
    assigned_field = master_list[master_list['Coach Name'] == name]['Assigned Field']
    status = 'Incorrect Field' if assigned_field.empty or field not in assigned_field.values else 'Correct Field'
    
    if action == 'Clock In':
        # Create a new record for clock in action
        new_data = pd.DataFrame([{
            'Date': current_time.date(),  # Add the date of the activity
            'Name': name, 
            'Action': action, 
            'Time': current_time,
            'Field Name': field, 
            'Status': status,
            'Clock In Time': current_time,
            'Clock Out Time': None,
            'Hours Spent': None
        }])
        return new_data

    elif action == 'Clock Out':
        # Find the most recent clock-in record for the coach
        recent_clock_in_idx = data[(data['Name'] == name) & (data['Action'] == 'Clock In')].last_valid_index()
        if pd.notna(recent_clock_in_idx):
            # Calculate hours spent
            clock_in_time = pd.to_datetime(data.at[recent_clock_in_idx, 'Clock In Time'])
            hours_spent = round((current_time - clock_in_time).total_seconds() / 3600.0, 2)
            
            # Update the existing record with clock out time and hours spent
            data.at[recent_clock_in_idx, 'Action'] = 'Clocked In/Out'
            data.at[recent_clock_in_idx, 'Clock Out Time'] = current_time
            data.at[recent_clock_in_idx, 'Hours Spent'] = hours_spent
            data.at[recent_clock_in_idx, 'Status'] = status  # Update status in case field is incorrect
            return None
        else:
            st.error('No recent clock-in record found for this coach.')
            return None

# Streamlit UI layout
st.title('Coach Activity Tracker')

# Sidebar for user inputs
with st.sidebar:
    st.header("Coach Input")
    coach_name = st.text_input("Coach Name:")
    field_name = st.selectbox("Field Name:", field_names)
    action = st.selectbox("Action:", ['Clock In', 'Clock Out'])
    
    if st.button('Submit'):
        new_record = record_activity_and_check(coach_name, action, field_name)
        if new_record is not None:
            data = pd.concat([data, new_record], ignore_index=True, sort=False)
        data.to_csv(data_file, index=False)
        st.success(f"Recorded: {coach_name} - {action} at {field_name}.")

# Displaying recorded data
if not data.empty:
    st.write("Recorded Activities:")
    display_columns = ['Date', 'Name', 'Action', 'Time', 'Field Name', 'Status', 'Clock In Time', 'Clock Out Time', 'Hours Spent']
    # Ensure only existing columns are displayed
    display_columns = [col for col in display_columns if col in data.columns]
    st.write(data[display_columns])

# Optional: Summary of activities by field
if not data.empty:
    st.write("Summary by Field:")
    summary = data.groupby('Field Name')['Name'].count().rename('Count').reset_index()
    st.write(summary)
