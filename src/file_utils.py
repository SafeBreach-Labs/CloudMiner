import os
import shutil
import zipfile
import tempfile
import subprocess


ROOT_DIRECTORY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_temp_file_path(file_name: str) -> str:
    temp_dir = tempfile.gettempdir()
    return os.path.join(temp_dir, file_name)

def get_file_extenstion(file_path: str):
    return os.path.basename(os.path.splitext(file_path)[1])

def get_file_name(file_path: str):
    return os.path.basename(os.path.splitext(file_path)[0])

def zip_file(source_file: str, file_name_within_archive: str = None, zip_path: str = None) -> str:
    src_file_name = get_file_name(source_file)
    
    if zip_path is None:
        zip_path = get_temp_file_path(f"{src_file_name}.zip")

    if file_name_within_archive is None:
        file_name_within_archive = src_file_name

    with zipfile.ZipFile(zip_path, "w") as zipf:
        zipf.write(source_file, arcname=file_name_within_archive)

    return zip_path

def package_to_whl(package_path: str):
    
    package_name = os.path.basename(package_path)
    setup_file = os.path.join(package_path, "setup.py")

    # Delete dist directory
    dist_dir_path = os.path.join(package_path, "dist")
    if os.path.exists(dist_dir_path):
        shutil.rmtree(dist_dir_path)

    print(f"[*] Creating a .whl file for package - '{package_name}' in temp directory")
    
    cmd = ["python", setup_file, "bdist_wheel"]
    
    print(f"[*] Running command: '{subprocess.list2cmdline(cmd)}'")
    process = subprocess.run(cmd, shell=True, cwd=package_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    try:
        whl_file_name = os.listdir(dist_dir_path)[0]
    except IndexError:
        raise Exception(f"Failed to create .whl file. Error: {process.stderr}")
    
    return os.path.join(dist_dir_path, whl_file_name)