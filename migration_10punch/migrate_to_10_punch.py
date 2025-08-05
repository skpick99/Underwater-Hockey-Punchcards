#!/usr/bin/env python3
"""
Migration script to convert from 11-punch to 10-punch punchcard system.

This script:
1. Identifies empty punchcards (0 punches used) for $10 refund
2. Removes the last punch from all other cards
3. Truncates all cards to 10 slots
4. Generates a refund report
"""

import csv
import os
from datetime import datetime
from utils import getHockeyPath

class PunchcardMigration:
    def __init__(self):
        self.path = getHockeyPath()
        self.punchcardFile = os.path.join(self.path, "punchcards.csv")
        self.backupFile = os.path.join(self.path, f"punchcards_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        
        # Column indices
        self.P_HOCKEYUSERID = 0
        self.P_MEETUPNAME = 1
        self.P_ALTPAYERID = 2
        self.P_ALTPAYERNAME = 3
        self.P_STATUS = 4
        self.P_PURCHASEDATE = 5
        self.firstPaySlot = 6
        self.totalSlotCount = 11
        
        self.punchcards = []
        self.emptyCards = []
        self.refundReport = []
        
    def loadPunchcards(self):
        """Load current punchcards from CSV"""
        print("Loading current punchcards...")
        with open(self.punchcardFile, newline='') as csvfile:
            rows = csv.reader(csvfile, delimiter='\t', quotechar='"')
            header = next(rows)  # Skip header
            for row in rows:
                if len(row) > 0:
                    self.punchcards.append(row)
        print(f"Loaded {len(self.punchcards)} punchcards")
        
    def createBackup(self):
        """Create backup of current punchcards"""
        print(f"Creating backup: {self.backupFile}")
        with open(self.punchcardFile, 'r') as source:
            with open(self.backupFile, 'w') as backup:
                backup.write(source.read())
        print("Backup created successfully")
        
    def countPunchesUsed(self, row):
        """Count how many punches are used in a punchcard row"""
        punches = 0
        for slot in range(self.totalSlotCount):
            slotVal = row[self.firstPaySlot + slot]
            if slotVal and slotVal.strip():  # Non-empty slot
                punches += 1
        return punches
        
    def analyzePunchcards(self):
        """Analyze all punchcards and categorize them"""
        print("\nAnalyzing punchcards...")
        
        for i, row in enumerate(self.punchcards):
            if row[self.P_STATUS] == "curr":  # Only process current cards
                punches = self.countPunchesUsed(row)
                playerName = row[self.P_MEETUPNAME]
                
                if punches == 0:
                    # Empty card - needs $10 refund
                    self.emptyCards.append({
                        'index': i,
                        'player': playerName,
                        'hockey_id': row[self.P_HOCKEYUSERID],
                        'purchase_date': row[self.P_PURCHASEDATE],
                        'punches': punches
                    })
                    print(f"  Empty card: {playerName} (0 punches) - $10 refund needed")
                else:
                    print(f"  Used card: {playerName} ({punches} punches) - remove last punch")
                    
        print(f"\nFound {len(self.emptyCards)} empty cards requiring refunds")
        
    def removeLastPunch(self, row):
        """Remove the last (most recent) punch from a punchcard row"""
        # Find the last non-empty punch slot
        lastPunchSlot = -1
        for slot in range(self.totalSlotCount - 1, -1, -1):  # Start from last slot
            slotVal = row[self.firstPaySlot + slot]
            if slotVal and slotVal.strip():
                lastPunchSlot = slot
                break
                
        if lastPunchSlot >= 0:
            # Clear the last punch
            row[self.firstPaySlot + lastPunchSlot] = ""
            return True
        return False
        
    def truncateTo10Slots(self, row):
        """Truncate a punchcard row to 10 slots (remove PlayDate11)"""
        # Remove the 11th slot (PlayDate11)
        if len(row) > self.firstPaySlot + 10:
            row = row[:self.firstPaySlot + 10] + row[self.firstPaySlot + 11:]
        return row
        
    def migratePunchcards(self):
        """Perform the migration"""
        print("\nStarting migration...")
        
        for i, row in enumerate(self.punchcards):
            if row[self.P_STATUS] == "curr":
                playerName = row[self.P_MEETUPNAME]
                punches = self.countPunchesUsed(row)
                
                if punches == 0:
                    # Empty card - just truncate, no punch removal needed
                    print(f"  Empty card: {playerName} - truncating to 10 slots")
                else:
                    # Used card - remove last punch then truncate
                    print(f"  Used card: {playerName} - removing last punch, then truncating")
                    self.removeLastPunch(row)
                    
                # Truncate to 10 slots for all cards
                self.punchcards[i] = self.truncateTo10Slots(row)
                
        print("Migration completed")
        
    def saveMigratedPunchcards(self):
        """Save the migrated punchcards back to CSV"""
        print("\nSaving migrated punchcards...")
        
        # Create new header with 10 slots instead of 11
        newHeader = ["Hockey User ID", "Meetup name", "Alt ID", "Alt name", "Status", "PurchaseDate"] + \
            [f"PlayDate{str(i).zfill(2)}" for i in range(1, 11)] + ["FollowUp"]
            
        with open(self.punchcardFile, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile, delimiter='\t', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            writer.writerow(newHeader)
            writer.writerows(self.punchcards)
            
        print("Migrated punchcards saved successfully")
        
    def generateRefundReport(self):
        """Generate a refund report for empty cards"""
        print("\nGenerating refund report...")
        
        reportFile = os.path.join(self.path, f"refund_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        
        with open(reportFile, 'w') as f:
            f.write("PUNCHCARD MIGRATION REFUND REPORT\n")
            f.write("=" * 50 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total empty cards requiring refunds: {len(self.emptyCards)}\n")
            f.write(f"Total refund amount: ${len(self.emptyCards) * 10}\n\n")
            
            f.write("REFUND LIST:\n")
            f.write("-" * 30 + "\n")
            
            for i, card in enumerate(self.emptyCards, 1):
                f.write(f"{i}. {card['player']}\n")
                f.write(f"   Hockey ID: {card['hockey_id']}\n")
                f.write(f"   Purchase Date: {card['purchase_date']}\n")
                f.write(f"   Refund Amount: $10\n")
                f.write(f"   Reason: Empty punchcard (0 punches used)\n")
                f.write("\n")
                
            f.write("\nREFUND INSTRUCTIONS:\n")
            f.write("-" * 30 + "\n")
            f.write("1. Send $10 refund to each player listed above\n")
            f.write("2. Use Venmo (@James-Melrod) or Zelle (jimmymelrod@gmail.com)\n")
            f.write("3. Include note: 'Punchcard system migration refund'\n")
            f.write("4. Mark each refund as completed in this report\n\n")
            
            f.write("MIGRATION SUMMARY:\n")
            f.write("-" * 30 + "\n")
            f.write("- Converted from 11-punch to 10-punch system\n")
            f.write("- Empty cards: $10 refund each\n")
            f.write("- Used cards: Removed last punch, no refund\n")
            f.write("- All cards truncated to 10 slots\n")
            
        print(f"Refund report saved: {reportFile}")
        return reportFile
        
    def runMigration(self):
        """Run the complete migration process"""
        print("PUNCHCARD MIGRATION: 11-PUNCH TO 10-PUNCH")
        print("=" * 50)
        
        # Step 1: Load current data
        self.loadPunchcards()
        
        # Step 2: Create backup
        self.createBackup()
        
        # Step 3: Analyze current state
        self.analyzePunchcards()
        
        # Step 4: Perform migration
        self.migratePunchcards()
        
        # Step 5: Save migrated data
        self.saveMigratedPunchcards()
        
        # Step 6: Generate refund report
        reportFile = self.generateRefundReport()
        
        print("\n" + "=" * 50)
        print("MIGRATION COMPLETED SUCCESSFULLY!")
        print(f"Backup saved: {self.backupFile}")
        print(f"Refund report: {reportFile}")
        print(f"Empty cards requiring refunds: {len(self.emptyCards)}")
        print(f"Total refund amount: ${len(self.emptyCards) * 10}")
        print("=" * 50)

if __name__ == "__main__":
    migration = PunchcardMigration()
    migration.runMigration() 