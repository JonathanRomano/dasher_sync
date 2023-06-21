import tkinter as tk
from tkinter import ttk
from tkinter import filedialog, messagebox

import os
import datetime
import time
from ftplib import FTP
from dotenv import load_dotenv

load_dotenv()

host = os.getenv("HOST")
user = os.getenv("ID")
password = os.getenv("PASSWORD")

default_folders = ['ANIM', 'FAB', 'INSTRUCTIONS', 'JPG', 'LOGO', 'MISE_NUIT', 'MP4', 'PSD', 'SCHEMA', 'SOURCE']
default_path = os.getenv("DEFAULT_PATH")

def directory_exists(ftp, directory_path):
    splited_path = directory_path.split('/')
    parent_dir = '/'.join(splited_path[:-1])
    dir_name = splited_path[-1]

    files = ftp.nlst(parent_dir)

    if len(splited_path) == 1:
        return dir_name in files

    return f'{parent_dir}/{dir_name}' in files

def make_folders(ftp, path):
    folders = path.split('/')
    current_path = ''

    for folder in folders:
        current_path += folder

        if not directory_exists(ftp, current_path):
            ftp.mkd(current_path)
        
        current_path += '/'


def upload_file(ftp, local_path, remote_path):
    parent_path = '/'.join(remote_path.split('/')[0:-1])
    
    make_folders(ftp,parent_path)

    with open(local_path, 'rb') as file:
        ftp.storbinary(f'STOR {remote_path}', file)

def iniciar():
    start_time = time.time()

    iniciar_button.configure(state='disabled')

    local_dir = textarea_select_folder.get()
    remote_dir = local_dir.split('/').pop()

    synced_files = 0
    pasted_files = 0
    
    # FTP conection
    ftp = FTP(host)
    ftp.login(user, password)

    if not ftp:
        messagebox.showinfo("ERRO", "Não foi possível estabelecer a conexão FTP.")

        iniciar_button.configure(state='active')
        return

    ftp.cwd(remote_dir)

    # list local files
    files = []

    for folder in default_folders:
        current_folder = os.path.join(local_dir, folder)
        for current_folder, subdiretorios, files_names in os.walk(current_folder):
            for file_name in files_names:
                file_path = os.path.join(current_folder, file_name)
                files.append(file_path)
    
    progress_bar['maximum'] = len(files)
    progress_bar.update()

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
        current_folder_list = ['ANIM', 'FAB', 'INSTRUCTIONS', 'JPG', 'LOGO', 'MISE_NUIT', 'MP4', 'PSD', 'SCHEMA', 'SOURCE'] # Diretorios padrão do force

        while current_folder_list != []:
            current_items = []

            for folder in current_folder_list:
                current_items += ftp.nlst(folder)

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
                print('mesmo arquivo!')
  

            else:
                upload_file(ftp, file, remote_file)
                synced_files += 1
        else:
            upload_file(ftp, file, remote_file)
            pasted_files += 1

        progress_bar['value'] += 1
        progress_bar.update()

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
    
    print(log)
    
    messagebox.showinfo("Concluído", f"{len(files)} arquivos sincronizados em {elapsed_time:.2f} segundos.")

    progress_bar['value'] = 0
    iniciar_button.configure(state='active')

    date = datetime.date.today().strftime("%d-%m-%Y")
    current_folder = os.path.dirname(os.path.abspath(__file__))

    with open(f"{current_folder}/logs/{date}.txt", "a") as log_file:
        log_file.write(log)

def selecionar_pasta(textarea):
    pasta_selecionada = filedialog.askdirectory(initialdir=default_path)
    if pasta_selecionada:
        textarea.delete(0, "end")
        textarea.insert("end", pasta_selecionada)

root = tk.Tk()
root.title("DasherSync")

root.geometry("600x100")

root.resizable(False, False)

root.grid_columnconfigure(0, weight=1)
root.grid_rowconfigure(0, weight=1)

textarea_select_folder = tk.Entry(root)
textarea_select_folder.grid(row=0, column=0, padx=10, pady=(2, 2), sticky="ew")

select_folder_button = tk.Button(root, text="Select", command=lambda: selecionar_pasta(textarea_select_folder))
select_folder_button.grid(row=0, column=1, padx=10, pady=(2, 2))

progress_bar = ttk.Progressbar(root ,value=0, maximum=100)
progress_bar.grid(row=2, columnspan=2, padx=10, pady=(2, 2), sticky="ew")

iniciar_button = tk.Button(root, text="Iniciar", command=iniciar)
iniciar_button.grid(row=3, columnspan=2, padx=10, pady=(2, 2), sticky="ew")

root.mainloop()
