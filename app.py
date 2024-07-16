import streamlit as st
import pandas as pd
import requests
from fpdf import FPDF
from datetime import datetime, timedelta

# PocketBase API URL
POCKETBASE_URL = 'https://mucollegdb.pockethost.io'
POCKETBASE_API_TOKEN = 'YOUR_ACCESS_TOKEN'  # Replace with your actual API token

HEADERS = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {POCKETBASE_API_TOKEN}'
}

# Function to fetch all courses from PocketBase
def fetch_courses():
    response = requests.get(f'{POCKETBASE_URL}/api/collections/courses/records?perPage=1080', headers=HEADERS)
    if response.status_code == 200:
        return response.json()['items']
    return []

# Function to fetch subjects for a given course from PocketBase
def fetch_subjects(course_id):
    response = requests.get(f'{POCKETBASE_URL}/api/collections/subjects/records', headers=HEADERS, params={'filter': f'subject_of="{course_id}"'})
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

# Function to save timetable to PocketBase
def save_timetable_to_pocketbase(start_date, end_date, selected_course_id):
    timetable_data = {
        "course_exam_start_date": start_date.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
        "course_exam_end_date": end_date.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
        "exam_of": selected_course_id,
        

    }

    response = requests.post(f'{POCKETBASE_URL}/api/collections/exams/records', headers=HEADERS, json=timetable_data)
    return response.status_code == 200, response.json()

# Streamlit app layout
def main():
    st.title('Timetable Generator')

    # Step 1: Select Course
    courses = fetch_courses()
    course_names = [course['course_name'] for course in courses]

    selected_course_name = st.selectbox('Select Course', course_names, index=0)

    if selected_course_name:
        selected_course = next(course for course in courses if course['course_name'] == selected_course_name)
        
        # Step 2: Select Start Date and End Date
        st.write("Select the timetable duration:")
        start_date = st.date_input('Start Date', value=datetime.today())
        end_date = st.date_input('End Date', value=datetime.today() + timedelta(days=30))

        if start_date and end_date:
            # Function to filter out Sundays
            def is_not_sunday(date):
                return date.weekday() != 6

            # Generate a list of dates excluding Sundays
            all_dates = pd.date_range(start=start_date, end=end_date)
            available_dates = [(date, date.strftime('%A')) for date in all_dates if is_not_sunday(date)]

            # Allow users to select holidays
            st.write("Select holidays to exclude:")
            holiday_dates = st.multiselect('Select Holidays', available_dates, format_func=lambda x: x[0].strftime('%Y-%m-%d'))

            # Exclude selected holidays
            valid_dates = [(date, day) for date, day in available_dates if date not in [holiday[0] for holiday in holiday_dates]]

            # Step 3: Select Subjects
            st.write(f"Select subjects for {selected_course_name}:")
            subjects = fetch_subjects(selected_course['id'])
            selected_subjects = {}
            for subject in subjects:
                if st.checkbox(subject['subject_name']):
                    selected_subjects[subject['subject_name']] = subject

            if selected_subjects:
                # Step 4: Set Dates and Time Slot for Selected Subjects
                dates_with_days = [f"{date.strftime('%Y-%m-%d')} ({day})" for date, day in valid_dates]
                timetable_data = []
                for subject_name, subject in selected_subjects.items():
                    with st.expander(f'{subject_name}'):
                        selected_dates = st.multiselect(f'Select Dates for {subject_name}', dates_with_days)
                        selected_date_objs = [date for date, day in valid_dates if f"{date.strftime('%Y-%m-%d')} ({day})" in selected_dates]
                        start_time = st.text_input(f'Start time for {subject_name} (e.g., 9:00 AM)', value='9:00 AM')
                        end_time = st.text_input(f'End time for {subject_name} (e.g., 12:00 PM)', value='12:00 PM')

                        for date in selected_date_objs:
                            timetable_data.append({'Date': date.strftime('%d/%m/%Y'), 'Subject': subject_name, 'Time': f'{start_time} to {end_time}'})

                if st.button('Generate Timetable'):
                    timetable_df = pd.DataFrame(timetable_data)
                    st.write('### Generated Timetable')
                    st.dataframe(timetable_df)
                    
                    pdf = create_pdf(timetable_df)
                    pdf_output = pdf.output(dest='S').encode('latin1')
                    st.download_button(label='Download Timetable as PDF', data=pdf_output, file_name='timetable.pdf', mime='application/pdf')
                    
                    # Save timetable to PocketBase
                    success, response = save_timetable_to_pocketbase(start_date, end_date, selected_course['id'])
                    if success:
                        st.success("Timetable successfully saved to PocketBase.")
                    else:
                        st.error(f"Failed to save timetable to PocketBase: {response}")

if __name__ == "__main__":
    main()
