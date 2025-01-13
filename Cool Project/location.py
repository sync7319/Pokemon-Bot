import pyautogui
import time

print("Move your mouse to desired locations. Press 'Ctrl+C' to stop the program.")

try:
    while True:
        x, y = pyautogui.position()  # Get current mouse position
        print(f"X: {x} Y: {y}")  # Print coordinates on a new line
        time.sleep(2)  # Update every 0.1 seconds
except KeyboardInterrupt:
    print("\nProgram terminated.")

