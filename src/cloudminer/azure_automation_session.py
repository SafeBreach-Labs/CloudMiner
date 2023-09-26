import time
import requests
from http import HTTPStatus
from requests.exceptions import ReadTimeout, ChunkedEncodingError

from logger import LoggerIndent, logger
from cloudminer import CloudMinerException

URL_GET_STORAGE_BLOB = "https://s2.automation.ext.azure.com/api/Orchestrator/GenerateSasLinkUri?accountId=%s&assetType=Module"
AUTOMATION_ACCOUNT_URL = "https://management.azure.com%s/?api-version=2018-06-30"
UPLOAD_TIMEOUT = 300
SLEEP_BETWEEN_ERROR = 10
TIME_BETWEEN_REQUESTS = 0.5

class UPLOAD_STATE:
    """
    Package/Module upload state
    """
    FAILED = "Failed"
    CREATING = "Creating"
    SUCCEEDED = "Succeeded"
    CONTENT_VALIDATED = "ContentValidated"

class AzureAutomationSession:
    """
    Represents a session of Azure Automation
    """
    def __init__(self, account_id: str, access_token: str) -> None:
        """
        Initiate an Azure Automation session
        Validates that the Automation Account exists and the access token is valid

        :param account_id: Automation account ID - /subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/Microsoft.Automation/automationAccounts/{automationAccountName}
        :param access_token: Azure access token
        """
        self.account_id = account_id
        self.access_token = access_token
        self.next_request_time = 0
        try:
            self.http_request("GET", AUTOMATION_ACCOUNT_URL % self.account_id)
            logger.info("Access token is valid")
        except requests.HTTPError as e:
            if e.response.status_code == HTTPStatus.UNAUTHORIZED:
                raise CloudMinerException(f"Access token provided is not valid")
            elif e.response.status_code == HTTPStatus.BAD_REQUEST:
                raise CloudMinerException(f"ID provided is not valid")
            elif e.response.status_code == HTTPStatus.NOT_FOUND:
                raise CloudMinerException(f"Automation Account does not exists - '{account_id}'")
            else:
                raise

    def _wait_for_next_request(self):
        """
        Helper function to make sure we wait before each request
        """
        current_time = time.time()
        time_gap = self.next_request_time - current_time
        if time_gap > 0:
            time.sleep(time_gap)

        self.next_request_time = time.time() + TIME_BETWEEN_REQUESTS

    def http_request(self,
                http_method: str,
                url: str,
                headers: dict = {},
                authorization: bool = True,
                retries: int = 5,
                **kwargs) -> requests.Response:
        """
        Safe HTTP request to Azure services

        :param http_method:   HTTP method of the request
        :param url:           URL of the request
        :param headers:       Headers of the request
        :param authorization: If True, set the 'Authorization' header
        :param retries:       Retries count on a bad server response

        Return the response object
        """
        self._wait_for_next_request()
        if authorization:
            headers["Authorization"] = f"Bearer {self.access_token}"
        
        with LoggerIndent(logger):
            while retries:
                resp = None
                try:
                    resp = requests.request(http_method, url, headers=headers, timeout=5, **kwargs)
                except (ReadTimeout, ChunkedEncodingError):
                    pass
                
                if resp is None or resp.status_code in [HTTPStatus.TOO_MANY_REQUESTS, 
                                                        HTTPStatus.GATEWAY_TIMEOUT, 
                                                        HTTPStatus.SERVICE_UNAVAILABLE]:
                    
                    logger.warning(f"Too many requests. Retrying in {SLEEP_BETWEEN_ERROR} seconds...")
                    time.sleep(SLEEP_BETWEEN_ERROR)
                    retries -= 1
                else:
                    break

        resp.raise_for_status()
        return resp
    
    def upload_file_to_temp_storage(self, file_path: str) -> str:
        """
        Create a temp storage and upload a file
        Return the temp storage URI
        """
        # Create temporary blob storage for the module
        url = URL_GET_STORAGE_BLOB % self.account_id
        blog_storage_uri = self.http_request("GET", url).json()
        logger.debug("Temporary blob storage created successfully")

        # Upload the module to the storage
        with open(file_path, "rb") as file:
            self.http_request("PUT", blog_storage_uri, headers={"x-ms-blob-type": "BlockBlob"}, authorization=False, data=file.read())
        
        logger.debug("File uploaded to the storage")
        return blog_storage_uri

    def upload_powershell_module(self, module_name: str, blog_storage_uri: str):
        """
        Upload a Powershell module from a given blob storage
        """
        url = AUTOMATION_ACCOUNT_URL % f"{self.account_id}/modules/{module_name}"
        data = {
            "properties": {
                "contentLink": {
                    "uri": blog_storage_uri
                }
            }
        }
        self.http_request("PUT", url, json=data)
        logger.debug("Triggered module import flow in Automation Account")

    def upload_python_package(self, package_name: str, blog_storage_uri: str):
        """
        Upload a Python package from a given blob storage
        """
        url = AUTOMATION_ACCOUNT_URL % f"{self.account_id}/python3Packages/{package_name}"
        data = {
            "properties": {
                "contentLink": {
                    "uri": blog_storage_uri
                }
            }
        }
        self.http_request("PUT", url, json=data)
        logger.debug("Triggered package import flow in Automation Account")

    def get_python_package(self, package_name: str) -> dict:
        """
        Retrieve a Python package. Return None if does not exist
        """
        url = AUTOMATION_ACCOUNT_URL % f"{self.account_id}/python3Packages/{package_name}"
        try:
            package_data = self.http_request("GET", url).json()
        except requests.HTTPError as e:
            if e.response.status_code == HTTPStatus.NOT_FOUND:
                return None
            else:
                raise
            
        return package_data
    

            