import os
import psutil

#-------------------------------------------------------------------------------   
def isChromeRunning():
    # Adjust Chrome process name for macOS compatibility
    chrome_process_name = 'chrome.exe' if os.name == 'nt' else 'Google Chrome'
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info['name'] == chrome_process_name:
            return True
    return False

#-------------------------------------------------------------------------------        
def getHockeyPath():
    return os.path.abspath(os.path.dirname(__file__))

#-------------------------------------------------------------------------------        
def getDownloadPath():
    if os.name == 'nt':
        import winreg
        sub_key = r'SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders'
        downloads_guid = '{374DE290-123F-4565-9164-39C4925E467B}'
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_key) as key:
            location = winreg.QueryValueEx(key, downloads_guid)[0]
        return location
    else:
        # Using os.path.join() for cross-platform compatibility
        return os.path.join(os.path.expanduser('~'), 'Downloads')

#-------------------------------------------------------------------------------    
def getDownloadFileCount():
    dirname = getDownloadPath()
    count = 0
    for filename in os.listdir(dirname):
        if filename.upper().endswith('.XLS') and 'UNDERWATER' in filename.upper() and 'HOCKEY' in filename.upper():
            count += 1
    return count

#-------------------------------------------------------------------------------    
def deleteAllDownloads():
    dirname = getDownloadPath()
    files = [f for f in os.listdir(dirname) if f.upper().endswith('.XLS') and 'UNDERWATER' in f.upper() and 'HOCKEY' in f.upper()]
    for filename in files:
        os.remove(os.path.join(dirname, filename))
        print("Deleting file -->", filename, "<-- from directory", dirname)

#-------------------------------------------------------------------------------    
def getDownloadPathAndFile():
    dirname = getDownloadPath()
    files = [f for f in os.listdir(dirname) if f.upper().endswith('.XLS') and 'UNDERWATER' in f.upper() and 'HOCKEY' in f.upper()]
    files.sort()
    
    if len(files) < 1:
        print("ERROR 574: No Underwater_Hockey files found in the Downloads directory")
        return "", ""
    elif len(files) == 1:
        return dirname, files[0]
    else:
        print("Multiple Underwater_Hockey files")
        for f in files:
            print(f)
        use_this_file = files[-1]  # Default to the last file in the list
        yesno = input(f"Use '{use_this_file}' and delete all others? (Y/N): ").upper()
        if yesno == "Y":
            for f in files:
                if f != use_this_file:
                    os.remove(os.path.join(dirname, f))
            return dirname, use_this_file
        else:
            print("Operation cancelled by user.")
            return "", ""
