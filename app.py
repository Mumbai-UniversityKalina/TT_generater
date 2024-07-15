# timetable_generator/main.py

import streamlit as st
import pandas as pd
import requests
from fpdf import FPDF
from datetime import datetime, timedelta

# PocketBase API URL
POCKETBASE_URL = 'https://mucollegdb.pockethost.io'

# Function to fetch all courses from PocketBase
def fetch_courses():
    response = requests.get(f'{POCKETBASE_URL}/api/collections/courses/records?perPage=1080')
    if response.status_code == 200:
        return response.json()['items']
    return []

# Function to fetch subjects for a given course from PocketBase
def fetch_subjects(course_id):
    response = requests.get(f'{POCKETBASE_URL}/api/collections/subjects/records', params={'filter': f'subject_of="{course_id}"'})
    if response.status_code == 200:
        return response.json()['items']
    return []

# Function to create PDF from timetable DataFrame
def create_pdf(timetable_df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font('Arial', 'B', 12)
    
    # Add table header
    pdf.cell(40, 10, 'Date', 1)
    pdf.cell(90, 10, 'Subject', 1)
    pdf.cell(60, 10, 'Time', 1)
    pdf.ln()
    
    # Add table rows
    for index, row in timetable_df.iterrows():
        pdf.cell(40, 10, row['Date'], 1)
        pdf.cell(90, 10, row['Subject'], 1)
        pdf.cell(60, 10, row['Time'], 1)
        pdf.ln()
    
    return pdf

# Streamlit app layout
st.title('Timetable Generator')

# Step 1: Select Course
courses = fetch_courses()
course_names = [course['course_name'] for course in courses]

selected_course_name = st.selectbox('Select Course', course_names, index=0)

if selected_course_name:
    selected_course = next(course for course in courses if course['course_name'] == selected_course_name)
    
    # Step 2: Select Start Date and End Date
    st.write("Select the timetable duration:")
    start_date = st.date_input('Start Date', value=datetime.today(), format='DD/MM/YYYY')
    end_date = st.date_input('End Date', value=datetime.today() + timedelta(days=30), format='DD/MM/YYYY')

    if start_date and end_date:
        # Function to filter out Sundays
        def is_not_sunday(date):
            return date.weekday() != 6

        # Generate a list of dates excluding Sundays
        all_dates = pd.date_range(start=start_date, end=end_date)
        available_dates = list(filter(is_not_sunday, all_dates))

        # Step 3: Set Dates for Subjects
        subjects = fetch_subjects(selected_course['id'])
        subject_dates = {}
        selected_dates = set()

        st.write(f"Set dates and times for subjects in {selected_course_name} (excluding Sundays):")

        for i, subject in enumerate(subjects):
            with st.expander(f'{subject["subject_name"]}'):
                while True:
                    try:
                        date = st.date_input(f'Select date for {subject["subject_name"]}', value=start_date, key=f'{subject["id"]}_{i}', min_value=start_date, max_value=end_date)
                        if date.weekday() == 6:
                            st.error(f'The date {date.strftime("%d/%m/%Y")} is a Sunday. Please choose a different date.')
                        elif date in selected_dates:
                            st.error(f'The date {date.strftime("%d/%m/%Y")} is already selected. Please choose a different date.')
                        else:
                            break
                    except Exception as e:
                        st.error(f'Error: {e}')
                        break

                # Add time range input for the subject
                start_time = st.text_input(f'Start time for {subject["subject_name"]} (e.g., 9:00 AM)', key=f'{subject["id"]}_start_time_{i}')
                end_time = st.text_input(f'End time for {subject["subject_name"]} (e.g., 12:00 PM)', key=f'{subject["id"]}_end_time_{i}')

                subject_dates[subject['subject_name']] = {'date': date, 'time': f'{start_time} to {end_time}'}
                selected_dates.add(date)

        if st.button('Generate Timetable'):
            timetable_data = []
            for subject, info in subject_dates.items():
                timetable_data.append({'Date': info['date'].strftime('%d/%m/%Y'), 'Subject': subject, 'Time': info['time']})
            
            timetable_df = pd.DataFrame(timetable_data)
            st.write('### Generated Timetable')
            st.dataframe(timetable_df)
            
            pdf = create_pdf(timetable_df)
            pdf_output = pdf.output(dest='S').encode('latin1')
            st.download_button(label='Download Timetable as PDF', data=pdf_output, file_name='timetable.pdf', mime='application/pdf')
