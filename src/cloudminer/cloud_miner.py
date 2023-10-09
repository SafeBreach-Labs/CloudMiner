import os
import json
import logging
import argparse

import cloudminer.utils as utils
from cloudminer.logger import logger
from cloudminer.exceptions import CloudMinerException
from azure_automation_session import AzureAutomationSession
from scripts_executor import PowershellScriptExecutor, PythonScriptExecutor


def get_access_token_from_cli() -> str:
    """
    Retrieve Azure access token using Azure CLI

    :raises CloudMinerException: If Azure CLI is not installed or not in PATH environment variable
                                 If account is not logged in via Azure CLI
                                 If failed to retrieve account access token
    """
    logger.info("Retrieving access token using Azure CLI...")
    try:
        # Check if user is logged in
        process = utils.run_command(["az", "account", "show"])
        if process.returncode != 0:
            raise CloudMinerException(f"Account must be logged in via Azure CLI")
        
        process = utils.run_command(["az", "account", "get-access-token"])
        if process.returncode != 0:
            raise CloudMinerException(f"Failed to retrieve access token using Azure CLI. Error: {process.stderr}")
         
    except FileNotFoundError:
        raise CloudMinerException("Azure CLI is not installed on the system or not in PATH environment variable")

    return json.loads(process.stdout)["accessToken"]
    

def parse_args() -> argparse.Namespace:
    """
    Parse command line arguments
    """
    parser = argparse.ArgumentParser(description="CloudMiner - Free computing power in Azure Automation Service")
    parser.add_argument("--path", type=str, help="the script path (Powershell or Python)", required=True)
    parser.add_argument("--id", type=str, help="id of the Automation Account - /subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/Microsoft.Automation/automationAccounts/{automationAccountName}", required=True)
    parser.add_argument("-c","--count", type=int, help="number of executions", required=True)
    parser.add_argument("-t","--token", type=str, help="Azure access token (optional). If not provided, token will be retrieved using the Azure CLI")
    parser.add_argument("-r","--requirements", type=str, help="Path to requirements file to be installed and use by the script (relevant to Python scripts only)")
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose mode')
    return parser.parse_args()


def main():
    args = parse_args()
    level = logging.DEBUG if args.verbose else logging.INFO
    logger.setLevel(level)
    logger.info(utils.PROJECT_BANNER)
    
    if not os.path.exists(args.path):
        raise CloudMinerException(f"Script path '{args.path}' does not exist!")
    
    if args.requirements and not os.path.exists(args.requirements):
        raise CloudMinerException(f"Requirements path '{args.requirements}' does not exist!")
    
    access_token = args.token or get_access_token_from_cli()
    automation_session = AzureAutomationSession(args.id, access_token)

    file_extension = utils.get_file_extension(args.path).lower()
    if file_extension == PowershellScriptExecutor.EXTENSION:
        logger.info(f"File type detected - Powershell")
        executor = PowershellScriptExecutor(automation_session, args.path)

    elif file_extension == PythonScriptExecutor.EXTENSION:
        logger.info(f"File type detected - Python")
        executor = PythonScriptExecutor(automation_session, args.path, args.requirements)

    else:
        raise CloudMinerException(f"File extension {file_extension} is not supported")

    
    executor.execute_script(args.count)
    
    logger.info("CloudMiner finished successfully :)")

if __name__ == "__main__":
    main()
