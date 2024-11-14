from flask import Flask, render_template, request, flash
import os
import pandas as pd
from sqlalchemy import create_engine
from werkzeug.utils import secure_filename
from datetime import datetime
from sqlalchemy import text

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # Set your secret key for flash messages
app.config['UPLOAD_FOLDER'] = 'uploads'  # Define your upload folder

# Ensure the upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Replace the following with your actual database connection string
DATABASE_URI = 'mysql+pymysql://root:@localhost/excel_python'
engine = create_engine(DATABASE_URI)

# Allowed file extensions for Excel files
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}

def allowed_file(filename):
    """Check if the uploaded file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def table_exists(table_name):
    """Check if the specified table exists in the database."""
    query = f"SHOW TABLES LIKE '{table_name}'"
    result = pd.read_sql(query, con=engine)
    return not result.empty

def get_data_from_table(table_name, page, per_page, search_query=None):
    """Fetch data from the table for display with pagination and search using SOUNDEX."""
    results = []
    offset = (page - 1) * per_page

    if search_query:
        # Using SOUNDEX for phonetic matching
        soundex_query = f"SELECT * FROM {table_name} WHERE SOUNDEX(Patient_Name) = SOUNDEX(%s)"
        df_soundex = pd.read_sql(soundex_query, con=engine, params=(search_query,))

        if not df_soundex.empty:
            print(f"Found {len(df_soundex)} phonetic matches for '{search_query}'.")
            return df_soundex.to_dict(orient='records')

        print(f"No phonetic matches found for '{search_query}'.")
        # Fallback to LIKE query if no matches found
        query = f"SELECT * FROM {table_name} WHERE Patient_Name LIKE %s LIMIT %s OFFSET %s"
        params = (f'%{search_query}%', per_page, offset)
    else:
        # Default query without search
        query = f"SELECT * FROM {table_name} LIMIT %s OFFSET %s"
        params = (per_page, offset)

    print(f"Executing query: {query} with params: {params}")
    results = pd.read_sql(query, con=engine, params=params)

    return results.to_dict(orient='records')

def create_table_from_excel(df, table_name):
    """Dynamically create a table based on the dataframe's columns and insert data."""
    columns = [f"`{col.replace(' ', '_')}` VARCHAR(255)" for col in df.columns]

    create_table_query = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(columns)})"
    
    # Execute the query using text()
    with engine.connect() as conn:
        conn.execute(text(create_table_query))  # Using text() to execute the SQL command

    # Insert data into the created table
    df.to_sql(table_name, con=engine, index=False, if_exists='append')

@app.route('/', methods=['GET', 'POST'])
def index():
    table_name = f'patients_data_{datetime.now().strftime("%Y_%m_%d")}'
    page = request.args.get('page', 1, type=int)
    per_page = 5  # Number of records per page
    search_query = request.args.get('search', '')
    filtered_users = None  # Initialize to None

    if table_exists(table_name):
        filtered_users = get_data_from_table(table_name, page, per_page, search_query)

    if request.method == 'POST':
        file = request.files.get('file')
        if not file or not allowed_file(file.filename):
            flash('Invalid file type. Please upload an Excel file.')
        else:
            try:
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)

                df = pd.read_excel(filepath)

                if not table_exists(table_name):
                    create_table_from_excel(df, table_name)
                    flash('File uploaded and data inserted successfully.')
                else:
                    flash('Table already exists. Data will not be inserted.')

                filtered_users = get_data_from_table(table_name, page, per_page)

            except Exception as e:
                flash(f'An error occurred: {str(e)}')

    return render_template('index.html', filtered_users=filtered_users, table_name=table_name, page=page, search_query=search_query)

if __name__ == '__main__':
    app.run(debug=True)
