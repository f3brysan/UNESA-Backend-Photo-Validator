import base64
import requests
import json

# Create a dummy 1x1 png image
dummy_png = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
b64 = base64.b64encode(dummy_png).decode('utf-8')

try:
    res = requests.post("http://localhost:5000/api/v1/validasi_foto", json={"foto": b64, "gender": "L"})
    print("Status code:", res.status_code)
    print("Response:", res.json())
except Exception as e:
    print("Error connecting to server:", e)
