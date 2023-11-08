import os
import time
import requests
import posixpath
import urllib.parse
from enum import Enum
from http import HTTPStatus
from datetime import datetime
from datetime import timedelta
from requests.exceptions import ReadTimeout, ChunkedEncodingError

from cloudminer.logger import logger
from cloudminer.exceptions import CloudMinerException

URL_GET_STORAGE_BLOB = "https://s2.automation.ext.azure.com/api/Orchestrator/GenerateSasLinkUri?accountId={account_id}&assetType=Module"
AZURE_MANAGEMENT_URL = "https://management.azure.com"
DEFAULT_API_VERSION = "2018-06-30"
UPLOAD_TIMEOUT = 300
SLEEP_BETWEEN_ERROR_SECONDS = 10
TIME_BETWEEN_REQUESTS_SECONDS = 0.5
TEMP_STORAGE_VALID_SAFETY_SECONDS = 60
HTTP_REQUEST_TIMEOUT = 5

class UPLOAD_STATE(str, Enum):
    """
    Package/Module upload state
    """
    FAILED = "Failed"
    CREATING = "Creating"
    SUCCEEDED = "Succeeded"
    CONTENT_VALIDATED = "ContentValidated"
    CONTENT_DOWNLOADED = "ContentDownloaded"
    CONNECTION_TYPE_IMPORTED = "ConnectionTypeImported"
    RUNNING_IMPORT_MODULE_RUNBOOK = "RunningImportModuleRunbook"

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

        :raises CloudMinerException: If access token proivided is not valid
                                     If Automation Account ID is not valid
                                     If Automation Account provided does not exist
        """
        self.__account_id = account_id
        self.__access_token = access_token
        self.__next_request_time = 0
        try:
            self.__http_request("GET", self.__get_url())
            logger.info("Access token is valid")
        except requests.HTTPError as e:
            if e.response.status_code == HTTPStatus.UNAUTHORIZED:
                raise CloudMinerException("Access token provided is not valid") from e
            if e.response.status_code == HTTPStatus.BAD_REQUEST:
                raise CloudMinerException(f"Automation Account ID provided is not valid - '{account_id}'") from e
            if e.response.status_code == HTTPStatus.NOT_FOUND:
                raise CloudMinerException(f"Automation Account does not exists - '{account_id}'") from e
            raise

    def __get_url(self, path: str = "") -> str:
        """
        Construct a url for the given path in the Automation Account
        """
        return posixpath.join(AZURE_MANAGEMENT_URL,
                              self.__account_id[1:],
                              path) + f"?api-version={DEFAULT_API_VERSION}"

    def __wait_for_next_request(self):
        """
        Helper function to make sure we wait before each request
        """
        current_time = time.time()
        time_gap = self.__next_request_time - current_time
        if time_gap > 0:
            time.sleep(time_gap)

        self.__next_request_time = time.time() + TIME_BETWEEN_REQUESTS_SECONDS

    def __http_request(self,
                     http_method: str,
                     url: str,
                     headers: dict = None,
                     add_auth_info: bool = True,
                     retries: int = 5,
                     timeout: int = HTTP_REQUEST_TIMEOUT,
                     **kwargs) -> requests.Response:
        """
        Safe HTTP request to Azure services

        :param http_method:   HTTP method of the request
        :param url:           URL of the request
        :param headers:       Headers of the request
        :param authorization: If True, set the 'Authorization' header
        :param retries:       Retries count on a bad server response
        :return:              Response object

        :raises HTTPError: If bad response is received
        """
        self.__wait_for_next_request()

        if headers is None:
            headers = {}
            
        if add_auth_info:
            headers["Authorization"] = f"Bearer {self.__access_token}"
        
        for _ in range(retries):
            resp = None
            try:
                resp = requests.request(http_method, url, headers=headers, timeout=timeout, **kwargs)
            except (ReadTimeout, ChunkedEncodingError, ConnectionError): # Bad response from server
                pass
            
            if resp is None or resp.status_code in [HTTPStatus.TOO_MANY_REQUESTS,
                                                    HTTPStatus.GATEWAY_TIMEOUT,
                                                    HTTPStatus.SERVICE_UNAVAILABLE]:
                
                logger.warning(f"Too many requests. Retrying in {SLEEP_BETWEEN_ERROR_SECONDS} seconds...")
                time.sleep(SLEEP_BETWEEN_ERROR_SECONDS)
            else:
                resp.raise_for_status()
                return resp
        else:
            raise CloudMinerException(f"Failed to send HTTP request - Reached maximum retries. "\
                                      f"Method - '{http_method}', url - '{url}'")

    def __upload_file_to_temp_storage(self, file_path: str) -> str:
        """
        Create a temp storage and upload a file

        :param file_path: File path to upload
        :return: Temp storage url
        """
        url = URL_GET_STORAGE_BLOB.format(account_id=self.__account_id)
        self.__current_temp_storage_url = self.__http_request("GET", url).json()
        logger.debug("Temporary blob storage created successfully")

        with open(file_path, "rb") as f:
            file_data = f.read()
            
        self.__http_request("PUT",
                            self.__current_temp_storage_url,
                            headers={"x-ms-blob-type": "BlockBlob"},
                            add_auth_info=False,
                            data=file_data)
        
        file_name = os.path.basename(file_path)
        logger.debug(f"File '{file_name}' uploaded to temporary storage")
        return self.__current_temp_storage_url

    def upload_powershell_module(self, module_name: str, zipped_ps_module: str):
        """
        Upload a Powershell module to the Automation Account
        """
        logger.info(f"Uploading Powershell module '{module_name}'")
        
        temp_storage_url = self.__upload_file_to_temp_storage(zipped_ps_module)
        url = self.__get_url(f"modules/{module_name}")
        request_data = {
            "properties": {
                "contentLink": {
                    "uri": temp_storage_url
                }
            }
        }
        self.__http_request("PUT", url, json=request_data)

    def upload_python_package(self, package_name: str, whl_path: str):
        """
        Upload a Python package from a given blob storage
        """
        logger.info(f"Uploading Python package - '{package_name}':")
        
        temp_storage_url = self.__upload_file_to_temp_storage(whl_path)
        url = self.__get_url(f"python3Packages/{package_name}")
        request_data = {
            "properties": {
                "contentLink": {
                    "uri": temp_storage_url
                }
            }
        }
        self.__http_request("PUT", url, json=request_data)
        logger.info(f"Triggered package import flow in Automation Account.")

    def get_python_package(self, package_name: str) -> dict:
        """
        Retrieve a Python package. Return None if does not exist
        """
        url = self.__get_url(f"python3Packages/{package_name}")
        try:
            package_data = self.__http_request("GET", url).json()
        except requests.HTTPError as e:
            if e.response.status_code == HTTPStatus.NOT_FOUND:
                return None
            else:
                raise
            
        return package_data
    
    def delete_python_package(self, package_name: str):
        """
        Delete a Python package
        
        :raises CloudMinerException: If the given package does not exists
        """
        url = self.__get_url(f"python3Packages/{package_name}")
        try:
            self.__http_request("DELETE", url)
        except requests.HTTPError as e:
            if e.response.status_code == HTTPStatus.NOT_FOUND:
                raise CloudMinerException(f"Failed to delete package {package_name}. Package does not exist")
            else:
                raise