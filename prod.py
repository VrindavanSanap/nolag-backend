from flask import Flask, request, jsonify, abort, send_file
import sqlite3
import base64
import io
import os
from functools import wraps
from datetime import datetime

app = Flask(__name__)

# Configuration
DATABASE = "screenshots.db"
SECRET_KEY = os.environ.get("API_SECRET_KEY", "default-dev-key")  # Better to use environment variables

# Authentication decorator
def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if api_key != SECRET_KEY:
            return jsonify({"error": "Unauthorized access"}), 401
        return f(*args, **kwargs)
    return decorated_function

# Database helper functions
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Returns rows as dictionaries
    return conn

def init_db():
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS screenshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                computer_name TEXT,
                system TEXT,
                processor TEXT,
                public_ip TEXT,
                image_file BLOB,
                location TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

# Initialize DB
init_db()
@app.route('/', methods=['GET'])
def info():
    return jsonify({
        "message": "Welcome to the Screenshot API",
        "endpoints": {
            "/upload": "POST - Upload a screenshot",
            "/data": "GET - Retrieve screenshot data with optional filters",
            "/stats": "GET - Retrieve statistics about screenshots"
        },
        "authentication": "Requires X-API-Key header with a valid API key"
    })

@app.route('/upload', methods=['POST'])
@require_api_key
def upload_screenshot():
    try:
        data = request.form
        computer_name = data.get("computer_name")
        system = data.get("system")
        processor = data.get("processor")
        public_ip = data.get("public_ip")
        image_file = request.files.get("image_file")
        location = data.get("location")
        
        # Validate required fields
        if not all([computer_name, system, processor, public_ip, image_file, location]):
            return jsonify({"error": "Missing required data"}), 400
        
        image_data = image_file.read()
        
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO screenshots (computer_name, system, processor, public_ip, image_file, location)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (computer_name, system, processor, public_ip, image_data, location))
            conn.commit()
            
        return jsonify({"message": "Screenshot data saved successfully", "id": c.lastrowid}), 201
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Improved data fetching with pagination and filtering
@app.route('/data', methods=['GET'])
@require_api_key
def get_data():
    try:
        # Get query parameters
        ids = request.args.getlist('id')
        last_n = request.args.get('last_n', type=int)
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        computer_name = request.args.get('computer_name')
        location = request.args.get('location')
        include_images = request.args.get('include_images', 'false').lower() == 'true'
        
        # Limit per_page to prevent excessive data transfer
        if per_page > 100:
            per_page = 100
        
        with get_db_connection() as conn:
            c = conn.cursor()
            
            # Build query dynamically
            query = "SELECT id, computer_name, system, processor, public_ip, location, timestamp"
            if include_images:
                query += ", image_file"
            query += " FROM screenshots"
            
            conditions = []
            params = []
            
            # Filter by IDs
            if ids:
                placeholders = ','.join('?' for _ in ids)
                conditions.append(f"id IN ({placeholders})")
                params.extend(ids)
            
            # Filter by date range
            if start_date:
                conditions.append("timestamp >= ?")
                params.append(start_date)
            if end_date:
                conditions.append("timestamp <= ?")
                params.append(end_date)
            
            # Filter by computer name
            if computer_name:
                conditions.append("computer_name LIKE ?")
                params.append(f"%{computer_name}%")
            
            # Filter by location
            if location:
                conditions.append("location LIKE ?")
                params.append(f"%{location}%")
            
            # Add WHERE clause if there are conditions
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            # Add ORDER BY and LIMIT
            query += " ORDER BY timestamp DESC"
            
            # Handle pagination or last_n
            if last_n is not None:
                query += " LIMIT ?"
                params.append(last_n)
            else:
                offset = (page - 1) * per_page
                query += " LIMIT ? OFFSET ?"
                params.extend([per_page, offset])
            
            c.execute(query, params)
            rows = c.fetchall()
            
            # Count total results for pagination metadata
            count_query = "SELECT COUNT(*) FROM screenshots"
            if conditions:
                count_query += " WHERE " + " AND ".join(conditions)
            c.execute(count_query, params[:-2] if last_n is None else params[:-1])
            total_count = c.fetchone()[0]
            
            # Prepare results
            results = []
            for row in rows:
                row_dict = dict(row)
                # Convert binary image data to base64 if included
                if include_images and row_dict.get('image_file'):
                    row_dict['image_file'] = base64.b64encode(row_dict['image_file']).decode()
                results.append(row_dict)
            
            # Prepare pagination metadata
            pagination = {
                "total": total_count,
                "page": page,
                "per_page": per_page,
                "pages": (total_count + per_page - 1) // per_page
            } if last_n is None else {"last_n": last_n}
            
            return jsonify({
                "data": results,
                "pagination": pagination
            })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Endpoint to retrieve a specific image directly
@app.route('/image/<int:screenshot_id>', methods=['GET'])
@require_api_key
def get_image(screenshot_id):
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT image_file FROM screenshots WHERE id = ?", (screenshot_id,))
            result = c.fetchone()
            
            if not result:
                return jsonify({"error": "Screenshot not found"}), 404
            
            image_data = result['image_file']
            return send_file(
                io.BytesIO(image_data),
                mimetype='image/png',  # Adjust based on your actual image type
                as_attachment=False
            )
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Endpoint for retrieving statistics
@app.route('/stats', methods=['GET'])
@require_api_key
def get_stats():
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            
            # Get total count
            c.execute("SELECT COUNT(*) FROM screenshots")
            total_count = c.fetchone()[0]
            
            # Get count by location
            c.execute("SELECT location, COUNT(*) as count FROM screenshots GROUP BY location ORDER BY count DESC")
            locations = [dict(row) for row in c.fetchall()]
            
            # Get count by computer
            c.execute("SELECT computer_name, COUNT(*) as count FROM screenshots GROUP BY computer_name ORDER BY count DESC")
            computers = [dict(row) for row in c.fetchall()]
            
            # Get latest entries
            c.execute("SELECT id, computer_name, location, timestamp FROM screenshots ORDER BY timestamp DESC LIMIT 5")
            latest = [dict(row) for row in c.fetchall()]
            
            return jsonify({
                "total_screenshots": total_count,
                "by_location": locations,
                "by_computer": computers,
                "latest_entries": latest
            })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5001, debug=True)