from flask import Flask, render_template, request, flash
import os
import pandas as pd
from werkzeug.utils import secure_filename
from sqlalchemy import create_engine, MetaData, Table, Column, String
import sqlalchemy
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'adasdfjashf132'
app.config['UPLOAD_FOLDER'] = 'uploads'

# MySQL Database connection
DATABASE_URL = "mysql+pymysql://server:@localhost:3306/excel_python"
engine = create_engine(DATABASE_URL)
metadata = MetaData()

# Allowed file extensions for Excel files
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def create_table_from_excel(df, table_name):
    """Dynamically create a table based on the dataframe's columns and insert data."""
    columns = []
    for col in df.columns:
        columns.append(Column(col.replace(" ", "_"), String(255)))  # Replace spaces with underscores

    # Create a new table if it doesn't exist
    table = Table(table_name, metadata, *columns, extend_existing=True)
    metadata.create_all(engine)

    # Insert the data from the dataframe into the table
    df.to_sql(table_name, con=engine, index=False, if_exists='append')

def table_exists(table_name):
    """Check if a table already exists in the database."""
    inspector = sqlalchemy.inspect(engine)
    return table_name in inspector.get_table_names()

def get_data_from_table(table_name, page, per_page, search_query=None):
    """Fetch data from the table for display with pagination and search."""
    query = f"SELECT * FROM {table_name}"
    if search_query:
        query += f" WHERE Patient_Name LIKE '%{search_query}%'"
    query += f" LIMIT {per_page} OFFSET {(page - 1) * per_page}"
    
    df = pd.read_sql(query, con=engine)
    return df

@app.route('/', methods=['GET', 'POST'])
def index():
    filtered_users = None  # Initialize to None
    table_name = None  # Variable to store the table name

    # Generate the table name using the current date
    current_date = datetime.now().strftime('%Y_%m_%d')
    table_name = f'patients_data_{current_date}'

    # Set pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = 5  # Number of records per page
    search_query = request.args.get('search', '')

    # Check if the table already exists and fetch data if it does
    if table_exists(table_name):
        filtered_users = get_data_from_table(table_name, page, per_page, search_query).to_dict(orient='records')

    if request.method == 'POST':
        # Handle file upload
        file = request.files.get('file')
        if not file or not allowed_file(file.filename):
            flash('Invalid file type. Please upload an Excel file.')
        else:
            try:
                # Save the file
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)

                # Read the Excel file into a pandas DataFrame
                df = pd.read_excel(filepath)

                # Check if the table already exists
                if not table_exists(table_name):
                    # Create the table and insert data
                    create_table_from_excel(df, table_name)
                    flash('File uploaded and data inserted successfully.')
                else:
                    flash('Table already exists. Data will not be inserted.')

                # Fetch the data to display
                filtered_users = get_data_from_table(table_name, page, per_page).to_dict(orient='records')

            except Exception as e:
                flash(f'An error occurred: {str(e)}')

    return render_template('index.html', filtered_users=filtered_users, table_name=table_name, page=page, search_query=search_query)



if __name__ == '__main__':
    app.run(debug=True)
