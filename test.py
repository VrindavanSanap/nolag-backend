import requests
url = "http://52.66.174.153:5001/upload"
data = {
    "computer_name": "MyPC",
    "system": "Windows 10",
    "processor": "Intel Core i7",
    "public_ip": "192.168.1.1",
    "location": "New York, USA"
}

file_path = "screenshot.png"  # Path to the image file
files = {"image_file": open(file_path, "rb")}

response = requests.post(url, data=data, files=files)

print(response.status_code)
print(response.json())
