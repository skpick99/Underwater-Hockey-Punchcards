import json
import os
import sys
from utils import *

#-------------------------------------------------------------------------------
class CInfo:
    #-------------------------------------------------------------------------------
    def __init__(self):
        self.path = getHockeyPath()
        self.infoFilename = os.path.join(self.path, "info.json")
        #default values
        self.info = {
            "system_name": "PunchcardSystem",
            "version": "1.0.0",
            "meetup_url": "https://www.meetup.com/*****************/events/",
            "club_email": "***********@gmail.com",
            "admin_contact_info": "************, Email ************@gmail.com, Phone 800-***-****",
            "sendgrid_api_key": "Enter your SendGrid API key here",
            "use_stars": True,
            "cc_purchase": ["*********@gmail.com", "*********@gmail.com"],
            "cc_invite": [],            
            "cc_punchused": [],
            "cc_latenotice": ["*********@gmail.com"],
            #"example_integer": 100,         
            #"example_subvalue": {
            #    "port": 8080,
            #    "protocol": "https",
            #    "timeout_seconds": 30
            #}
        }
        self.loadInfoFile()

    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        # close, deallocate, etc
        pass
    
    #-------------------------------------------------------------------------------
    def loadInfoFile(self):
        """Load the information file if it exists, otherwise create a new one with default values."""
        if os.path.exists(self.infoFilename):
            with open(self.infoFilename, 'r') as file:
                try:
                    self.info = json.load(file)
                except Exception as e:
                    print("\n\nERROR 943: Your info.json file is formatted incorrectly. Did you hand edit it recently?")
                    print(e)
                    sys.exit(94)
                
        else:
            self.saveInfoFile()

    #-------------------------------------------------------------------------------
    def saveInfoFile(self):
        """Save the info data to the JSON file."""
        with open(self.infoFilename, 'w') as file:
            json.dump(self.info, file, indent=4)

    #-------------------------------------------------------------------------------
    def setValue(self, key, value):
        """Update a specific setting in the info file."""
        keys = key.split('.')
        current = self.info
        for k in keys[:-1]:
            current = current.setdefault(k, {})
        current[keys[-1]] = value
        self.saveInfoFile()

    def getAll(self):
        """Get all info key/values pairs."""
        return self.info

    def getValue(self, key):
        """Get a specific setting from the info file."""
        keys = key.split('.')
        current = self.info
        for k in keys:
            current = current.get(k)
            if current is None:
                return None
        return current

# Example usage
if __name__ == "__main__":
    # Load or create the info file
    info = CInfo()
    control_data = info.getAll()
    print("Initial control data:")
    print(json.dumps(control_data, indent=4))

    # Update a setting
    info.setValue("example_subvalue.port", 9090)
    print("\nUpdated example_subvalue port:")
    print(info.getValue("example_subvalue.port"))

    # Get a specific setting
    name = info.getValue("system_name")
    print("\nCurrent system name:", name)

    # add a new setting
    info.setValue("sendgrid_api_key", "")

    # Print the final control data
    print("\nFinal control data:")
    print(json.dumps(info.getAll(), indent=4))
