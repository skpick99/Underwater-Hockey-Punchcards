import subprocess
import time
import pyautogui

while False:
    print(pyautogui.position())


# Launch the batch file
subprocess.Popen(r"ChromHockey.bat", shell=True)

# Wait 5 seconds
time.sleep(10)

# Send Alt+Space, then X
pyautogui.hotkey("alt", "space")
time.sleep(1)
pyautogui.press("x")

time.sleep(5)
pyautogui.moveTo(2000, 1575, duration=0.5)
pyautogui.click()

time.sleep(10)
pyautogui.moveTo(2700, 1080, duration=0.5)
pyautogui.click()

time.sleep(1)
pyautogui.moveTo(2600, 1210, duration=0.5)
pyautogui.click()

time.sleep(10)
pyautogui.moveTo(2350, 750, duration=0.5)
pyautogui.click()

time.sleep(5)
pyautogui.moveTo(1700, 1210, duration=0.5)
pyautogui.click()

time.sleep(15)

# Send Alt+Space, then X
pyautogui.hotkey("alt", "F4")
time.sleep(1)

print("all done")