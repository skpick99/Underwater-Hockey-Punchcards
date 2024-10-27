import os
import sys
import csv
import CPunchcards
import CEmail
import CRoster
from CInfo import CInfo
from utils import *
import pandas as pd
import datetime
sys.path.append("\\")

THURSDAY = 3

#-------------------------------------------------------------------------------
class CGameDay:
    def __init__(self, date = ""):
        self.path = getHockeyPath()
        self.M_MEETUPNAME = 0
        self.M_MEETUPUSERID = 1
        self.M_SIGNUPTIME = 6
        self.X_MEETUPNAME = 0           
        self.X_MEETUPUSERID = 1
        self.X_HOCKEYUSERID = 2   
        self.meetupRosterHeader = ["Meetup name", "Meetup User ID", "Hockey User ID"]
        self.gameday = {}
        self.gameday_df = None
        self.info = CInfo()
        self.useStars = self.info.getValue("use_stars")
        self.date = date
        if len(date) > 0:            
            self._loadGameDay()
        
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        # close, deallocate, etc
        pass
  
    #-------------------------------------------------------------------------------    
    def _loadGameDay(self):
        
        # create the meetup/roster ID cross reference
        self._createXref()       
        
        # loadup attendees from meetup
        self.gameday = {}
        filepath = os.path.join(self.path, "games", f"{self.date}.xls")
        if not os.path.exists(filepath):
            print(f"\nERROR 594: No game file exists for {self.date}")
            return       
            
        try:
            df = pd.read_csv(filepath, delimiter='\t')
            df['RSVPed on'] = pd.to_datetime(df['RSVPed on'])
            self.gameday_df = df
        except Exception as e:
            print(f"Error reading attendees file: {e}")
            self.gameday_df = None

        print(f"The following players played UWH on {self.date}")
        print(f"--------------------------------------------")        
        with open(filepath, newline='') as csvfile:
            rows = csv.reader(csvfile, delimiter='\t', quotechar='"')
            for row_number,row in enumerate(rows):
                print(', '.join(row))
                if row_number > 0 and len(row) > 0:
                    row[self.M_SIGNUPTIME] = df.iloc[row_number-1]['RSVPed on']
                    self.gameday[row[self.M_MEETUPUSERID]] = row     
        return

    #-------------------------------------------------------------------------------    
    def _createXref(self):  
        self.idXref = {}
        filepath = os.path.join(self.path, "meetup_roster.csv")
        try:
            with open(filepath, newline='') as csvfile:
                rows = csv.reader(csvfile, delimiter='\t', quotechar='"')
                next(rows)
                for row in rows:
                    if len(row) > 0:    
                        self.idXref[row[self.X_MEETUPUSERID]] = row[self.X_HOCKEYUSERID]     
        except Exception as e:
            print(f"Error reading xref file: {e}")
       
    #-------------------------------------------------------------------------------    
    def isValid(self):    
        return (len(self.gameday) > 0)
        
    #-------------------------------------------------------------------------------    
    def addNewXref(self, hockeyID, meetupName, meetupID):
        if meetupID in self.idXref:

            print("ERROR 977: Trying to add player who is already in the roster XREF. Contact ", 
                  self.info.getValue("admin_contact_info"), hockeyID, meetupName, meetupID)
            sys.exit(92)
            
        # load the meetup_roster.csv file
        filepath = os.path.join(self.path, "meetup_roster.csv")
        rowlist = []
        with open(filepath, newline='') as csvfile:
            rows = csv.reader(csvfile, delimiter='\t', quotechar='"')
            next(rows)
            for row in rows:
                rowlist.append(row)                         
                
        # add new row
        newrow = ['','','']
        newrow[self.X_HOCKEYUSERID] = hockeyID
        newrow[self.X_MEETUPNAME] = meetupName
        newrow[self.X_MEETUPUSERID] = meetupID    
        rowlist.append(newrow)     

        # sort into meetupName order
        rowlist = sorted(rowlist, key=lambda x: x[self.X_MEETUPNAME].upper())
        
        # save the meetup_roster.csv file
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile, delimiter='\t', quotechar='"', quoting=csv.QUOTE_ALL)
            writer.writerow(self.meetupRosterHeader)
            writer.writerows(rowlist)
            
        # load the new cross reference
        self._createXref()
    
    #-------------------------------------------------------------------------------    
    def addPlayerToRoster(self):

        roster = CRoster.CRoster()
        new_player_list = [meetup_id for meetup_id in self.gameday if not roster.getMeetupName(self.getHockeyID(meetup_id))]

        if not new_player_list:
            print("No new players to add.")
            return

        print()
        for index, meetup_id in enumerate(new_player_list, 1):
            print(f"Choice {index}: {meetup_id} {self.gameday[meetup_id][self.M_MEETUPNAME]}")

        choice = input("Which choice would you like to add? ")
        try:
            choice_val = int(choice)
            if 1 <= choice_val <= len(new_player_list):
                add_meetup_id = new_player_list[choice_val - 1]
                add_meetup_name = self.gameday[add_meetup_id][self.M_MEETUPNAME]
                email = input("Email address ")
                phone = input("Phone number ")
                if input("OK to add to our permanent roster? (y/n) ").strip().upper() == "Y":
                    roster.addNewPlayer(add_meetup_id, add_meetup_name, add_meetup_name, add_meetup_name, email, "", "", phone)
                    self.addNewXref(add_meetup_id, add_meetup_name, add_meetup_id)
                    print(f"Added to roster --> {add_meetup_id} {self.gameday[add_meetup_id][self.M_MEETUPNAME]}")
                else:
                    print("Nothing done")                    
            else:
                print("Nothing done")
        except ValueError:
            print("Invalid choice")

    #-------------------------------------------------------------------------------    
    def isEarlyBird(self, meetupID, gameDate):
        # all variables as datetime
        dt_signupTime = self.gameday[meetupID][self.M_SIGNUPTIME]
        dt_gameDate = datetime.datetime.strptime(gameDate, "%Y%m%d")

        # cutoff time for both games (Friday and Sunday) are at Thursday midnight
        dt_cutoff = dt_gameDate.date()
        while dt_cutoff.weekday() != THURSDAY:
            dt_cutoff -= datetime.timedelta(days=1)

        retval = (dt_signupTime.date() <= dt_cutoff)
        return retval

    #-------------------------------------------------------------------------------    .
    def printGameDay(self):
        
        punchcards = CPunchcards.CPunchcards()
        
        print()
        print(f"Underwater Hockey Gameday for {self.date}")
        print("---------------------------------------------")
        
        for meetupID in self.gameday:
            hockeyID = self.getHockeyID(meetupID)
            
            # early bird?
            #signupTime = self.gameday[meetupID][self.M_SIGNUPTIME]
            #hoursInAdvance = self.signupTimeCalculation(signupTime)
            #if hoursInAdvance > 12.0:
            if self.isEarlyBird(meetupID, self.date):
                earlyBird = "EarlyBird "
            else:
                earlyBird = "          "

            pc_status, isAlt = self.getPunchcardStatus(hockeyID, punchcards)
            hockeyIDpadded = hockeyID.ljust(16)

            if isAlt == 0:                
                print(pc_status, hockeyID, earlyBird, self.gameday[meetupID][self.M_MEETUPNAME])
            else:
                print(pc_status, hockeyID, earlyBird, self.gameday[meetupID][self.M_MEETUPNAME], "(listed as alternate on punchcard)")

        print()
        return

    #-------------------------------------------------------------------------------    
    def getPunchcardStatus(self, hockey_id, punchcards):
        pc_idx, slot, is_alt = punchcards.getNextFreePaymentSlot(player=hockey_id)
        if slot >= 0:
            return "punchcarder ", is_alt
        pc_idx, slot = punchcards.getNextFreePastDueSlot(player=hockey_id)
        if slot >= 0:
            return "past due    ", is_alt
        return "            ", is_alt

    #-------------------------------------------------------------------------------    
    def getHockeyID(self, meetupID):
        try:
            retval = self.idXref[meetupID]
        except:
            retval = meetupID
        return retval


    def handleAlreadyProcessedError(self):
        print("\nEEEEEEEEEEERRRRRRRRRRRRRRROOOOOOOOOOOOORRRRRRRRRRRRR ERROR ERROR ERROR EEEEEEEEEEEEEERRRRRRRRRRRROOOOOORRRRRRRRRRR\n")            
        print(self.date + " has already been processed.  Have you gone crazy???????\nI'm sorry, but I refuse to have anything to do with this.\n       **** Program aborted! ****")
        print("(If you insist on doing this, you'll need to manually punch each punchcard yourself.)")
        print("\nEEEEEEEEEEERRRRRRRRRRRRRRROOOOOOOOOOOOORRRRRRRRRRRRR ERROR ERROR ERROR EEEEEEEEEEEEEERRRRRRRRRRRROOOOOORRRRRRRRRRR\n")
        print("(If you want to override this safety check, type OVERRIDE and press <enter>)")
        answer = input("Press <enter> to quit ")
        if answer != "OVERRIDE":
            sys.exit(97)

    #-------------------------------------------------------------------------------    
    def analyze(self):
        
        punchcards = CPunchcards.CPunchcards()
        email = CEmail.CEmail()
        roster = CRoster.CRoster()      

        if punchcards.alreadyProcessed(self.date):
            self.handleAlreadyProcessedError()
        
        print(f"UWH Gameday analysis for {self.date}")
        print(f"----------------------------------------")
        
        for meetupID, playerInfo in self.gameday.items():
            self.processPlayer(meetupID, playerInfo, roster, punchcards, email)
            
        print()
        
        punchcards._savePunchcards() 
        roster.saveRoster()      
        return

    #-------------------------------------------------------------------------------           
    def processPlayer(self, meetupID, playerInfo, roster, punchcards, email):

        starcount = 0
        bEarlyBird = False
        gamePaid = False

        hockeyID = self.getHockeyID(meetupID)

        # check if can pay for game using stars
        if self.useStars:
            starcount = roster.getStars(hockeyID)
            if starcount is None:
                starcount = 0
                print()
                print("ERROR reading starcount for ", playerInfo)
            if starcount >= 20:
                emailAddress = roster.getEmail(hockeyID) 
                meetupName = roster.getMeetupName(hockeyID)
                subject, body = email.composeUseStarsForFreeGameEmail(hockeyID, meetupName, self.date)
                email.sendEmail(emailAddress, subject, body)
                starcount -= 20
                roster.setStars(hockeyID, starcount)
                gamePaid = True
            else:
                bEarlyBird = self.isEarlyBird(meetupID, self.date)
                if bEarlyBird and hockeyID in roster.roster:
                    starcount = roster.incrStars(hockeyID)

        # use a punch on their punchcard (they didn't have enough stars yet)
        if not gamePaid:
            self.handlePunchcardPayment(hockeyID, playerInfo, punchcards, roster, email, bEarlyBird, starcount)

    #-------------------------------------------------------------------------------               
    def handlePunchcardPayment(self, hockeyID, playerInfo, punchcards, roster, email, bEarlyBird, starcount):
        pcIdx,slot,isAlt = punchcards.getNextFreePaymentSlot(player=hockeyID)
        paid = False
        if slot >= 0:
            print(hockeyID, playerInfo[self.M_MEETUPNAME], ">>> Payment", slot+1, " (", 10-slot, "left on this card )")
            paid = punchcards.makePaymentBySlot(pcIdx, slot, self.date)
        if paid:
            emailAddress = roster.getEmail(hockeyID) 
            meetupName = roster.getMeetupName(hockeyID)
            subject, body = email.composeUsePunchcardEmail(hockeyID, meetupName, self.date, punchcards.punchcards[pcIdx], slot, bEarlyBird, starcount, 20)
            email.sendEmail(emailAddress, subject, body)
            ccList = self.info.getValue("cc_punchused") 
            for ccEmail in ccList:
                email.sendEmail(ccEmail, "A punch-used email was sent to " + emailAddress, body)  
        else:
            pcIdx,slot = punchcards.getNextFreePastDueSlot(player=hockeyID)
            if pcIdx >= 0 and slot >= 0:
                paid = punchcards.makePaymentBySlot(pcIdx, slot, self.date)
                print(hockeyID, playerInfo[self.M_MEETUPNAME], ">>>", "added to past due account")        

#-------------------------------------------------------------------------------           
if __name__ == "__main__":        
            
     
    print("all done")
