import requests
import time

IP = "192.168.0.1"
URL = "http://localhost:5001"  # ou o IP/porta do container exposto

for i in range(10):
    print(f"Attempt {i+1}")
    
    # Registra tentativa com falha
    r1 = requests.post(f"{URL}/register_attempt", json={"ip": IP, "success": False})
    
    # Avalia ação do sistema
    r2 = requests.post(f"{URL}/evaluate", json={"ip": IP})
    print("Response:", r2.json())

    time.sleep(1)
