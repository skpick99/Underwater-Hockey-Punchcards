import os
import sys
import csv
from datetime import datetime
import CRoster
import CEmail
from CInfo import CInfo
from utils import *
sys.path.append("\\")

VALID_STATUSES = {"curr", "next", "prev", "pastdue", "REFUNDED"}

#-------------------------------------------------------------------------------
class CPunchcards:
    def __init__(self):
        self.path = getHockeyPath()
        self.P_HOCKEYUSERID = 0
        self.P_MEETUPNAME = 1
        self.P_ALTPAYERID = 2        
        self.P_STATUS = 4
        self.P_PURCHASEDATE = 5
        self.firstPaySlot = 6
        self.totalSlotCount = 11     
        self.info = CInfo()
        self.useStars = self.info.getValue("use_stars")
        self.punchcards = []
        self.punchcards = self.loadPunchcards()
        self.punchcardFileHeader = ["Hockey User ID", "Meetup name", "Alt ID", "Alt name", "Status", "PurchaseDate"] + \
            [f"PlayDate{str(i).zfill(2)}" for i in range(1, self.totalSlotCount + 1)]
        
        # Calculate column indices dynamically
        self._calculateColumnIndices()   
        
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        # close, deallocate, etc
        pass
    
    #-------------------------------------------------------------------------------
    def _calculateColumnIndices(self):
        """Calculate column indices dynamically from the header"""
        self.PLAY_DATE_INDICES = {}
        
        for i, header in enumerate(self.punchcardFileHeader):
            if header.startswith("PlayDate"):
                # Extract the number from PlayDateXX (e.g., "PlayDate01" -> 1)
                # Find where "PlayDate" ends and extract the number
                playdate_prefix = "PlayDate"
                if header.startswith(playdate_prefix):
                    num_str = header[len(playdate_prefix):]  # Get everything after "PlayDate"
                    num = int(num_str)  # This will handle "01", "02", etc.
                    self.PLAY_DATE_INDICES[num] = i
        
        # Verify we have all expected indices
        if len(self.PLAY_DATE_INDICES) != self.totalSlotCount:
            raise ValueError(f"Expected {self.totalSlotCount} PlayDate columns, found {len(self.PLAY_DATE_INDICES)}")
    
    #-------------------------------------------------------------------------------    
    def loadPunchcards(self, includeHistory = False):
        
        punchcardList = []
        filepaths = [os.path.join(self.path, "punchcards.csv")]
        if includeHistory:
            filepaths.append(os.path.join(self.path, "punchcards_history.csv"))
        for filepath in filepaths:
            with open(filepath, newline='') as csvfile:
                rows = csv.reader(csvfile, delimiter='\t', quotechar='"')
                next(rows)
                for row in rows:
                    if len(row) > 0:
                        if row[self.P_STATUS] not in VALID_STATUSES:
                            print("ERROR 636: Card status must be 'curr', 'next', or 'prev' or 'pastdue' (not '" + row[self.P_STATUS] + "')")
                            print(row)                      
                        punchcardList.append(row)
        return punchcardList
    
    #-------------------------------------------------------------------------------    
    def _savePunchcards(self):

        self.validatePunchcards() 
        filepath = os.path.join(self.path, "punchcards.csv")
        with open(filepath, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile, delimiter='\t', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            writer.writerow(self.punchcardFileHeader)
            writer.writerows(self.punchcards)      
        return   
    
    def createEmptyRow(self):
        return [''] * len(self.punchcardFileHeader)
            
    #-------------------------------------------------------------------------------    
    def alreadyProcessed(self, date):
        
        # check for invalid calling parameters
        if len(date) == 0:
            print("Call to CPunchcards.alreadyProcessed is missing the date parameter")
            return False
        
        # check if any punchcard has already been charged for this date
        for row in self.punchcards:
            for slot in range(self.totalSlotCount):
                slotVal = row[self.slotIdx(slot)]
                if not slotVal is None and slotVal == date:
                    return True
        return False            
    
    #-------------------------------------------------------------------------------    
    def printPunchcards(self, player='', status=''):
        
        print("Underwater Hockey Open Punchcards")
        print("----------------------------------")
        pc = self.getPunchcards(player, status)
        for row in pc:
            print(' '.join(row[:len(self.punchcardFileHeader)]))
        print("")
        return

    #-------------------------------------------------------------------------------    
    def getPunchcards(self, player='', status=''):

        retList = []        
        for row in self.punchcards:
            requested = True
            if len(player) > 0 and row[self.P_HOCKEYUSERID] != player:
                requested = False
            if len(status) > 0 and row[self.P_STATUS] != status:
                requested = False
            if requested:
                retList.append(row)                
        return retList

    #-------------------------------------------------------------------------------    
    def slotIdx(self, idx):
        return self.firstPaySlot + idx

    #-------------------------------------------------------------------------------
    def countPunchcardSlots(self, pcRow):
        """Count punches used and remaining slots in a punchcard row
        
        Returns:
            tuple: (punches_used, remaining_slots, total_slots)
        """
        if pcRow is None:
            return 0, 0, 0
            
        punches_used = 0
        remaining_slots = 0
        
        # Check if PlayDate11 slot has NULL value to determine card type
        playdate11_value = pcRow[self.PLAY_DATE_INDICES[11]] if len(pcRow) > self.PLAY_DATE_INDICES[11] else ''
        is_new_10_punch = playdate11_value == 'NULL'
        
        # For new 10-punch cards, only count first 10 slots
        # For old 11-punch cards, count all 11 slots
        max_slots = self.totalSlotCount - 1 if is_new_10_punch else self.totalSlotCount
        total_slots = max_slots
        
        # Count punches used (non-empty values) and remaining slots
        for slot_num in range(1, max_slots + 1):
            if slot_num in self.PLAY_DATE_INDICES:
                slot_value = pcRow[self.PLAY_DATE_INDICES[slot_num]]
                if slot_value and slot_value != 'NULL':
                    punches_used += 1
                else:
                    remaining_slots += 1
        
        return punches_used, remaining_slots, total_slots



    #-------------------------------------------------------------------------------    
    def getPaymentCard(self, player=''):
        
        if len(player) == 0:
            print ("ERROR 427: getPaymentCard called with invalid player (" +player+ ")")
            return -1
        
        # find punchcard for this player
        for rowidx,row in enumerate(self.punchcards):
            if row[self.P_HOCKEYUSERID] == player and row[self.P_STATUS] == "curr":
                return rowidx, 0
            
        #find punchcard where this player is listed as an alternate
        for rowidx,row in enumerate(self.punchcards):
            if row[self.P_ALTPAYERID] == player and row[self.P_STATUS] == "curr":
                return rowidx, 1         

        # slot not found
        return -1, 0

    #-------------------------------------------------------------------------------    
    def getPastDueCard(self, player=''):
        
        if len(player) == 0:
            print ("ERROR 429: getPastDueCard called with invalid player (" +player+ ")")
            return -1
        
        for rowidx,row in enumerate(self.punchcards):
            if row[self.P_HOCKEYUSERID] == player and row[self.P_STATUS] == "pastdue":
                return rowidx

        # slot not found
        return -1

    #-------------------------------------------------------------------------------
    # find next past due for this player. If no past due record, add it.
    # returns punchcardIdx, slot
    def getNextFreePastDueSlot(self, player=''):
        
        # find player's past due punchcard
        pcIdx = self.getPastDueCard(player)
        
        # if no past due card found, add it
        if pcIdx == -1:
            # add past due card for this player
            roster = CRoster.CRoster()
            meetupName = roster.getMeetupName(player)
            if len(meetupName) == 0:
                print("ERROR 530: The following player is not yet in our Roster. No tracking of past due play.")
                return -1,-1
            
            newrow = self.createEmptyRow()
            newrow[self.P_HOCKEYUSERID] = player
            newrow[self.P_MEETUPNAME] = roster.getMeetupName(player)
            newrow[self.P_STATUS] = "pastdue"
            # New cards (including past due) are 10-punch cards with NULL value in PlayDate11 slot
            newrow[self.PLAY_DATE_INDICES[11]] = 'NULL'  # Put NULL in PlayDate11 slot
            self.punchcards.append(newrow)
            
        # get player's past due card, which should always exist at this point.  (If not, it would have been added above.)
        pcIdx = self.getPastDueCard(player)
        if pcIdx == -1:
            print("ERROR 532: Programming error in getNextFreePastDueSlot. Past due punchcard should have been added, but wasn't")
            return -1,-1
        
        # find the first unused slot on the past due punchcard
        row = self.punchcards[pcIdx]                
        for slot in range(self.totalSlotCount):
            if len(row[self.slotIdx(slot)]) == 0:
                return pcIdx, slot

        # no past due slot found
        return -1, -1

    #-------------------------------------------------------------------------------
    # find next available punch for this player
    # returns punchcardIdx, slot
    def getNextFreePaymentSlot(self, player=''):
        
        # find player's current punchcard
        pcIdx, isAlt = self.getPaymentCard(player)
        if pcIdx == -1:
            return -1, -1, 0
        
        # find the first unused punch on the punchcard
        row = self.punchcards[pcIdx]
        
        # Use utility function to determine max slots based on card type
        punches_used, remaining_slots, total_slots = self.countPunchcardSlots(row)
        maxSlot = total_slots
        
        for slot in range(maxSlot):
            if len(row[self.slotIdx(slot)]) == 0:
                return pcIdx, slot, isAlt

        # no payment slot found
        return -1, -1, 0

    #-------------------------------------------------------------------------------    
    def makePaymentBySlot(self, pcIdx=-1, slot=-1, date=''):
        
        if len(date) == 0:
            print ("ERROR 214: makePayment called without a date specified")
            return False
        
        if pcIdx == -1 or slot < 0 or slot >= self.totalSlotCount:
            print ("ERROR 237: makePayment called with invalid punchcardIdx (" +pcIdx+ ") or slot number (" +str(slot)+ ")")
            return False
        
        self.punchcards[pcIdx][self.slotIdx(slot)] = date
        
        # Determine when to change status to "prev"
        # Use utility function to determine final slot based on card type
        row = self.punchcards[pcIdx]
        punches_used, remaining_slots, total_slots = self.countPunchcardSlots(row)
        
        # Check if this is a new 10-punch card by looking at PlayDate11 slot
        playdate11_value = row[self.PLAY_DATE_INDICES[11]] if len(row) > self.PLAY_DATE_INDICES[11] else ''
        isNewCard = playdate11_value == 'NULL'
        
        # For new 10-punch cards: after 10th punch (slot 9)
        # For old 11-punch cards: after 11th punch (slot 10)
        finalSlot = total_slots - 2 if isNewCard else total_slots - 1  # 0-based indexing
        
        if slot == finalSlot and self.punchcards[pcIdx][self.P_STATUS] == "curr":
            self.punchcards[pcIdx][self.P_STATUS] = "prev"
        return True
    
    #-------------------------------------------------------------------------------    
    def getPunchcardCount(self, player=''):
        
        count = 0
        for rowidx,row in enumerate(self.punchcards):
            if ((player == row[self.P_HOCKEYUSERID] or player == row[self.P_ALTPAYERID]) and 
                (row[self.P_STATUS] == "curr" or row[self.P_STATUS] == "next")):
                count += 1
        return count
    
    #-------------------------------------------------------------------------------    
    def makePayment(self, player='', date=''):
        
        if len(date) == 0:
            print ("ERROR 322: makePayment called without a date specified")
            return -1,-1
        
        pcIdx,slot,isAlt = self.getNextFreePaymentSlot(player)
        if slot != -1:
            retval = self.makePaymentBySlot(pcIdx, slot, date)
            if retval is False:
                return -1,-1
            
        return pcIdx, slot
 
    #-------------------------------------------------------------------------------    
    def addPunchcards(self):
        
        roster = CRoster.CRoster()
        email = CEmail.CEmail()
        
        print()
        print()
        print("Punchcard Purchase")
        
        playerRecord = roster.getPlayerName()
        if playerRecord is None:
            print("exiting Punchcard Purchase ...")
            return
        
        playerHockeyID = playerRecord[roster.R_HOCKEYUSERID]            
        playerMeetupName = playerRecord[roster.R_MEETUPNAME]
        playerEmail = playerRecord[roster.R_EMAIL]
        currentDate = datetime.today().strftime('%m/%d/%Y')
        remainingPunchcards = self.getPunchcards(player=playerHockeyID, status="curr")
        
        if len(playerEmail) == 0:
            print("\nEEEEEEEEEEERRRRRRRRRRRRRRROOOOOOOOOOOOORRRRRRRRRRRRR ERROR ERROR ERROR EEEEEEEEEEEEEERRRRRRRRRRRROOOOOORRRRRRRRRRR\n")            
            print("We cannot add a punchcard to a player who doesn't have a valid email address in roster.csv")
            print("\nEEEEEEEEEEERRRRRRRRRRRRRRROOOOOOOOOOOOORRRRRRRRRRRRR ERROR ERROR ERROR EEEEEEEEEEEEEERRRRRRRRRRRROOOOOORRRRRRRRRRR\n")
            input("Press enter to continue ...")
            return
        
        # if past due card found, make it a current card by (1) change 'pastdue' to 'curr, and (2) set the purchase date
        pcPastDueIdx = self.getPastDueCard(playerHockeyID)
        if pcPastDueIdx >= 0:
            # inform the purchaser and the club treasurer we added a punchcard
            subject, body = email.composePunchcardPurchaseEmail(playerMeetupName, currentDate, remainingPunchcards, True)        
            email.sendEmail(playerEmail, subject, body)
            ccList = self.info.getValue("cc_purchase") 
            for ccEmail in ccList:
                email.sendEmail(ccEmail, "A punchcard has been activated for " + playerMeetupName, body)                

            self.punchcards[pcPastDueIdx][self.P_STATUS] = 'curr'
            self.punchcards[pcPastDueIdx][self.P_PURCHASEDATE] = currentDate          

        # otherwise, do a normal addition of newly purchased punchcard
        else:
            # inform the purchaser and the club treasurer we added a punchcard
            subject, body = email.composePunchcardPurchaseEmail(playerMeetupName, currentDate, remainingPunchcards, False)        
            ccList = self.info.getValue("cc_purchase") 
            for ccEmail in ccList:                
                email.sendEmail(ccEmail, "A punchcard has been activated for " + playerMeetupName, body)
            email.sendEmail(playerEmail, subject, body)                    
            
            # add the punchcard
            # New cards are 10-punch cards with NULL value in PlayDate11 slot
            newPunchcard = self.createEmptyRow()
            newPunchcard[self.P_HOCKEYUSERID] = playerHockeyID
            newPunchcard[self.P_MEETUPNAME] = playerMeetupName
            newPunchcard[self.P_STATUS] = "curr"
            newPunchcard[self.P_PURCHASEDATE] = currentDate
            newPunchcard[self.PLAY_DATE_INDICES[11]] = 'NULL'  # Put NULL in PlayDate11 slot
            self.punchcards.append(newPunchcard)            
        return
    
    #-------------------------------------------------------------------------------    
    def validatePunchcards(self):

        self.punchcards = sorted(self.punchcards, key=lambda x: x[self.P_MEETUPNAME].upper())
        playerList = list(set(row[self.P_HOCKEYUSERID] for row in self.punchcards))
        for player in playerList:
            self.validatePlayer(player)

    #-------------------------------------------------------------------------------    
    def validatePlayer(self, player=''):
        
        roster = CRoster.CRoster()
        
        currCount = 0
        meetupName = roster.getMeetupName(player)
        if len(meetupName) == 0:
            print("ERROR - Invalid Hockey ID =", player)
            print("ERROR - Invalid Hockey ID =", player)
            print("ERROR - Invalid Hockey ID =", player)   
            val = 'a'
            while val.upper() != "X":
                val = input("Press X to continue")

        for rowidx,row in enumerate(self.punchcards):
            
            # punchcard for this player
            if row[self.P_HOCKEYUSERID] == player:
                
                # check if meetup name is missing
                if len(row[self.P_MEETUPNAME]) == 0:
                    row[self.P_MEETUPNAME] = meetupName
                
                # check if any money left on this card
                emptySlotFound = False
                if row[self.P_STATUS] == "curr" or row[self.P_STATUS] == "next":               
                    for idx in range(self.totalSlotCount):
                        if len(row[self.slotIdx(idx)]) == 0:
                            emptySlotFound = True
                    if not emptySlotFound:
                        row[self.P_STATUS] = "prev"
                    else:
                        if currCount == 0:
                            row[self.P_STATUS] = "curr"
                            currCount += 1
                        else:
                            row[self.P_STATUS] = "next"   

                # check if any money left on this card                            
    
    #-------------------------------------------------------------------------------    
    def manualPunch(self, punchDate, gameStars = 20):       # gameStars: 20=full punch, 10=half punch
        
        email = CEmail.CEmail()
        roster = CRoster.CRoster()  

        if gameStars == 20:
            print("\n\nManual Punch")
        else:
            print("\n\nManual HALF of a Punch")
        
        while True:

            playerRecord = roster.getPlayerName()
            if playerRecord is None:
                print("exiting Manual Punch ...")
                return False
            
            playerMeetupName = playerRecord[roster.R_MEETUPNAME]
            playerHockeyID = playerRecord[roster.R_HOCKEYUSERID]
            playerEmail = playerRecord[roster.R_EMAIL]     

            starcount = 0
            bEarlyBird = False
            gamePaid = False

            # check if can pay for game using stars
            if self.useStars:        
                starcount = roster.getStars(playerHockeyID)
                if starcount is None:
                    starcount = 0
                    print("\nERROR reading starcount in CPunchcards for ", playerMeetupName)
                if starcount >= gameStars:
                    emailAddress = roster.getEmail(playerHockeyID) 
                    meetupName = roster.getMeetupName(playerHockeyID)
                    if gameStars == 20:
                        subject, body = email.composeUseStarsForFreeGameEmail(playerHockeyID, meetupName, punchDate)
                    else:
                        subject, body = email.composeUseStarsForFreeHalfGameEmail(playerHockeyID, meetupName, punchDate)
                    email.sendEmail(emailAddress, subject, body)
                    starcount -= gameStars
                    roster.setStars(playerHockeyID, starcount)
                    gamePaid = True

            # use a punch on their punchcard (they didn't have enough stars yet)                
            if not gamePaid:        
                pcIdx,slot,isAlt = self.getNextFreePaymentSlot(player=playerHockeyID)
                paid = False
                if slot >= 0:
                    # Calculate remaining punches using utility function
                    punches_used, remaining_slots, total_slots = self.countPunchcardSlots(self.punchcards[pcIdx])
                    remainingPunches = remaining_slots
                    print(f"{playerHockeyID} {playerMeetupName} >>> Payment {slot+1} ({remainingPunches} left on this card)")
                    paid = self.makePayment(player=playerHockeyID, date=punchDate)
                    # when only charging a half-game (10 stars), charge them a punch then give them 10 stars so only charging them half a game
                    if gameStars != 20:
                        starcount = roster.getStars(playerHockeyID)
                        if starcount is None:
                            starcount = 0
                            print("\nERROR2 reading starcount in CPunchcards for ", playerMeetupName)
                        starcount += 20 - gameStars
                        roster.setStars(playerHockeyID, starcount)
                if paid:
                    subject, body = email.composeUsePunchcardEmail(playerHockeyID, playerMeetupName, punchDate, self.punchcards[pcIdx], slot, False, starcount, gameStars)
                    email.sendEmail(playerEmail, subject, body)   
                    ccList = self.info.getValue("cc_punchused") 
                    for ccEmail in ccList:
                        email.sendEmail(ccEmail, f"A manual punch-used email was sent to {playerEmail}", body)
                    print(f"{playerHockeyID} {playerMeetupName} >>> email confirmation sent\n")
                else:
                    pcIdx,slot = self.getNextFreePastDueSlot(player=playerHockeyID)
                    if pcIdx >= 0 and slot >= 0:
                        paid = self.makePaymentBySlot(pcIdx, slot, punchDate)
                        print(f"{playerHockeyID} {playerMeetupName} >>> added to past due account")

            self._savePunchcards() 
            roster.saveRoster()
    
    #-------------------------------------------------------------------------------    
    def _loadPastDuePunchcards(self):
        
        self.pastDuePunchcards = []
        filepath = os.path.join(self.path, "punchcards.csv")
        with open(filepath, newline='') as csvfile:
            rows = csv.reader(csvfile, delimiter='\t', quotechar='"')
            next(rows)
            for row in rows:
                if len(row) > 0:
                    if row[self.P_STATUS] == "pastdue":                    
                        self.pastDuePunchcards.append(row)
        return    
    
    #-------------------------------------------------------------------------------    
    def sendPastDueNotices(self):
        
        roster = CRoster.CRoster()
        email = CEmail.CEmail()     

        self._loadPastDuePunchcards()
        for row in self.pastDuePunchcards:
            print(row)
            if input("Send out this past due notice? (y/n) ").strip().upper() == "Y":                             
                this_player = row[self.P_HOCKEYUSERID]
                emailAddress = roster.getEmail(this_player) 
                meetupName = roster.getMeetupName(this_player)
                playdates = []
                for i in range(self.totalSlotCount):
                    if len(row[self.slotIdx(i)]) > 0:
                        playdates.append(row[self.slotIdx(i)])
                subject, body = email.composePastDueEmail(this_player, meetupName, playdates)
                email.sendEmail(emailAddress, subject, body)    
                ccList = self.info.getValue("cc_latenotice") 
                for ccEmail in ccList:
                    email.sendEmail(ccEmail, "A past due email was sent to " + emailAddress, body)                  
            else:
                print("Nothing done")

    #-------------------------------------------------------------------------------    
    def errorCheck(self):
        # this routine checks if anyone has been charged multiple punches on the same date.
        # this happened to Mike Sick and Aniket during a period when I was manually entering punches due to a site breakage on Meetup.
        # it occurs naturally sometimes, e.g. Paden/Denise and Brian/daughter and Omri's final half-punchcard
        
        filepath = os.path.join(self.path, "punchcards.csv")
        with open(filepath, newline='') as csvfile:
            rows = csv.reader(csvfile, delimiter='\t', quotechar='"')
            for row in rows:
                prev_row = "!@#$"
                for i in range(self.totalSlotCount):
                    if len(row[self.slotIdx(i)]) > 0 and prev_row == row[self.slotIdx(i)]:
                        print("Duplicate: ", prev_row, row)
                    prev_row = row[self.slotIdx(i)]                                
        return
    
    #-------------------------------------------------------------------------------
    # find next available punch for this player
    # returns punchcardIdx, slot
    def countPrepaymentPunches(self):
        
        count = 0
        for rowidx,row in enumerate(self.punchcards):
            if row[self.P_STATUS] == "curr" or row[self.P_STATUS] == "next":
                for slot in range(self.totalSlotCount):
                    if len(row[self.slotIdx(slot)]) == 0:
                        count += 1

        return count
    
    #-------------------------------------------------------------------------------
    # count historical punches used for each player in a given period of time
    def countPunchesUsed(self, historicPunchcards, startdate, enddate):  
        playerCountDict = {}
        dates = set()
        
        for row in historicPunchcards:
            
            playerID   = row[self.P_HOCKEYUSERID]
            playerName = row[self.P_MEETUPNAME]
            
            # find the first unused punch on the punchcard
            for slot in range(self.totalSlotCount):
                val = row[self.slotIdx(slot)]
                if len(val) > 0 and startdate <= val <= enddate:
                    dates.add(val)
                    if not playerID in playerCountDict:
                        playerCountDict[playerID] = {'name': playerName, 'count': 0}                        
                    playerCountDict[playerID]['count'] += 1
                    
        return playerCountDict, len(dates)          

    #-------------------------------------------------------------------------------
    # count historical punches used for each player in a given period of time
    def countGamesPlayedInYear(self):          
        startdate = '20240101'
        enddate = '20241231'
        historicPunchcards = self.loadPunchcards(includeHistory=True)
        playerCountDict, totalGameCount = self.countPunchesUsed(historicPunchcards, startdate, enddate)
        sortedPlayerCountsDict = dict(sorted(playerCountDict.items(), key=lambda item: item[1]['count'], reverse=True))
        print(f"\nTotal games played between {startdate} and {enddate} is {totalGameCount}")
        for x in sortedPlayerCountsDict:
            print(sortedPlayerCountsDict[x]['name'], sortedPlayerCountsDict[x]['count'])        
            
#-------------------------------------------------------------------------------           
if __name__ == "__main__":        
    
    pc = CPunchcards()
    
    pc.countGamesPlayedInYear()   
    
    x = pc.countPrepaymentPunches()
    print()
    print(x, "prepaid, but not yet used, punches.  Total value (at $9.00 each) is   $", x*9)
    print()
    
    print("all done")
