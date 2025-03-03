from flask import Flask, request, jsonify
import sqlite3

app = Flask(__name__)

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
    if not ids:
        return jsonify({"error": "No IDs provided"}), 400

    # Use parameterized query to prevent SQL injection and improve readability
    placeholders = ','.join('?' for _ in ids)
    query = f"SELECT * FROM screenshots WHERE id IN ({placeholders})"

    conn = sqlite3.connect("screenshots.db")
    c = conn.cursor()
    c.execute(query, ids)
    data = c.fetchall()

    # Convert the fetched data into a list of dictionaries for better JSON serialization
    column_names = [column[0] for column in c.description]
    result = [
        {column: (value.decode('utf-8', 'replace') if isinstance(value, bytes) else value) for column, value in zip(column_names, row)}
        for row in data
    ]

    conn.close()
    return jsonify({"data": result})
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5001, debug=True)