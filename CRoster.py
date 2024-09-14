import os
import sys 
import csv
from utils import *
from CInfo import CInfo

#-------------------------------------------------------------------------------
class CRoster:
    def __init__(self):
        self.R_HOCKEYUSERID = 0        
        self.R_MEETUPNAME = 1        
        self.R_FIRSTNAME = 2
        self.R_LASTNAME = 3
        self.R_EMAIL = 4
        self.R_PHONE = 7
        self.R_STARS = 9
        self.R_CUMSTARS = 10
        self.path = getHockeyPath()
        self.rosterFileHeader = [
            "Hockey User ID", "Meetup name", "First", "Last", "Email", 
            "Address", "isMember", "textPhone", "Stars", "altPhone", 
            "altPhoneDesc", "useEmail", "useText", "everyCharge", 
            "weekly", "monthly", "whenXleft"
            ]
        self.roster = {}
        self._loadRoster()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # close, deallocate, etc
        pass

    #-------------------------------------------------------------------------------    
    def _loadRoster(self):
        self.roster = {}
        filepath = os.path.join(self.path, "roster.csv")
        with open(filepath, newline='') as csvfile:
            rows = csv.reader(csvfile, delimiter='\t', quotechar='"')
            next(rows)  # skip header
            for row in rows:
                if len(row) > 0:           
                    self.roster[row[self.R_HOCKEYUSERID]] = row
        return

    #-------------------------------------------------------------------------------    
    def saveRoster(self):
        player_list = list(set(self.roster.keys()))
        meetup_name_list = [self.roster[player][self.R_MEETUPNAME].upper() for player in player_list]
        sort_index = sorted(range(len(meetup_name_list)), key=meetup_name_list.__getitem__)

        filepath = os.path.join(self.path, "roster.csv")
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile, delimiter='\t', quotechar='"', quoting=csv.QUOTE_NONNUMERIC)
            writer.writerow(self.rosterFileHeader)
            for idx in sort_index:
                writer.writerow(self.roster[player_list[idx]])
        return

    #-------------------------------------------------------------------------------    
    def createEmptyRow(self):
        return [''] * len(self.rosterFileHeader)

    #-------------------------------------------------------------------------------    
    def addNewPlayer(self, hockeyID, meetupName, firstName, lastName, email, address, isMember, phone):
        
        if hockeyID in self.roster:
            info = CInfo()
            print("ERROR 986: Trying to add player who is already in the roster. Contact ", 
                  info.getValue("admin_contact_info"), hockeyID, meetupName)
            sys.exit(93)
        
        if len(address) > 0:
            print("Saving address to roster in addNewPlayer() is not yet implemented")
        if len(isMember) > 0:
            print("Saving isMember to roster in addNewPlayer() is not yet implemented")            
        
        newrow = self.createEmptyRow()
        newrow[self.R_HOCKEYUSERID] = hockeyID
        newrow[self.R_MEETUPNAME] = meetupName
        newrow[self.R_FIRSTNAME] = firstName
        newrow[self.R_LASTNAME] = lastName
        newrow[self.R_EMAIL] = email
        newrow[self.R_PHONE] = phone    
        newrow[self.R_STARS] = '0'    
        newrow[self.R_CUMSTARS] = '0'            
        self.roster[hockeyID] = newrow
        self.saveRoster()
        
    #-------------------------------------------------------------------------------    
    def getStars(self, hockeyID):
        retval = 0
        try:           
            retval = int(self.roster[hockeyID][self.R_STARS])
        except:
            retval = None
        return retval
    
    #-------------------------------------------------------------------------------    
    def setStars(self, hockeyID, stars):
        retval = True
        try:           
            self.roster[hockeyID][self.R_STARS] = str(stars)
        except:
            retval = False
            print()
            for i in range(5):
                print("ERROR:", self.roster[hockeyID][self.R_FIRSTNAME], self.roster[hockeyID][self.R_LASTNAME], "DID NOT SET THEIR STAR TO", stars)
            print()            
        return retval

    #-------------------------------------------------------------------------------    
    def incrStars(self, hockeyID):
        try:           
            self.roster[hockeyID][self.R_STARS] = str(int(self.roster[hockeyID][self.R_STARS]) + 1)
            self.roster[hockeyID][self.R_CUMSTARS] = str(int(self.roster[hockeyID][self.R_CUMSTARS]) + 1)
            retval = int(self.roster[hockeyID][self.R_STARS])
        except:
            print()
            for i in range(5):
                print("ERROR:", self.roster[hockeyID][self.R_FIRSTNAME], self.roster[hockeyID][self.R_LASTNAME], "DID NOT GET THEIR STAR !!!")
            print()
            x = input("ACKNOWLEDGE ERROR BY HITTING <ENTER>")
            retval = -1
        return retval

    #-------------------------------------------------------------------------------    
    def getMeetupName(self, hockeyID):
        retval = ""
        try:           
            retval = self.roster[hockeyID][self.R_MEETUPNAME]
        except:
            retval = ""
        return retval
            
    #-------------------------------------------------------------------------------    
    def getEmail(self, hockeyID):
        return self.roster.get(hockeyID, [""])[self.R_EMAIL]

    #-------------------------------------------------------------------------------    
    def getPlayers(self, partialPlayerName):
        partialPlayerName = partialPlayerName.upper()
        retval = [self.roster[player] for player in self.roster if self.roster[player][self.R_MEETUPNAME].upper().find(partialPlayerName) >= 0]               
        if len(retval) == 0:
            retval = [self.roster[player] for player in self.roster 
                      if self.roster[player][self.R_FIRSTNAME].upper().find(partialPlayerName) >= 0 or 
                         self.roster[player][self.R_LASTNAME].upper().find(partialPlayerName) >= 0]
        return retval 

    #-------------------------------------------------------------------------------    
    def printRoster(self):
        print("Underwater Hockey Roster")
        print("-------------------------")
        for player in self.roster.values():
            print(f"{player[self.R_HOCKEYUSERID]:<16} {player[self.R_MEETUPNAME]}")
        print("")

    #-------------------------------------------------------------------------------    
    def getPlayerName(self):
        while True:
            print("")
            playername = input("Enter some portion of the player name (or nothing to exit): ")
            if len(playername) == 0:
                return None
            players = self.getPlayers(playername)        
            if len(players) == 1:
                ok = input("Did you mean " + players[0][self.R_HOCKEYUSERID] + " (" + players[0][self.R_FIRSTNAME] + " " + players[0][self.R_LASTNAME] + ")? (y/n) ")
                if len(ok) == 0 or ok.upper()[0] != "Y":
                    print("Nothing done")
                else:
                    return players[0]
            elif len(players) == 0:
                print("Sorry, we have no players that match your request")
            elif len(players) > 1:
                print("There are multiple matches.  You'll need to be more specific.")
                for player in players:
                    print("         ", player[0])
        return None

    #-------------------------------------------------------------------------------    
    def playHistory(self, playerRec):
        print()
        print("Play History for ", playerRec)
        print("-------------------------------------------------------------")

        # get game history files
        files = []
        files = [filename for filename in os.listdir(os.path.join(self.path, "games")) if len(filename)==12 and filename.upper().startswith('20') and filename.upper().endswith('.XLS')]
        files.sort()

        # check each play date to see if player included on that day
        for filename in files:
            filepath = os.path.join(self.path, "games", filename)
            with open(filepath, newline='') as csvfile:
                rows = csv.reader(csvfile, delimiter='\t', quotechar='"')
                for row_number,row in enumerate(rows):
                    if row_number > 0 and len(row) > 0:
                        if row[1] == playerRec[self.R_HOCKEYUSERID] and len(row[1]) > 0:	    #SKPTODO hockeyuserid vs meetupuserid
                            print(filename[0:8])    
        print()
        return         

#-------------------------------------------------------------------------------           
if __name__ == "__main__":        

    roster = CRoster()
    roster.printRoster()
    roster.saveRoster()

    playerRec = roster.getPlayerName()

    if not playerRec is None:        
        print("Player record: ", playerRec)
        roster.playHistory(playerRec)

    print("all done")

