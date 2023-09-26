import os
import zipfile
import tempfile
import subprocess

from logger import logger
from cloudminer import CloudMinerException


ROOT_DIRECTORY = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_temp_file_path(file_name: str) -> str:
    """
    Returns the user temp directory
    """
    temp_dir = tempfile.gettempdir()
    return os.path.join(temp_dir, file_name)


def get_file_extension(file_path: str):
    """
    Get file extension from file path
    """
    return os.path.basename(os.path.splitext(file_path)[1])


def get_file_name(file_path: str):
    """
    Get file name from full file path
    """
    return os.path.basename(os.path.splitext(file_path)[0])


def zip_file(source_file: str, file_name_within_archive: str = None, zip_path: str = None) -> str:
    """
    Zip a file

    :param source_file: file path to zip
    :param file_name_within_archive: name of file within the zip archive
    :param zip_path: path to the zipped file
    """
    src_file_name = get_file_name(source_file)
    if zip_path is None:
        zip_path = get_temp_file_path(f"{src_file_name}.zip")

    if file_name_within_archive is None:
        file_name_within_archive = src_file_name

    with zipfile.ZipFile(zip_path, "w") as zipf:
        zipf.write(source_file, arcname=file_name_within_archive)

    return zip_path


def package_to_whl(package_path: str):
    """
    Create a whl file from a given Python package
        whl file wil lbe saved in the dist directory
    """
    package_name = os.path.basename(package_path)
    setup_file = os.path.join(package_path, "setup.py")
    dist_dir_path = os.path.join(package_path, "dist")

    logger.debug(f"Creating a .whl file for package - '{package_name}'")
    cmd = ["python", setup_file, "bdist_wheel"]
    logger.debug(f"Running command: '{subprocess.list2cmdline(cmd)}'")
    process = subprocess.run(cmd, shell=True, cwd=package_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    try:
        whl_file_name = os.listdir(dist_dir_path)[0]
    except IndexError:
        raise CloudMinerException(f"Failed to create .whl file. Error: {process.stderr}")
    
    return os.path.join(dist_dir_path, whl_file_name)