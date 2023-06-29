from pymongo import MongoClient
import time
from ftplib import FTP

import os
from dotenv import load_dotenv

import datetime

load_dotenv("./.env")

host = os.getenv("HOST")
user = os.getenv("ID")
password = os.getenv("PASSWORD")

default_folders = ['ANIM', 'FAB', 'INSTRUCTIONS', 'JPG', 'LOGO', 'MISE_NUIT', 'MP4', 'PSD', 'SCHEMA', 'SOURCE']

directory = "/home/jonathan/2023"

def update_folder_list(directory):
    folder_list = []

    dirs = os.listdir(directory)
    for dir in dirs:
        if '.' not in dir:
            folder_list += [f"{directory}/{dir}/{item}" for item in os.listdir(f"{directory}/{dir}")]

    return folder_list

def find_project_folder(project_name, folder_list):
    for folder in folder_list:
        if folder.split('/')[-1] == project_name:
            return folder
        
    return False

def directory_exists(ftp, directory_path):
    splited_path = directory_path.split('/')
    parent_dir = '/'.join(splited_path[:-1])
    dir_name = splited_path[-1]

    files = ftp.nlst(parent_dir)

    if len(splited_path) <= 2:
        return dir_name in files

    return directory_path in files

def make_folders(ftp, path):
    folders = path.split('/')
    current_path = ''

    for folder in folders:
        current_path += folder

        print('path:' + current_path)
        if not directory_exists(ftp, current_path):
            print('criando: ' + current_path)
            ftp.mkd(current_path)
        
        current_path += '/'


def upload_file(ftp, local_path, remote_path):
    parent_path = '/'.join(remote_path.split('/')[0:-1])
    
    make_folders(ftp,parent_path)

    with open(local_path, 'rb') as file:
        ftp.storbinary(f'STOR {remote_path}', file)

def sync_data(local_dir, request_obj):
    obj_filter = {"projectId": request_obj["projectId"]}

    start_time = time.time()

    remote_dir = local_dir.split('/').pop()

    synced_files = 0
    pasted_files = 0
    
    # FTP connection
    try:
        ftp = FTP(host)
        ftp.login(user, password)

    except:
        operation = {"$set": {
            "status" : "errored",
            "history": request_obj["history"] + " - Error: There was an error on the FTP connection"
        }}
        
        collection.update_one(obj_filter, operation)
        return

    block_size = 128 * 1024  # 128KB em bytes

    ftp.cwd(remote_dir)

    # list local files
    files = []

    for folder in default_folders:
        current_folder = os.path.join(local_dir, folder)
        for current_folder, subdiretorios, files_names in os.walk(current_folder):
            for file_name in files_names:
                file_path = os.path.join(current_folder, file_name)
                files.append(file_path)
    
    max_progress = len(files)
    progress = 0
    def progress_percentage(progress, max_progress):
        return round((progress / max_progress) * 100)


    log = f'''
# LOG START #
# Sincronização iniciada
Input folder:{local_dir}
Output folder: {remote_dir} 
Total de arquivos: {len(files)}
'''

    # list remote files
    def is_dir(string):
        return '.' not in string

    def get_all_files(ftp):
        file_list = []
        current_folder_list = [folder for folder in ftp.nlst() if folder in default_folders]
        print(current_folder_list)

        while current_folder_list != []:
            current_items = []

            for folder in current_folder_list:
                print('folder: ' + folder)
                print(ftp.nlst(folder))
                current_items += [f'{folder}/{item.split("/")[-1]}' for item in ftp.nlst(folder)]

            file_list += [item for item in current_items if not is_dir(item)]
            current_folder_list = [item for item in current_items if is_dir(item)]

        return file_list
    
    remote_files = get_all_files(ftp)

    # Main iteration
    for file in files:
        remote_file = file.replace(local_dir + '/', '')
        
        if remote_file in remote_files:
            remote_size = ftp.size(remote_file)
            local_size = os.path.getsize(file)

            if remote_size == local_size:
                print(f'{file} is updated!')
  

            else:
                upload_file(ftp, file, remote_file)
                synced_files += 1
        else:
            upload_file(ftp, file, remote_file)
            pasted_files += 1

        progress += 1

        operation = {"$set": {
            "progress": progress_percentage(progress, max_progress)
        }}
        
        collection.update_one(obj_filter, operation)

    ftp.quit()
    
    end_time = time.time()
    elapsed_time = end_time - start_time

    log += f'''
Arquivos enviados: {pasted_files}
Arquivos sincronizados: {synced_files}
Arquivos ignorados: {len(files) - (pasted_files + synced_files)}
{len(files)} arquivos sincronizados em {elapsed_time:.2f} segundos.
# LOG END #
'''
    
    

    operation = {"$set": {
        "status": "completed",
        "history": request_obj["history"] + f" - {len(files)} files synchronized in {elapsed_time:.2f} seconds."
    }}
        
    collection.update_one(obj_filter, operation)

    date = datetime.date.today().strftime("%d-%m-%Y")
    current_folder = os.path.dirname(os.path.abspath(__file__))

    with open(f"./logs/{date}.txt", "a") as log_file:
        log_file.write(log)

client = MongoClient(os.getenv('MONGO_URI'))

collection = client.test.syncrequests
filter = {"status": "pending"}

iteration = 0
while True:
    query = list(collection.find(filter))
    print(f'iteration n: {iteration}')

    if len(query) != 0:

        for request in query:
            folder_list = update_folder_list(directory)
            project_folder = find_project_folder(request["projectName"], folder_list)
            
            if not project_folder:
                operation = {"$set": {
                    "status" : "errored",
                    "history": request["history"] + " - Error: The script could not find the folder with the correct default formatting."
                }}
        
                collection.update_one({"projectId": request["projectId"]}, operation)
            
            else:
                sync_data(project_folder, request)

    iteration += 1
    time.sleep(1) # É nescesario?...