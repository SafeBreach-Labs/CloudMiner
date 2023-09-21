import time
import requests
from http import HTTPStatus

URL_GET_STORAGE_BLOB = "https://s2.automation.ext.azure.com/api/Orchestrator/GenerateSasLinkUri?accountId=%s&assetType=Module"
AUTOMATION_ACCOUNT_URL = "https://management.azure.com%s/?api-version=2018-06-30"
UPLOAD_TIMEOUT = 300

class UPLOAD_STATE:
    FAILED = "Failed"
    CREATING = "Creating"
    SUCCEEDED = "Succeeded"
    CONTENT_VALIDATED = "ContentValidated"


class AzureAutomationSession:
    """
    Represents a session for Azure
    """
    def __init__(self, account_id: str, access_token: str) -> None:
        self.account_id = account_id
        self.access_token = access_token
        
        try:
            self.azure_request("GET", AUTOMATION_ACCOUNT_URL % self.account_id)
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                raise Exception(f"Automation Account does not exists - '{account_id}'")

    def azure_request(self,
                      http_method: str,
                      url: str,
                      headers: dict = {},
                      auth_info: bool = True,
                      retries: int = 5,
                      **kwargs) -> requests.Response:

        if auth_info:
            headers["Authorization"] = f"Bearer {self.access_token}"
        
        while retries:
            resp = None
            try:
                resp = requests.request(http_method, url, headers=headers, timeout=5, **kwargs)
            except requests.exceptions.ReadTimeout:
                pass
            
            if not resp or resp.status_code in [HTTPStatus.TOO_MANY_REQUESTS, HTTPStatus.GATEWAY_TIMEOUT]:
                print("\t\t[-] Too many requests. Retrying...")
                time.sleep(10)
                retries -= 1
            else:
                break
        
        resp.raise_for_status()
        return resp
    
    def upload_file_to_temp_storage(self, file_path: str):
        # Create temporary blob storage for the module
        url = URL_GET_STORAGE_BLOB % self.account_id
        storage_blob_uri = self.azure_request("GET", url).json()
        print("\t[+] Temporary blob storage created successfully")

        # Upload the module to the storage
        with open(file_path, "rb") as file:
            self.azure_request("PUT", storage_blob_uri, headers={"x-ms-blob-type": "BlockBlob"}, auth_info=False, data=file.read())
        
        print("\t[+] File uploaded to the storage")
        return storage_blob_uri

    def upload_powershell_module(self, module_name: str, storage_blob_uri: str):
        url = AUTOMATION_ACCOUNT_URL % f"{self.account_id}/modules/{module_name}"
        data = {
            "properties": {
                "contentLink": {
                    "uri": storage_blob_uri
                }
            }
        }
        self.azure_request("PUT", url, json=data)
        print("\t[+] Triggered module import flow in Automation Account")

    def upload_python_package(self, package_name: str, storage_blob_uri: str):
        
        url = AUTOMATION_ACCOUNT_URL % f"{self.account_id}/python3Packages/{package_name}"
        data = {
            "properties": {
                "contentLink": {
                    "uri": storage_blob_uri
                }
            }
        }
        self.azure_request("PUT", url, json=data)
        print("\t[+] Triggered package import flow in Automation Account")

    def get_python_package(self, package_name: str):
        url = AUTOMATION_ACCOUNT_URL % f"{self.account_id}/python3Packages/{package_name}"
        package_data = self.azure_request("GET", url).json()
        return package_data
    

            