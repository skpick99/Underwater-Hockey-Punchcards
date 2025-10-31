# read players signed up for next hockey game
import os
import subprocess
import urllib.request, urllib.error, urllib.parse
from threading import Thread
import bs4
import webbrowser
import re  
import time
import shutil
from utils import *
from CInfo import CInfo

CHROME_PATH_WINDOWS = 'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe'
CHROME_PATH_WINDOWS = 'C:/Program Files/Google/Chrome/Application/chrome.exe'
CHROME_PATH_MAC = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'

# Setting up the path for Google Chrome on macOS
if os.name == 'nt':
    chrome_path = CHROME_PATH_WINDOWS
else:    
    chrome_path = CHROME_PATH_MAC
webbrowser.register('chrome', None, webbrowser.BackgroundBrowser(chrome_path))

#-------------------------------------------------------------------------------
def downloadMeetupAttendeesThread(url):
    if not isChromeRunning():
        start_chrome()

    print("Starting download", url)
    webbrowser.get('chrome').open(url)
    timeout = 30
    while getDownloadFileCount() != 1 and timeout > 0:
        timeout -= 1
        time.sleep(1)
    time.sleep(5)        
    return

#-------------------------------------------------------------------------------
def start_chrome():
    try:
        subprocess.Popen([chrome_path])
        time.sleep(5)  # wait for Chrome to open
    except Exception as e:
        print("Failed to start Chrome:", e)

#-------------------------------------------------------------------------------
def osRenameSafe(src, dst):
    retval = ""
    try:
        os.rename(src, dst)
    except FileNotFoundError:
        retval = "File not found"
    except Exception as e:
        retval = e
    return retval

#-------------------------------------------------------------------------------
def downloadNextPracticeAttendees():

    # download attendee file for upcoming practice
    pathname, filename = downloadAttendees("?type=upcoming")
    if len(pathname+filename) == 0:
        return False

    # Rename the downloaded file to "upcoming.csv". Keep the previous download for any error checking or comparisons.
    downloaded_file_loc = os.path.join(pathname, filename)
    target_file_loc = os.path.join(pathname, "upcoming.csv")
    history_file_loc = os.path.join(pathname, "upcoming_old.csv")
    try:
        os.remove(history_file_loc)
    except:
        pass
    osRenameSafe(target_file_loc, history_file_loc)
    retval = osRenameSafe(downloaded_file_loc, target_file_loc)    
    if len(retval) == 0:
        print("Info 352: Attendee download success:\n", target_file_loc)
    else:
        print("ERROR 553: Attendee download failed ", e)
    return retval

#-------------------------------------------------------------------------------
def downloadLastPracticeAttendees(date):
    # get game date
    if len(date) != 8:
        print(f"ERROR 424: Invalid date ('{date}')\n")
        return False

    pathname, filename = downloadAttendees("?type=past")
    if len(pathname + filename) == 0:
        return False

    # calculate paths
    dirname = pathname
    dirname_dest = os.path.join(getHockeyPath(), "games")    
    os.makedirs(dirname_dest, exist_ok=True)

    gameday_source = os.path.join(dirname, date + ".xls")
    gameday_dest = os.path.join(dirname_dest, date + ".xls")
    gameday_source_exists = os.path.isfile(gameday_source)
    gameday_dest_exists = os.path.isfile(gameday_dest)

    # if the gameday file already exists, delete it and use the new download
    if gameday_source_exists:
        print("WARNING 234: The gameday file already exists in the 'Downloads' folder. It will be deleted and replaced with the download.")
        os.remove(gameday_source)  
    fromfilename = os.path.join(pathname, filename)
    retval = osRenameSafe(fromfilename, gameday_source)
    if len(retval) == 0:
        print(f"Info 424: Renaming {fromfilename} to {date}.xls")
    else:
        print(f"ERROR 483: Error renaming {fromfilename} to {date}.xls")

    # copy Underwater_Hockey file from 'Downloads' folder to the autopay folder
    if gameday_dest_exists:
        print("WARNING 236: The gameday file already exists in the 'autopay' folder. It will be deleted and replaced.")
        os.remove(gameday_dest)
    shutil.copyfile(gameday_source, gameday_dest)
    print("INFO 421: Underwater Hockey gameday file for '" + date + "' has been copied into the 'autopay' folder")
    return True

#-------------------------------------------------------------------------------
def getEventNumber(pagesource):
    # get the event number for the next upcoming event
    searchstring = "-hockey-meetup/events/"
    sslen = len(searchstring)
    loc = 0
    bfound = False
    while not bfound:
        loc = pagesource.find(searchstring, loc)
        if loc < 0:
            eventnumber = ""
            bfound = True
        else:
            eventnumberstart = loc + sslen
            if pagesource[eventnumberstart].isdigit():
                stemp = pagesource[eventnumberstart:eventnumberstart+20]
                eventnumber = re.match("([0-9]*)", stemp).groups()[0]
                bfound = True
        loc += 1
    return eventnumber

#-------------------------------------------------------------------------------
def downloadAttendees(urlSuffix="?type=upcoming"):

    deleteAllDownloads()

    # given a url, get page content
    info = CInfo()
    url = info.getValue("meetup_url")
    urlsend = url + urlSuffix
    data = urllib.request.urlopen(urlsend).read()
    bs = bs4.BeautifulSoup(data, "xml")
    pagesource = bs.prettify()

    # get the event number and send it to chrome browser to download "attendee details", i.e. a list of people signed up
    # it is stored in the Windows Downloads directory
    pathname = ""
    filename = ""
    eventnumber = getEventNumber(pagesource)
    if len(eventnumber) > 0:
        #urlsend = url + eventnumber + "/csv/"
        urlsend = url + eventnumber + "/attendees/"        
        thread = Thread(target=downloadMeetupAttendeesThread, args=(urlsend,))
        thread.start()
        thread.join()
        print("download thread ended")

        if getDownloadFileCount() == 1:
            # get name of the attendee file just downloaded
            pathname, filename = getDownloadPathAndFile()
            if len(pathname + filename) == 0:
                print()
                print("ERROR 524: An error occurred getting the attendees file for the next practice")
                print()
        else:
            print()
            print("ERROR 326: No events were found on meetup for group ", url)
            print()

    return pathname, filename

#-------------------------------------------------------------------------------
def checkForDownload(date):
    # get game date
    if len(date) != 8:
        print(f"ERROR 428: Invalid date ('{date}')\n")
        return False

    # calculate paths
    dirname = getDownloadPath()
    dirname_dest = os.path.join(getHockeyPath(), "games")    
    os.makedirs(dirname_dest, exist_ok=True)

    gameday_source = os.path.join(dirname, date + ".csv")
    gameday_dest = os.path.join(dirname_dest, date + ".csv")
    gameday_source_exists = os.path.isfile(gameday_source)
    gameday_dest_exists = os.path.isfile(gameday_dest)

    # copy Underwater_Hockey file from 'Downloads' folder to the autopay folder
    if not gameday_dest_exists:
        shutil.copyfile(gameday_source, gameday_dest)
        print("INFO 421: Underwater Hockey gameday file for '" + date + "' has been copied into the 'autopay//games' folder")
    return True

#-------------------------------------------------------------------------------
if __name__ == "__main__":

    #downloadNextPracticeAttendees()
    print("all done")
