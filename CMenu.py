import datetime
from CGameDay import CGameDay
from CPunchcards import CPunchcards
from CRoster import CRoster
from CEmail import CEmail
from utils import *
from readAttendees import *

#-------------------------------------------------------------------------------
class CMenu:
    #-------------------------------------------------------------------------------
    def __init__(self):
        self.path = getHockeyPath()
        self.gamedate = datetime.datetime.now()
        
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        # close, deallocate, etc
        pass
    
    #-------------------------------------------------------------------------------               
    def getMenuChoice(self):
        print()
        print()
        print()
        print("Game date: ", self.gamedate.strftime('%A %Y%m%d'))
        print()
        print("0. Change game date")
        print("   '-' to decrease, '+' to increase")
        print("1. Instructions")
        #print("1. Download list of attendees from last practice")        
        print("2. Display download")
        print("3. Charge punchcards for current game")
        print("4. Manual punch")
        print("H. Manual half punch")
        print("5. Invitation email to new player")
        print("6. Add new player from current game")
        print("7. Display player information")
        print("8. Punchcard purchase")
        print("9. Send past-due notices")
        print("A. Prepaid counts")
        print()
        choice = input("Enter selection (or <enter> to quit) ")
        return choice

    #-------------------------------------------------------------------------------               
    def doMenu(self):
        choice = "1"
        while len(choice) > 0:
            
            choice = self.getMenuChoice()
            
            # move game date back one day   
            if choice == "-":    
                self.gamedate -= datetime.timedelta(days=1)
             
            # move game date forward one day                
            elif choice == "+":    
                self.gamedate += datetime.timedelta(days=1)

            # remind them to use +/- to adjust game date
            elif choice == "0":   
                print()
                print()
                print("Tricked you. There is not really a '0' menu item. It's just a reminder to adjust the game date using the plus and minus keys.")
                print("Press <enter> to continue")
                print()
                _ = input("")

            # deprecated (temporarily?) --> download list of attendees from last practice
            # instructions
            elif choice == "1":
                #downloadLastPracticeAttendees(self.gamedate.strftime('%Y%m%d'))
                for i in range(7):
                    print()
                print("First step: Download the latest hockey game to your normal Download directory.")
                print("Second step: Rename the file to the date of the game, for example 20260110.csv")
                print("Third step: Use the +/- keys to set the date to the date of the game. (Nothing required if you're going it on gameday.)") 
                print("Fourth step: Choose menu item 2 to view the download and make sure the players are correct.")
                print("Fifth step: Choose menu item 3 to charge everyone's punchcards and send the emails.")
                print("Sixth step: Use menu item 4 to charge players who played without signing up on Meetup (if necessary)")
                print()
                print()
                print("Press <enter> to return to the main menu")
                for i in range(7):
                    print()
                _ = input("")
            
            # display list of attendees from last practice
            elif choice == "2":
                g = CGameDay(self.gamedate.strftime('%Y%m%d'))
                if g.isValid():                    
                    g.printGameDay()  
            
            # charge punchcards for current game
            elif choice == "3":
                g = CGameDay(self.gamedate.strftime('%Y%m%d'))
                if g.isValid():   
                    g.analyze()   
                    
            # charge punchcards for current game
            elif choice == "4":
                pc = CPunchcards()
                pc.manualPunch(self.gamedate.strftime('%Y%m%d'), 20)

            # charge half of a punch for current game
            elif choice.upper() == "H":
                pc = CPunchcards()
                pc.manualPunch(self.gamedate.strftime('%Y%m%d'), 10)                

            # send invitational email to new player
            elif choice == "5":
                email = CEmail()
                email.sendInvitationalEmail()

            # Add new player from current game                    
            elif choice == "6":                    
                g = CGameDay(self.gamedate.strftime('%Y%m%d'))
                if g.isValid():
                    g.addPlayerToRoster()

            # display player information
            elif choice == "7":
                    r = CRoster()
                    r.printRoster()                    
                    playerRec = r.getPlayerName()
                    if not playerRec is None:        
                        print("Player record: ", playerRec)
                        
            # purchase punchcard
            elif choice == "8":
                pc = CPunchcards()
                pc.addPunchcards()
                pc._savePunchcards()    
            
            # send pastdue notices
            elif choice == "9":
                pc = CPunchcards()
                pc.sendPastDueNotices()      

            # purchase punchcard
            elif choice == "A" or choice == "a":
                pc = CPunchcards()   
                pc.countGamesPlayedInYear()       
                x = pc.countPrepaymentPunches()
                print()
                print(x, "prepaid, but not yet used, punches.  Total value (at $9.00 each) is   $", x*9)
                print()
    
        return              
            
#-------------------------------------------------------------------------------           
if __name__ == "__main__":    
    
    menu = CMenu()
    menu.doMenu() 
    print("all done")
