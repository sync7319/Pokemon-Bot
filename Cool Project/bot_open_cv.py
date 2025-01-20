import os, sys, threading, time
from concurrent.futures import ThreadPoolExecutor

import keyboard
import pyautogui
import cv2
import mss
import numpy as np

# Screen regions for different game elements
POKEMON_REGION = (1129, 424, 1360, 616)
VS_REGION = (1088, 295, 1156, 352)
GENERAL_REGION = (705, 705, 1313, 863)
DISCONNECTED_REGION = (665, 706, 917, 756)
CONNECT_REGION = (862, 814, 1131, 893)

# Load Pokémon and party member images from respective folders
pokemon_images_folder = "pokemon_images"
alive_party_members_folder = "alive_party_members"

pokemon_images = [
    os.path.join(pokemon_images_folder, f)
    for f in os.listdir(pokemon_images_folder) if f.endswith(".png")
]
alive_party_members = [
    os.path.join(alive_party_members_folder, f)
    for f in os.listdir(alive_party_members_folder) if f.endswith(".png")
]

# This event is used to gracefully stop all threads
kill_event = threading.Event()

# Master "active" flag for pause/unpause
active = True

# SCREEN CAPTURE & TEMPLATE MATCH
def capture_region(region):
    # Captures a specific screen region and returns it as a numpy array.
    x, y, w, h = region
    with mss.mss() as sct:
        mon = {"top": y, "left": x, "width": w, "height": h}
        img = np.array(sct.grab(mon), dtype=np.uint8)
    return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

def match_template(region, tpl_path, thresh=0.7, gray=True):
    # Matches a template image within a screen region and returns match status and coordinates.
    if not os.path.isfile(tpl_path):
        return (False, None)

    scr = capture_region(region)
    tpl = cv2.imread(tpl_path, cv2.IMREAD_COLOR)
    if scr is None or tpl is None:
        return (False, None)

    if gray:
        scr = cv2.cvtColor(scr, cv2.COLOR_BGR2GRAY)
        tpl = cv2.cvtColor(tpl, cv2.COLOR_BGR2GRAY)

    res = cv2.matchTemplate(scr, tpl, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(res)
    if max_val >= thresh:
        h, w = tpl.shape[:2]
        cx = max_loc[0] + w // 2
        cy = max_loc[1] + h // 2
        return (True, (region[0] + cx, region[1] + cy))

    return (False, None)

# THREADS & LOGIC
def spam_a_and_d(kill_event):
    # Continuously spams 'A' and 'D' keys unless paused or killed.
    global active
    while not kill_event.is_set():
        if not active:
            time.sleep(0.1)
            continue

        keyboard.press("a")
        time.sleep(0.5)
        keyboard.release("a")

        time.sleep(0.05)

        if not active:
            continue

        keyboard.press("d")
        time.sleep(0.52)
        keyboard.release("d")

def detect_vs_menu():
    # Detects the presence of the VS menu on the screen.
    global active
    if not active:
        return False
    f, _ = match_template(VS_REGION, "vs.png", 0.7, True)
    return f

def detect_single_pokemon(img):
    # Detects a single Pokémon using a given image template.
    global active
    if not active:
        return False
    f, _ = match_template(POKEMON_REGION, img, 0.7, True)
    if f:
        print("Found", os.path.splitext(os.path.basename(img))[0])
    return f

def detect_pokemon():
    # Detects any Pokémon from the list of template images in the defined region.
    global active
    if not active:
        return False
    with ThreadPoolExecutor() as e:
        return any(e.map(detect_single_pokemon, pokemon_images))

def handle_fainted_pokemon():
    # Handles the switching of Pokémon when the current one faints.
    global active
    if not active:
        return False
    f, _ = match_template(GENERAL_REGION, "fainted.png", 0.60, True)
    if not f:
        return True

    print("Fainted Pokémon found, switching...")
    for m in alive_party_members:
        if not active:
            return False
        fm, mc = match_template(GENERAL_REGION, m, 0.45, True)
        if fm:
            print("Switching to", os.path.basename(m))
            pyautogui.moveTo(mc)
            time.sleep(0.12)
            pyautogui.click()
            time.sleep(0.5)
            f2, _ = match_template(GENERAL_REGION, "fainted.png", 0.65, True)
            if not f2:
                return True
    print("Could not resolve fainted Pokémon.")
    return False

def spam_left_click():
    # Spams left clicks on the Fight button if detected.
    global active
    if not active:
        return
    f, c = match_template(GENERAL_REGION, "fight_button.png", 0.8, True)
    if f:
        print("Found Fight button.")
        if pyautogui.position() != c:
            pyautogui.moveTo(c)
            time.sleep(0.12)
        pyautogui.click(clicks=10, interval=0.1)

def check_for_disconnect():
    # Checks for disconnection and reconnects the game if needed.
    global active
    if not active:
        return False
    f, _ = match_template(DISCONNECTED_REGION, "disconnected.png", 0.8, True)
    if not f:
        return False

    print("Game disconnected. Reloading...")
    active = False  # Force pause during reconnect

    # Press Ctrl+R
    keyboard.press("ctrl")
    keyboard.press("r")
    keyboard.release("r")
    keyboard.release("ctrl")
    time.sleep(6)

    found_conn = False
    for _ in range(30):
        fc, cc = match_template(CONNECT_REGION, "connect.png", 0.8, True)
        if fc:
            pyautogui.moveTo(cc)
            time.sleep(0.1)
            pyautogui.click()
            found_conn = True
            break
        time.sleep(1)

    if not found_conn:
        sys.exit("Connect not found.")

    time.sleep(6)
    keyboard.press("b")
    keyboard.release("b")
    time.sleep(1)

    # After reconnect, allow script to continue
    active = True
    print("Reconnected.")
    return True

def main_logic(kill_event):
    # Runs the main loop to manage game automation logic.
    global active
    lc = 0
    while not kill_event.is_set():
        if not active:
            time.sleep(0.1)
            continue

        lc += 1

        if lc % 10 == 1 and check_for_disconnect():
            continue

        if detect_vs_menu():
            if not handle_fainted_pokemon():
                continue
            if detect_pokemon():
                spam_left_click()

        time.sleep(0.2)

# TOGGLE THREAD
def toggle_active_thread(kill_event):
    # Monitors for user input to toggle active state or stop the script.
    global active
    print("Toggle thread started. Press '\\' to pause/unpause, 'esc' to quit.")

    while not kill_event.is_set():
        if keyboard.is_pressed("\\"):
            old_active = active
            active = not active

            # If we just turned on 'active', move mouse & click
            if not old_active and active:
                pyautogui.moveTo(1000, 500)
                time.sleep(0.1)
                pyautogui.click()
                print("Re-activated.")

            print(f"[Toggle] active = {active}")
            time.sleep(0.5)  # small delay to prevent rapid toggles

        time.sleep(0.1)

# MAIN ENTRY POINT
if __name__ == "__main__":
    # Initialize threads for various functionalities.
    t1 = threading.Thread(target=spam_a_and_d, args=(kill_event,), daemon=True)
    t2 = threading.Thread(target=main_logic, args=(kill_event,), daemon=True)
    t3 = threading.Thread(target=toggle_active_thread, args=(kill_event,), daemon=True)

    t1.start()
    t2.start()
    t3.start()

    print("Press 'esc' to stop.")
    while True:
        time.sleep(0.1)
        # Use ESC as the kill signal
        if keyboard.is_pressed("esc"):
            print("ESC pressed. Stopping threads...")
            kill_event.set()
            break

    t1.join()
    t2.join()
    t3.join()
    print("Exiting.")
