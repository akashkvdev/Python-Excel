from flask import Flask, request, render_template, redirect, url_for, flash
import pandas as pd
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)
app.secret_key = 'abcd12345'  # Required for flashing messages

# MySQL database configuration
db_config = {
    'host': '192.168.50.250',  # Change as needed
    'user': 'Akash',            # Your MySQL username
    'password': 'Akash@123',    # Your MySQL password
    'database': 'cms'           # Your MySQL database name
}

def check_database_connection():
    try:
        connection = mysql.connector.connect(**db_config)
        if connection.is_connected():
            connection.close()  # Close the connection
            return True
    except Error as e:
        print(f"Error while connecting to MySQL: {e}")
        return False

def get_patients_data():
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)
        
        # Query to select all patients
        cursor.execute("SELECT * FROM patients")
        patients = cursor.fetchall()
        
        # print(f"Retrieved patients data: {patients}")  # Debugging line
        
        cursor.close()
        connection.close()
        return patients
    
    except Error as e:
        print(f"Error while connecting to MySQL: {e}")
        return None  # Return None if there's an error

@app.route('/')
def index():
    # Check database connection status
    if not check_database_connection():
        flash('Could not connect to the database.', 'error')
        return render_template('index.html', filtered_users=[])

    # Get all patients data from the database
    patients = get_patients_data()
    
    if patients is None:
        flash('Could not retrieve patients data from the database.', 'error')
        return render_template('index.html', filtered_users=[])

    # Pagination logic
    page = request.args.get('page', 1, type=int)  # Get page number from query parameters
    per_page = 10  # Number of records per page
    total = len(patients)  # Total number of patients
    start = (page - 1) * per_page
    end = start + per_page
    paginated_patients = patients[start:end]  # Get the current page's patients

    # Calculate total pages
    total_pages = (total + per_page - 1) // per_page

    return render_template('index.html', filtered_users=paginated_patients, page=page, total_pages=total_pages)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file part in the request.', 'error')
        return redirect(request.url)

    file = request.files['file']
    if file.filename == '':
        flash('No file selected.', 'error')
        return redirect(request.url)

    try:
        # Read the Excel file
        df = pd.read_excel(file)

        # Clean and get unique names from the first column
        user_names = df.iloc[:, 0].str.strip().unique()  # Get unique names and strip whitespace

        # print(f"User names from Excel: {user_names}")  # Debugging line

        # Get all patients data from the database
        patients = get_patients_data()

        if patients is None:
            flash('Could not retrieve patients data from the database.', 'error')
            return redirect(request.url)

        # Filter patients based on names
        filtered_patients = [p for p in patients if p['name'].strip() in user_names]  # Strip whitespace

        # print(f"Filtered patients: {filtered_patients}")  # Debugging line

        # Store filtered patients in the session for pagination
        total = len(filtered_patients)  # Total number of filtered patients
        per_page = 10  # Number of records per page
        page = request.args.get('page', 1, type=int)  # Get page number from query parameters
        start = (page - 1) * per_page
        end = start + per_page
        paginated_patients = filtered_patients[start:end]  # Get the current page's filtered patients

        # Calculate total pages for filtered results
        total_pages = (total + per_page - 1) // per_page

        return render_template('index.html', filtered_users=paginated_patients, page=page, total_pages=total_pages)

    except Exception as e:
        print(f"Error while processing the uploaded file: {e}")
        flash('An error occurred while processing the uploaded file. Please ensure it is a valid Excel file.', 'error')
        return redirect(request.url)

if __name__ == '__main__':
    app.run(debug=True)
