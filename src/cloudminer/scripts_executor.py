import os
import time
import uuid
import shutil
from typing import List
from abc import ABC, abstractmethod

import cloudminer.utils as utils
from cloudminer.logger import logger
from cloudminer.exceptions import CloudMinerException
from azure_automation_session import UPLOAD_STATE, UPLOAD_TIMEOUT, AzureAutomationSession


class ScriptExecutor(ABC):

    EXTENSION: str

    def __init__(self, automation_session: AzureAutomationSession, script_path: str) -> None:
        """
        :param automation_session: Automation account session to use
        :param script_path: Script to execute within Automation Account
        """
        super().__init__()
        self.automation_session = automation_session
        self.script_path = script_path

    @abstractmethod
    def execute_script(self, count: int):
        """
        Executes a script within Azure Automation

        :param count: Number of executions
        """
        pass


class PowershellScriptExecutor(ScriptExecutor):

    EXTENSION = ".ps1"

    def execute_script(self, count: int):
        """
        Executes Powershell module within Azure Automation

        :param count: Number of executions
        """
        for index in range(count):
            logger.info(f"Triggering Powershell execution - {index+1}/{count}:")
            logger.add_indent()
            module_name = str(uuid.uuid4())
            zipped_ps_module = utils.zip_file(self.script_path, f"{module_name}.psm1")
            self.automation_session.upload_powershell_module(module_name, zipped_ps_module)
            logger.info(f"Triggered module import flow in Automation Account. Code execution will be triggered in a few minutes...")
            logger.remove_indent()


class PythonScriptExecutor(ScriptExecutor):
    """
    ScriptExecutor class to execute Python scripts
    """
    EXTENSION = ".py"
    PIP_PACKAGE_NAME = "pip"
    UPLOAD_STATE_CHECK_INTERVAL_SECONDS = 20
    CUSTOM_PIP_PATH = os.path.join(utils.RESOURCES_DIRECTORY, PIP_PACKAGE_NAME)
    DUMMY_WHL_PATH = os.path.join(utils.RESOURCES_DIRECTORY, "random_whl-0.0.1-py3-none-any.whl")
    
    def __init__(self, automation_session: AzureAutomationSession, script_path: str, requirements_file: str = None) -> None:
        """
        :param automation_session: Automation account session to use
        :param script_path: Script to execute within Automation Account
        :param requirements_path: Path to requirements file to be installed and use by the script
        """
        super().__init__(automation_session, script_path)
        self.requirements_file = requirements_file

    def _delete_pip_if_exists(self):
        """
        Validate 'pip' package does not exist

        :param delete_if_exists: If True and package exists, deletes the package

        :raises CloudMinerException: If package exists and 'delete_if_exists' is False
        """
        pip_package = self.automation_session.get_python_package(PythonScriptExecutor.PIP_PACKAGE_NAME)
        if pip_package:
            logger.warning(f"Package '{PythonScriptExecutor.PIP_PACKAGE_NAME}' already exists in Automation Account. Deleting package")
            self.automation_session.delete_python_package(PythonScriptExecutor.PIP_PACKAGE_NAME)

    def _wait_for_package_upload(self, package_name: str, timeout_seconds: int = UPLOAD_TIMEOUT):
        """
        Wait until the package upload flow is finished or until timeout (Blocking)

        :param package_name: Python package name to wait for
        :param timeout_seconds: Maximum time to wait for the upload

        :raises CloudMinerException: If the upload flow has not started for the given package
                                     If upload flow has finished with an error
                                     If timeout is reached
        """
        logger.info(f"Waiting for package to finish upload. This might take a few minutes...")
        logger.add_indent()
        start_time = time.time()
        end_time = start_time + timeout_seconds
        while time.time() < end_time:
            package_data = self.automation_session.get_python_package(package_name)
            if not package_data:
                raise CloudMinerException(f"Upload flow for package '{package_name}' has failed to be started")
            
            upload_state = package_data["properties"]["provisioningState"]         
            if upload_state == UPLOAD_STATE.SUCCEEDED:
                logger.remove_indent()
                break
            elif upload_state == UPLOAD_STATE.FAILED:
                error = package_data["properties"]["error"]["message"]
                raise CloudMinerException("Python package upload failed. Error: ", error)
            else:
                logger.debug(f"Upload state - '{upload_state}'")
                time.sleep(PythonScriptExecutor.UPLOAD_STATE_CHECK_INTERVAL_SECONDS)
        else:
            raise CloudMinerException("Python package upload failed due to timeout")
        
    def _wrap_script(self) -> List[str]:
        """
        Construct lines of code for installing Python packages
        """
        INSTALL_REQUIREMENTS_CODE = []
        if self.requirements_file:
            with open(self.requirements_file, 'r') as f:
                requirements = [line.replace('\n', '') for line in f.readlines()]
                INSTALL_REQUIREMENTS_CODE = ["import requests, subprocess, sys, os, tempfile",
                                            "tmp_folder = tempfile.gettempdir()",
                                            "sys.path.append(tmp_folder)",
                                            "tmp_pip = requests.get('https://bootstrap.pypa.io/get-pip.py').content",
                                            "open(os.path.join(tmp_folder, 'tmp_pip.py'), 'wb+').write(tmp_pip)",
                                            f"subprocess.run(f'{{sys.executable}} {{os.path.join(tmp_folder, \"tmp_pip.py\")}} {' '.join(requirements)} --target {{tmp_folder}}', shell=True)"]
            
        return '\n'.join(["# Auto added by CloudMiner",
                          "######################################################################################"] +
                          INSTALL_REQUIREMENTS_CODE +
                          ["def _main():\n\tpass",
                          "######################################################################################\n"])
        

    def _create_whl_for_upload(self) -> str:
        """
        Creates a Python package whl using the given Python script

        :raises CloudMinerException: If failed to create .whl file
        """
        main_file_path = os.path.join(PythonScriptExecutor.CUSTOM_PIP_PATH, "src", PythonScriptExecutor.PIP_PACKAGE_NAME, "main.py")
        shutil.copyfile(self.script_path, main_file_path)

        #Add a main function to the file to be used as the entry point
        with open(main_file_path, 'r') as f:
            raw_main_file = f.read()
        
        wrapped_main_file = self._wrap_script() + raw_main_file

        with open(main_file_path, 'w') as f:
            f.write(wrapped_main_file)
            
        return utils.package_to_whl(PythonScriptExecutor.CUSTOM_PIP_PATH)

    def execute_script(self, count: int):
        """
        Executes Python script within Azure Automation

        :param script_path: .whl file path. Get using 'prepare_file_for_upload'
        :param count: Number of executions
        """
        self._delete_pip_if_exists()
        whl_path = self._create_whl_for_upload()
        logger.info(f"Replacing the default 'pip' package present in the Automation account:")
        logger.add_indent()
        self.automation_session.upload_python_package(PythonScriptExecutor.PIP_PACKAGE_NAME, whl_path)
        self._wait_for_package_upload(PythonScriptExecutor.PIP_PACKAGE_NAME)
        logger.remove_indent()

        logger.info("Successfully replaced the pip package!")
        for index in range(count):
            logger.info(f"Triggering Python execution - {index+1}/{count}:")
            logger.add_indent()
            package_name = str(uuid.uuid4())
            self.automation_session.upload_python_package(package_name, PythonScriptExecutor.DUMMY_WHL_PATH)
            logger.info(f"Code execution will be triggered in a few minutes...")
            logger.remove_indent()
