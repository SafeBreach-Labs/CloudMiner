# CloudMiner
Execute code within Azure Automation service without getting charged

## Description
CloudMiner is a tool designed to get free computing power within Azure Automation service. The tool utilizes the upload module/package flow to execute code which is totally free to use. This tool is intended for educational and research purposes only and should be used responsibly and with proper authorization.

* This flow was reported to Microsoft on 3/23 which decided to not change the service behavior as it's considered as "by design". As for 3/9/23, this tool can still be used without getting charged.

* Each execution is limited to 3 hours

## Requirements
1. Python 3.8+ with the libraries mentioned in the file `requirements.txt`
2. Configured Azure CLI - https://learn.microsoft.com/en-us/cli/azure/install-azure-cli
    - Account must be logged in before using this tool

## Installation
```pip install .```

## Usage
```
usage: cloud_miner.py [-h] --path PATH --id ID -c COUNT [-t TOKEN] [-r REQUIREMENTS] [-v]

CloudMiner - Free computing power in Azure Automation Service

optional arguments:
  -h, --help            show this help message and exit
  --path PATH           the script path (Powershell or Python)
  --id ID               id of the Automation Account - /subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/Microsoft.Automation/a
                        utomationAccounts/{automationAccountName}
  -c COUNT, --count COUNT
                        number of executions
  -t TOKEN, --token TOKEN
                        Azure access token (optional). If not provided, token will be retrieved using the Azure CLI
  -r REQUIREMENTS, --requirements REQUIREMENTS
                        Path to requirements file to be installed and use by the script (relevant to Python scripts only)
  -v, --verbose         Enable verbose mode
```

## Example usage
### Python
![Alt text](images/cloud-miner-usage-python.png?raw=true "Usage Example")
### Powershell
![Alt text](images/cloud-miner-usage-powershell.png?raw=true "Usage Example")

## License
CloudMiner is released under the BSD 3-Clause License.
Feel free to modify and distribute this tool responsibly, while adhering to the license terms.

## Author - Ariel Gamrian
* LinkedIn - [Ariel Gamrian](https://www.linkedin.com/in/ariel-gamrian/)