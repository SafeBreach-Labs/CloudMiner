import os
import sys
import zipfile
import tempfile
import subprocess
from typing import List

from cloudminer.logger import logger
from cloudminer.exceptions import CloudMinerException

RESOURCES_DIRECTORY = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0])))), "resources")
PROJECT_BANNER = """
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

\n-- CloudMiner: v1.0.0 (SafeBreach Labs) --\n"""

def get_temp_file_path(file_name: str) -> str:
    """
    Returns the user temp directory
    """
    temp_dir = tempfile.gettempdir()
    return os.path.join(temp_dir, file_name)


def get_file_extension(file_path: str):
    """
    Returns the file extension from file path
    """
    return os.path.basename(os.path.splitext(file_path)[1])


def get_file_name(file_path: str):
    """
    Returns the file name from full file path
    """
    return os.path.basename(os.path.splitext(file_path)[0])


def zip_file(source_file: str, file_name_within_archive: str = None, zip_path: str = None) -> str:
    """
    Zip a file

    :param source_file: File path to zip
    :param file_name_within_archive: Name of file within the zip archive
    :param zip_path: Path to the zipped file. If None, will use the temp directory
    
    :return: zip file path
    """
    src_file_name = get_file_name(source_file)
    if zip_path is None:
        zip_path = get_temp_file_path(f"{src_file_name}.zip")

    if file_name_within_archive is None:
        file_name_within_archive = src_file_name

    with zipfile.ZipFile(zip_path, "w") as zipf:
        zipf.write(source_file, arcname=file_name_within_archive)

    logger.debug(f"Zip file created at '{zip_path}'")
    return zip_path


def run_command(cmd: List[str], shell: bool = True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs) -> subprocess.CompletedProcess:
    """
    Helper function to run commands
    """
    logger.debug(f"Running command: '{subprocess.list2cmdline(cmd)}'")
    return subprocess.run(cmd,
                          shell=shell,
                          text=text,
                          stdout=stdout,
                          stderr=stderr,
                          **kwargs)


def package_to_whl(package_path: str) -> str:
    """
    Create a whl file from a given Python package
        whl file wil lbe saved in the dist directory

    :raises CloudMinerException: If failed to create whl file
    
    :return: whl file path
    """
    package_name = os.path.basename(package_path)
    setup_file = os.path.join(package_path, "setup.py")
    dist_dir_path = os.path.join(package_path, "dist")

    logger.debug(f"Creating a .whl file for package - '{package_name}'")
    process = run_command(["python", setup_file, "bdist_wheel"], cwd=package_path)
    if process.returncode != 0:
        raise CloudMinerException(f"Failed to create .whl file. Error: {process.stderr}")

    try:
        whl_file_name = os.listdir(dist_dir_path)[0]
    except IndexError:
        raise CloudMinerException(f"Failed to find the creatd .whl file in folder '{dist_dir_path}'.")
    
    logger.info(f"whl file successfully created - '{whl_file_name}'")
    return os.path.join(dist_dir_path, whl_file_name)
