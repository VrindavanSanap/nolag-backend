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
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()  # Ensure DB is set up

@app.route('/upload', methods=['POST'])
def upload_screenshot():
    data = request.json

    computer_name = data.get("computer_name")
    system = data.get("system")
    processor = data.get("processor")
    public_ip = data.get("public_ip")

    if not all([computer_name, system, processor, public_ip]):
        return jsonify({"error": "Missing data"}), 400

    conn = sqlite3.connect("screenshots.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO screenshots (computer_name, system, processor, public_ip)
        VALUES (?, ?, ?, ?)
    """, (computer_name, system, processor, public_ip))
    conn.commit()
    conn.close()

    return jsonify({"message": "Screenshot data saved successfully"}), 201

@app.route('/data', methods=['GET'])
def get_data():
    conn = sqlite3.connect("screenshots.db")
    c = conn.cursor()
    c.execute("SELECT * FROM screenshots")
    data = c.fetchall()
    conn.close()
    
    return jsonify({"data": data})

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5001, debug=True)

