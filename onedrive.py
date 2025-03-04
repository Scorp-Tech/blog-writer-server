import msal
import requests
import json
from werkzeug.utils import secure_filename

CLIENT_ID = "f2a0cca4-a73a-497c-aee3-d15256e5c8d3"  # Replace with your app's Client ID
AUTHORITY = "https://login.microsoftonline.com/consumers"  # For personal accounts
SCOPES = ["Files.ReadWrite", "User.Read"]
SERVER = "http://127.0.0.1:5000"

# Microsoft Graph API base URL
GRAPH_API_ENDPOINT = "https://graph.microsoft.com/v1.0/me/drive"


def get_valid_access_token():
    refresh_token = 'M.C511_SN1.0.U.-Cpj0vIgI*edNN*!KS*ILm*4cbfeKl0gmT3!miMrUKZBKi0W5xTn0PomTV!YDuMQpZtpZ!lFK7GXZl2XL8fGlNSaIhICekdmPvQjlIzYJ5Vb6c4IHGZRYa3V*WgvwgOMfO5Gam1jCrxWfkdMJsHz5fhkbVmyY6*aWbaeWgdIAOx5Z7yQHQYJjG8pqqNC4FrCjmUkmTbq0kV5O1tZ9D9dov4T6OZbo2MqGB4L*hL!EjEpVHGZ!AWNOzhAXMcY*TukN9mWaIT8T6z!jJxrRTOrsGUyd7E7HNRV1IqrXXGWC5Tj1lT7zqAfx8HUnohf9CL*FjULwaExzQ8BVXWWhbwROC2yNDWAJCEp!e7DCZ6HzehOi'
    # Check if the token is expired and refresh if necessary
    app = msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY)
    result = app.acquire_token_by_refresh_token(refresh_token, scopes=SCOPES)
    if "access_token" in result:
        return result["access_token"]
    else:
        raise Exception(f"Could not refresh access token: {result.get('error_description')}")

def list_files():
    token = get_valid_access_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(f"{GRAPH_API_ENDPOINT}/root/children", headers=headers)
    
    if response.status_code == 200:
        files = response.json().get("value", [])
        return files
    else:
        print(f"Error: {response.text}")
        return None

def upload_file(binary_data, onedrive_path, file_name):
    # Secure the file name to avoid potential issues with special characters
    file_name = secure_filename(file_name)
    
    token = get_valid_access_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/octet-stream"
    }
    upload_url = f"{GRAPH_API_ENDPOINT}/root:/{onedrive_path}/{file_name}:/content"
    response = requests.put(
        upload_url,
        headers=headers,
        data=binary_data
    )

    if response.status_code in [200, 201]:
        headers['Content-Type'] = "application/json"
        res = requests.post(f"{GRAPH_API_ENDPOINT}/items/{response.json()['id']}/createLink", headers=headers, data=json.dumps({
            "type": "embed",
            "scope": "anonymous",
        })).json()
        return({
            "onedriveUrl" : res['link']['webUrl'],
            "url": f"{SERVER}/{onedrive_path}/{file_name}",
        })
    else:
        print(f"Upload failed: {response.text}")
        return None

def download_file(onedrive_path):
    token = get_valid_access_token()
    headers = {
        "Authorization": f"Bearer {token}",
    }
    
    # Construct URL using the OneDrive path.
    # The API endpoint uses the format: /root:/path/to/file:/content
    url = f"{GRAPH_API_ENDPOINT}/root:/{onedrive_path}:/content"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.content
    else:
        raise Exception(f"Download failed: {response.text}")

def delete_file(file_name):
    token = get_valid_access_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get the file ID
    files = list_files()
    file_id = None
    for file in files:
        if file["name"] == file_name:
            file_id = file["id"]
            break
    
    if file_id:
        response = requests.delete(f"{GRAPH_API_ENDPOINT}/items/{file_id}", headers=headers)
        if response.status_code == 204:
            print("File deleted successfully!")
        else:
            print(f"Delete failed: {response.text}")
    else:
        print("File not found.")


# while True:
#     command = input("> ")
#     if(command == "list"):
#         print(list_files())
#     elif("upload" in command):
#         t = command.split()
#         localPath = t[1]
#         onedrivePath = t[2]
#         print(upload_file(localPath, onedrivePath))
#     elif("download" in command):
#         t = command.split()
#         print(download_file(t[0], save_path="/"))
#     elif("delete" in command):
#         t = command.split()
#         print(delete_file())