from flask import Flask, request, jsonify, send_file
from flask_cors import CORS  # Import CORS
import sqlite3
import io  # Needed to handle binary image data

app = Flask(__name__)
CORS(app)  # Enable CORS

# Initialize the database
def init_db():
    conn = sqlite3.connect("screenshots.db")
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
    conn.close()

init_db()  # Ensure DB is set up

@app.route('/upload', methods=['POST'])
def upload_screenshot():
    data = request.form

    computer_name = data.get("computer_name")
    system = data.get("system")
    processor = data.get("processor")
    public_ip = data.get("public_ip")
    image_file = request.files.get("image_file")
    location = data.get("location")

    if not all([computer_name, system, processor, public_ip, image_file, location]):
        return jsonify({"error": "Missing data"}), 400

    image_data = image_file.read()

    conn = sqlite3.connect("screenshots.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO screenshots (computer_name, system, processor, public_ip, image_file, location)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (computer_name, system, processor, public_ip, image_data, location))
    conn.commit()
    conn.close()

    return jsonify({"message": "Screenshot data saved successfully"}), 201

@app.route('/data', methods=['GET'])
def get_data():
    ids = request.args.getlist('id')
    last_n = request.args.get('last_n', type=int)
    id_range_start = request.args.get('range_start', type=int)
    id_range_end = request.args.get('range_end', type=int)

    conn = sqlite3.connect("screenshots.db")
    c = conn.cursor()

    if ids:
        placeholders = ','.join('?' for _ in ids)
        query = f"SELECT id, computer_name, system, processor, public_ip, location, timestamp FROM screenshots WHERE id IN ({placeholders})"
        c.execute(query, ids)
    elif last_n is not None:
        query = "SELECT id, computer_name, system, processor, public_ip, location, timestamp FROM screenshots ORDER BY timestamp DESC LIMIT ?"
        c.execute(query, (last_n,))
    elif id_range_start is not None and id_range_end is not None:
        query = "SELECT id, computer_name, system, processor, public_ip, location, timestamp FROM screenshots WHERE id BETWEEN ? AND ?"
        c.execute(query, (id_range_start, id_range_end))
    else:
        return jsonify({"error": "No IDs, last_n, or range parameters provided"}), 400

    data = c.fetchall()
    column_names = [column[0] for column in c.description]

    result = [
        {
            column: value for column, value in zip(column_names, row)
        } for row in data
    ]

    # Add image URL dynamically
    for entry in result:
        entry["image_url"] = f"/image/{entry['id']}"

    conn.close()
    return jsonify({"data": result})

@app.route('/image/<int:image_id>')
def get_image(image_id):
    conn = sqlite3.connect("screenshots.db")
    c = conn.cursor()
    c.execute("SELECT image_file FROM screenshots WHERE id = ?", (image_id,))
    row = c.fetchone()
    conn.close()

    if row and row[0]:
        image_data = io.BytesIO(row[0])  # Convert BLOB to file-like object
        return send_file(image_data, mimetype='image/png')  # Adjust MIME type if needed

    return jsonify({"error": "Image not found"}), 404

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5001, debug=True)
