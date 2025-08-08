import os
import sys
#import sendgrid
#from sendgrid import SendGridAPIClient
#from sendgrid.helpers.mail import Mail
import smtplib
from email.message import EmailMessage
import CPunchcards
from CInfo import CInfo
from utils import *
sys.path.append("\\")

#-------------------------------------------------------------------------------
class CEmail:
    def __init__(self):
        self.path = getHockeyPath()
        self.info = CInfo()
        self.useStars = self.info.getValue("use_stars")
        #self.SENDGRID_API_KEY = self.info.getValue("sendgrid_api_key")
        self.GOOGLE_APP_PASSWORD = self.info.getValue("google_app_password")
        
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        # close, deallocate, etc
        pass
  
    #-------------------------------------------------------------------------------      
    def convertDate(self, dateIn):
        if len(dateIn) > 0:            
            return dateIn[4:6] +"/"+ dateIn[6:8] +"/"+ dateIn[0:4]
        return ""
  
    #-------------------------------------------------------------------------------    
    def readFileToString(self, filename):
        try:
            filepath = os.path.join(self.path, filename)
            with open(filepath, 'r') as file:
                content = file.read()
            return content
        except FileNotFoundError:
            print(f"Error: The file '{filepath}' was not found.")
            return None
        except IOError:
            print(f"Error: There was an issue reading the file '{filepath}'.")
            return None

    #-------------------------------------------------------------------------------    
    def composeUsePunchcardEmail(self, playerID, meetupName, date, pcRow, pcIdx, bEarlyBird, starcount, gameStars):
        
        punchcards = CPunchcards.CPunchcards()
        # Calculate remaining punches using utility function
        punches_used, remaining_slots, total_slots = punchcards.countPunchcardSlots(pcRow)
        remainingPunches = remaining_slots
        boughtNextCard = False
        if remainingPunches <= 2:
            if punchcards.getPunchcardCount(playerID) > 1:
                boughtNextCard = True        
        
        subject = "Underwater Hockey punchcard used on " + self.convertDate(date) + ". You have " + str(remainingPunches) + " punches remaining."
        if remainingPunches == 2 and not boughtNextCard:
            subject = "UWH: Only 2 punches remaining. Information on upgrading enclosed."
        if remainingPunches == 1 and not boughtNextCard:
            subject = "UWH: Only 1 punch left *** Please.Buy.Your.Next.Punchcard.Soon ***"
        if remainingPunches == 0 and not boughtNextCard:
            subject = "UWH: ***** LAST PUNCH USED ***** TIME TO BUY YOUR NEXT PUNCHCARD *****"
            
        body = "Hi " + meetupName + ",\n\n"
        body += "You played Underwater Hockey on " + self.convertDate(date) + ". We hope you enjoyed the game.\n\n"
        if self.useStars:
            if bEarlyBird:
                body += "You signed up by Thursday and earned a star, bringing your current star count to " + str(starcount) + ".\n"
            else:
                body += "FYI, if you know you're playing in advance and sign up by midnight on Thursday, you'll earn a star.\n"
                if starcount > 0:
                    body += "Your current star count is " + str(starcount) + ".\n"
            body += "Collect 20 stars and you'll get a free game of Underwater Hockey.\n\n"

        body += "You used punch number " + str(pcIdx+1) + " on the punchcard you purchased on " + pcRow[punchcards.P_PURCHASEDATE] + "\n"
        if gameStars != 20:
            body += "You were only charged for a partial game. You were credited 10 stars (half of a free game) because we can't do partial punches.\n"
        # Display punch slots, but handle NULL value for new 10-punch cards
        punches_used, remaining_slots, total_slots = punchcards.countPunchcardSlots(pcRow)
        maxSlots = total_slots
        for i in range(maxSlots):
            slotValue = pcRow[punchcards.slotIdx(i)]
            if slotValue == 'NULL':
                # Skip displaying NULL value in emails
                continue
            body += "%10d %s\n" % (i+1, self.convertDate(slotValue))
        body += "You have %d punches remaining." % (remainingPunches)
        
        if remainingPunches > 0 and remainingPunches <= 2 and not boughtNextCard:
            self.readFileToString("email_buysoon.txt")
            
        if remainingPunches == 0:
            if boughtNextCard:
                body += self.readFileToString("email_nobuyrequired.txt")
            else:
                body += self.readFileToString("email_buynow.txt")

        body += "\n\nThanks for being part of our community.  Have a great day.\n"
        return subject,body
    
    #-------------------------------------------------------------------------------    
    def composeUseStarsForFreeGameEmail(self, hockeyID, meetupName, date):

        subject = "You just played a FREE GAME of Underwater Hockey using your Early Signup stars!"
        body = "Hi " + meetupName + ",\n\n"
        body += "You played a FREE game of Underwater Hockey on " + self.convertDate(date) + ".\n\n"
        body += self.readFileToString("email_staruse.txt")
        return subject,body
    
    #-------------------------------------------------------------------------------    
    def composeUseStarsForFreeHalfGameEmail(self, hockeyID, meetupName, date):

        subject = "You just played a FREE HALF GAME of Underwater Hockey using your Early Signup stars!"
        body = "Hi " + meetupName + ",\n\n"
        body += "You played a FREE half game of Underwater Hockey on " + self.convertDate(date) + ".\n\n"
        body += self.readFileToString("email_staruse.txt")
        return subject,body
  
    #-------------------------------------------------------------------------------    
    def composePunchcardPurchaseEmail(self, meetupName, date, remainingPunchcards, bPastDuePunches):
        
        punchcards = CPunchcards.CPunchcards()
        
        subject = "Your new Underwater Hockey punchcard has been activated!"
        body = "Hi " + meetupName + ",\n\n"
        body += self.readFileToString("email_purchase.txt")

        if bPastDuePunches:
            body += "We applied any previously unpaid games to the punchcard and they will appear in your next gameday email .\n"
             
        if len(remainingPunchcards) > 0:
            for slot in range(punchcards.totalSlotCount):
                slotVal = remainingPunchcards[0][punchcards.slotIdx(slot)]
                if not slotVal is None and len(slotVal) == 0:
                    break
            # Calculate remaining slots using utility function
            punches_used, remaining_slots, total_slots = punchcards.countPunchcardSlots(remainingPunchcards[0])
            remainingSlots = remaining_slots
            body += "Your previous punchcard (purchased on " + remainingPunchcards[0][3] + ") has " + str(remainingSlots) + " slots remaining. We will finish it up first so you won't lose any plays.\n"  
        body += "\nThanks for supporting Underwater Hockey.  We'll see you on the bottom.\n"
        return subject,body 
  
    #-------------------------------------------------------------------------------    
    def composeInviteEmail(self):
        
        subject = "Please join the Underwater Hockey punchcard program"
        body = self.readFileToString("email_invite.txt")
        
        return subject,body
  
    #-------------------------------------------------------------------------------    
    def composePastDueEmail(self, playerID, meetupName, playdates):
        
        subject = "TIME TO PURCHASE YOUR NEXT PUNCHCARD"
            
        body = "Hi " + meetupName + ",\n\n"
        body += "Our records show you have not paid for the following hockey games:\n"
        for playdate in playdates:            
            body += "      %s\n" % (self.convertDate(playdate))
        body += "\n"
        body += self.readFileToString("email_pastdue.txt")
        
        return subject,body
 
    #-------------------------------------------------------------------------------    
    def sendInvitationalEmail(self):
        info = CInfo()
        
        print()
        emailAddress = input("Email address ")

        if len(emailAddress) == 0:
            print("Nothing done.\n")
            return

        subject,body = self.composeInviteEmail()
        self.sendEmail(emailAddress, subject, body)
        ccList = info.getValue("cc_invite") 
        for ccEmail in ccList:                
            self.sendEmail(ccEmail, "An invite has been sent to " + name + " at " + emailAddress, body)

    #-------------------------------------------------------------------------------    
    def sendEmail(self, toAddress, subject, message):
  
        # TEMPORARILY DISABLED FOR TESTING
        # Create the email
        #msg = EmailMessage()
        #msg['Subject'] = subject
        #msg['From'] = self.info.getValue("club_email")
        #msg['To'] = toAddress
        #msg.set_content(message)

        #with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        #    smtp.login(self.info.getValue("club_email"), self.GOOGLE_APP_PASSWORD)
        #    smtp.send_message(msg)

        # SENDGRID EMAIL DISCONTINUED
        #mail = Mail(from_email, toAddress, subject, message)
        ##mail_json = mail.get()
        ##try:
        #sg = SendGridAPIClient(self.SENDGRID_API_KEY)
        #response = sg.send(mail)            
        ##response = my_sg.client.mail.send.post(request_body=mail_json)
        #pass
        ##except:
        ##    print("ERROR 959: Email not successfully sent TO", toAddress, "SUBJECT", subject, "TEXT", message)            
        ##    return False
        
        print("-----------------------------------: Email successfully sent TO", toAddress)
        print("SUBJECT", subject)
        print("TEXT", message)
        print("-----------------------------------------------------------------")
        return True

#-------------------------------------------------------------------------------           
if __name__ == "__main__":
     
    emailAddress = "********@gmail.com"

    subject,body = email.composeInviteEmail()

    ccList = info.getValue("cc_invite") 
    for ccEmail in ccList:                
        email.sendEmail(ccEmail, "An invite has been sent to " + emailAddress, body)

    email.sendEmail(emailAddress, subject, body)
    
    print("all done")
