import os
import json
import logging
import argparse
import subprocess

import file_utils
from logger import logger
from cloudminer import CloudMinerException
from azure_automation_session import AzureAutomationSession
from scripts_executor import PowershellScriptExecutor, PythonScriptExecutor


def get_access_token() -> str:
    """
    Retrieve Azure access token using Azure CLI

    :raises CloudMinerException: If Azure CLI is not installed or not in PATH environment variable
                                 If account is not logged in via Azure CLI
                                 If failed to retrieve account access token
    """
    logger.debug("Retrieving access token using Azure CLI...")
    try:
        # Check if user is logged in
        process = subprocess.run(["az", "account", "show"],
                                 shell=True,
                                 text=True,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        
        if process.returncode != 0:
            raise CloudMinerException(f"Account must be logged in via Azure CLI")
        
        process = subprocess.run(["az", "account", "get-access-token"],
                                 shell=True,
                                 text=True,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        
        if process.returncode != 0:
            raise CloudMinerException(f"Failed to retrieve access token using Azure CLI. Error - {process.stderr}")
         
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
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose mode')
    return parser.parse_args()


def main():
    args = parse_args()
    
    level = logging.DEBUG if args.verbose else logging.INFO
    logger.setLevel(level)
    logger.info("""
  /$$$$$$  /$$                           /$$ /$$      /$$ /$$                                        /$$   
 /$$__  $$| $$                          | $$| $$$    /$$$|__/                                      /$$$$$$ 
| $$  \__/| $$  /$$$$$$  /$$   /$$  /$$$$$$$| $$$$  /$$$$ /$$ /$$$$$$$   /$$$$$$   /$$$$$$        /$$__  $$
| $$      | $$ /$$__  $$| $$  | $$ /$$__  $$| $$ $$/$$ $$| $$| $$__  $$ /$$__  $$ /$$__  $$      | $$  \__/
| $$      | $$| $$  \ $$| $$  | $$| $$  | $$| $$  $$$| $$| $$| $$  \ $$| $$$$$$$$| $$  \__/      |  $$$$$$ 
| $$    $$| $$| $$  | $$| $$  | $$| $$  | $$| $$\  $ | $$| $$| $$  | $$| $$_____/| $$             \____  $$
|  $$$$$$/| $$|  $$$$$$/|  $$$$$$/|  $$$$$$$| $$ \/  | $$| $$| $$  | $$|  $$$$$$$| $$             /$$  \ $$
 \______/ |__/ \______/  \______/  \_______/|__/     |__/|__/|__/  |__/ \_______/|__/            |  $$$$$$/
                                                                                                  \_  $$_/ 
                                                                                                    \__/   

\n\t-- CloudMiner: v1.0.0 (SafeBreach Labs) --\n""")
    
    if not os.path.exists(args.path):
        raise CloudMinerException(f"Script path '{args.path}' does not exist!")
    
    access_token = args.token or get_access_token()
    automation_session = AzureAutomationSession(args.id, access_token)

    logger.debug(f"Script path - {args.path}")
    file_extension = file_utils.get_file_extension(args.path)
    if file_extension == PowershellScriptExecutor.EXTENSION:
        executor = PowershellScriptExecutor(automation_session)

    elif file_extension == PythonScriptExecutor.EXTENSION:
        executor = PythonScriptExecutor(automation_session)

    else:
        raise CloudMinerException(f"File extension {file_extension} is not supported")

    logger.info(f"File type detected - {executor.NAME}")
    
    executor.execute_script(args.path, args.count)
    logger.info("CloudMiner finished successfully :)")

if __name__ == "__main__":
    main()
