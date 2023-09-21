import os
import json
import argparse
import subprocess

import file_utils
from azure_automation_session import AzureAutomationSession
from scripts_executor import PowershellScriptExecutor, PythonScriptExecutor


def get_access_token():
    try:
        process = subprocess.run(["az", "account", "get-access-token"], shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if process.returncode != 0:
            raise Exception(f"Failed to get access token using Azure CLI. Error - {process.stderr}")
         
    except FileNotFoundError:
        raise Exception("Azure CLI is not installed on the system.")

    return json.loads(process.stdout)["accessToken"]
    

def main():
    parser = argparse.ArgumentParser(description="Cloud Miner - Free compute in Azure")
    parser.add_argument("--path", type=str, help="The script path (Powershell or Python)", required=True)
    parser.add_argument("--id", type=str, help="ID of Automation account - /subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/Microsoft.Automation/automationAccounts/{automationAccountName}", required=True)
    parser.add_argument("-c","--count", type=int, help="Number of executions", required=True)
    args = parser.parse_args()
    print("""
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
""")
    if not os.path.exists(args.path):
        raise Exception(f"Path '{args.path}' does not exist!")
    
    file_extension = file_utils.get_file_extenstion(args.path)
    executor_class = None
    if file_extension == PowershellScriptExecutor.EXTENSION:
        executor_class = PowershellScriptExecutor

    elif file_extension == PythonScriptExecutor.EXTENSION:
        executor_class = PythonScriptExecutor

    else:
        raise Exception(f"File extension {file_extension} is not supported")

    print(f"[*] File type detected - {executor_class.NAME}")
    print("[*] Retrieving access token using Azure CLI...")
    access_token = get_access_token()
    automation_session = AzureAutomationSession(args.id, access_token)
    print("[+] Access token is valid")
    executor = executor_class(automation_session)
    executor.execute_script(args.path, args.count)
    
    print("\n[+] Finished successfully :)")

if __name__ == "__main__":
    main()

