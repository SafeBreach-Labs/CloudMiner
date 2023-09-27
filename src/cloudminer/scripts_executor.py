import os
import time
import uuid
import shutil
from abc import ABC, abstractmethod

import file_utils
from logger import LoggerIndent, logger
from cloudminer import CloudMinerException
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
        """
        Executes Powershell script within Azure Automation
        """
        logger.info(f"Attempting to execute the Powershell script {count} times:")
        for index in range(count):
            logger.info(f"Triggering Powershell execution - {index+1}/{count}:")
            with LoggerIndent(logger):
                module_name = str(uuid.uuid4())
                zipped_module_path = file_utils.zip_file(script_path, f"{module_name}.psm1")
                blob_storage_uri = self.automation_session.upload_file_to_temp_storage(zipped_module_path)
                self.automation_session.upload_powershell_module(module_name, blob_storage_uri)
                logger.debug("Waiting for code execution...")


class PythonScriptExecutor(ScriptExecutor):

    EXTENSION = ".py"
    NAME = "Python"
    PIP_PACKAGE_NAME = "pip"
    UPLOAD_STATE_CHECK_INTERVAL_SECONDS = 15

    def __init__(self, automation_session: AzureAutomationSession) -> None:
        super().__init__(automation_session)

    def _wait_for_package_upload(self, package_name: str, timeout_seconds: int = UPLOAD_TIMEOUT):
        """
        Wait until the package upload flow is finished or until timeout (Blocking)

        :param package_name: Python package name to wait for
        :param timeout_seconds: Maximum time to wait for the upload

        :raises CloudMinerException: If the upload flow has not started for the given package
                                     If upload flow has finished with an error
                                     If timeout is reached
        """
        end_time = time.time() + timeout_seconds
        with LoggerIndent(logger):
            while time.time() < end_time:
                package_data = self.automation_session.get_python_package(package_name)
                if not package_data:
                    raise CloudMinerException(f"Upload flow for package {package_name} has failed to be started")
                
                upload_state = package_data["properties"]["provisioningState"]         
                if upload_state == UPLOAD_STATE.SUCCEEDED:
                    break
                elif upload_state == UPLOAD_STATE.FAILED:
                    error = package_data["properties"]["error"]["message"]
                    raise CloudMinerException("Python package upload failed. Error: ", error)
                else:
                    logger.debug(f"Upload state - '{upload_state}'")
                    time.sleep(PythonScriptExecutor.UPLOAD_STATE_CHECK_INTERVAL_SECONDS)
            else:
                raise CloudMinerException("Python package upload failed due to timeout")
        

    def execute_script(self, script_path: str, count: int):
        """
        Executes Python script within Azure Automation
        """
        package_path = os.path.join(file_utils.ROOT_DIRECTORY, "resources", PythonScriptExecutor.PIP_PACKAGE_NAME)
        main_file_path = os.path.join(package_path, "src", PythonScriptExecutor.PIP_PACKAGE_NAME, "main.py")
        shutil.copyfile(script_path, main_file_path)
        
        whl_path = file_utils.package_to_whl(package_path)
        logger.info(f"whl file successfully created - '{os.path.basename(whl_path)}'")
        
        logger.info(f"Replacing the default 'pip' package present in the Automation account...")
        blob_storage_uri = self.automation_session.upload_file_to_temp_storage(whl_path)
        self.automation_session.upload_python_package(PythonScriptExecutor.PIP_PACKAGE_NAME, blob_storage_uri)
        self._wait_for_package_upload(PythonScriptExecutor.PIP_PACKAGE_NAME)

        logger.info("Successfully replaced the pip package!")
        logger.info(f"Attempting to execute the Python script {count} times:")
        for index in range(count):
            logger.info(f"Triggering Python execution - {index+1}/{count}:")
            with LoggerIndent(logger):
                package_name = str(uuid.uuid4())
                blob_storage_uri = self.automation_session.upload_file_to_temp_storage(whl_path)
                self.automation_session.upload_python_package(package_name, blob_storage_uri)
                logger.debug(f"Waiting for code execution...")
