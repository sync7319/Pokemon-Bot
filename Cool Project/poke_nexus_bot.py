import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import keyboard
import pyautogui
from pyautogui import locateOnScreen, center, moveTo, click

# Define regions for specific searches
POKEMON_REGION = (2075, 600, 325, 250)  # (x, y, width, height)
VS_REGION = (2050, 475, 100, 100)       # (x, y, width, height)
GENERAL_REGION = (1650, 900, 750, 200)  # (x, y, width, height)

# New regions for disconnection checks
DISCONNECTED_REGION = (1490, 910, 240, 160)  # (x, y, width, height)
CONNECT_REGION = (1800, 1050, 350, 175)     # (x, y, width, height)

pokemon_images_folder = "pokemon_images"
alive_party_members_folder = "alive_party_members"

# Dynamically fetch all .png files in the respective folders
pokemon_images = [
    os.path.join(pokemon_images_folder, file)
    for file in os.listdir(pokemon_images_folder)
    if file.endswith(".png")
]
alive_party_members = [
    os.path.join(alive_party_members_folder, file)
    for file in os.listdir(alive_party_members_folder)
    if file.endswith(".png")
]

# Event object for safely stopping threads
kill_event = threading.Event()

# Global variable to control spamming of A/D
spam_active = True


def spam_a_and_d(kill_event):
    """
    Continuously spam 'A' and 'D' alternately until the kill_event is set.
    Pauses if spam_active is False.
    """
    global spam_active
    print("Task 1: Spamming 'A' and 'D'...")
    while not kill_event.is_set():
        # If spamming is paused, skip pressing A/D
        if not spam_active:
            time.sleep(0.1)
            continue

        keyboard.press("a")
        time.sleep(0.5)
        keyboard.release("a")

        # Short sleep between key presses to avoid accidental overlap
        time.sleep(0.05)

        if not spam_active:
            # Check again in case it changed while sleeping
            continue

        keyboard.press("d")
        time.sleep(0.5)
        keyboard.release("d")

        if kill_event.is_set():
            print("Spam A and D stopped.")
            break


def detect_vs_menu() -> bool:
    """
    Check if the VS menu ('vs.png') is visible within the VS region.
    Returns True if found, False otherwise.
    """
    try:
        return locateOnScreen("vs.png", region=VS_REGION, confidence=0.7, grayscale=True) is not None
    except pyautogui.ImageNotFoundException:
        return False
    except Exception:
        return False


def detect_single_pokemon(image: str) -> bool:
    """
    Check if a single Pokémon image is visible within the Pokémon region.
    Returns True if found, False otherwise.
    """
    try:
        location = locateOnScreen(image, region=POKEMON_REGION, confidence=0.55, grayscale=True)
        if location is not None:
            pokemon_name = os.path.splitext(os.path.basename(image))[0]
            print(f"Found {pokemon_name}")
            return True
    except pyautogui.ImageNotFoundException:
        pass
    except Exception:
        pass
    return False


def detect_pokemon() -> bool:
    """
    Check if any Pokémon image is visible using parallel processing.
    Returns True if at least one Pokémon image is found.
    """
    with ThreadPoolExecutor() as executor:
        results = list(executor.map(detect_single_pokemon, pokemon_images))
    return any(results)


def handle_fainted_pokemon() -> bool:
    """
    Handle the scenario when a Pokémon faints by switching to an available party member.
    Returns True if a fainted Pokémon was detected and handled, or if no fainted Pokémon
    is detected. Returns False if fainted Pokémon is still unresolved.
    """
    try:
        fainted_location = locateOnScreen(
            "fainted.png", region=GENERAL_REGION, confidence=0.65,
        )
    except pyautogui.ImageNotFoundException:
        fainted_location = None

    if fainted_location is None:
        return True  # No fainted Pokémon to handle, or not visible

    print("Found Fainted Pokémon, switching Pokémon!")

    # Try switching to each alive party member
    for member_image in alive_party_members:
        try:
            location = locateOnScreen(member_image, region=GENERAL_REGION, confidence=0.55)
            if location is not None:
                print(f"Switching to party member: {os.path.basename(member_image)}")

                moveTo(center(location))
                time.sleep(0.12)
                click()

                time.sleep(0.5)

                try:
                    fainted_location = locateOnScreen(
                        "fainted.png", region=GENERAL_REGION, confidence=0.8, grayscale=True
                    )
                except pyautogui.ImageNotFoundException:
                    fainted_location = None

                if fainted_location is None:
                    print("Fainted Pokémon successfully swapped out.")
                    return True
        except Exception as e:
            print(f"Error checking {os.path.basename(member_image)}: {e}")

    print("Fainted Pokémon could not be resolved with available party members.")
    return False


def spam_left_click():
    """
    Spam left click on the fight button within the general region if it's visible.
    """
    try:
        fight_button_location = locateOnScreen(
            "fight_button.png", region=GENERAL_REGION, confidence=0.8, grayscale=True
        )
        if fight_button_location is not None:
            print("Found Fight button, attacking!")
            target_position = center(fight_button_location)

            if pyautogui.position() != target_position:
                moveTo(target_position)
                time.sleep(0.12)

            # Perform 10 clicks with a small interval
            click(target_position, clicks=10, interval=0.1)
        else:
            print("Fight button not detected.")
    except pyautogui.ImageNotFoundException:
        pass
    except Exception:
        pass


def check_for_disconnect() -> bool:
    """
    Checks if the game is disconnected by looking for 'disconnected.png' in DISCONNECTED_REGION.
    If found:
      - Sets spam_active to False to pause spamming.
      - Press Ctrl+R, wait 10s, then look for 'connect.png' in CONNECT_REGION for up to 30 tries.
      - If found, click it, wait 10s, press 'b', set spam_active to True, and return True.
      - If not found after 30 attempts, sys.exit(1).
    Returns:
      True if disconnected was found and successfully reconnected.
      False if disconnected.png was not found at all.
    """
    global spam_active
    try:
        disconnected_location = locateOnScreen(
            "disconnected.png", region=DISCONNECTED_REGION, confidence=0.8, grayscale=True
        )
    except pyautogui.ImageNotFoundException:
        disconnected_location = None

    if disconnected_location is None:
        return False  # Not disconnected, do nothing.

    print("Game is disconnected! Reloading page...")
    spam_active = False  # Pause spamming A/D

    # Press Ctrl+R
    keyboard.press('ctrl')
    keyboard.press('r')
    keyboard.release('r')
    keyboard.release('ctrl')

    # Wait for reload
    time.sleep(6)

    # Look for the connect button up to 30 times
    found_connect = False
    for _ in range(30):
        try:
            connect_location = locateOnScreen(
                "connect.png", region=CONNECT_REGION, confidence=0.8, grayscale=True
            )
        except pyautogui.ImageNotFoundException:
            connect_location = None

        if connect_location is not None:
            print("Found connect button, clicking...")
            moveTo(center(connect_location))
            time.sleep(0.1)
            click()
            found_connect = True
            break
        time.sleep(1)

    if not found_connect:
        print("Could not find connect button. Exiting program.")
        sys.exit(1)

    # Wait after clicking Connect
    time.sleep(6)

    # Press 'b' in-game
    keyboard.press('b')
    keyboard.release('b')
    time.sleep(1)

    # Reactivate spamming after successful reconnect
    spam_active = True

    print("Reconnected successfully. Resuming...")
    return True


def main_logic(kill_event):
    """
    Main logic running in a loop until kill_event is set:
      - Every 10 iterations, check if the game is disconnected.
      - Checks if the VS menu is up.
      - Handles fainted Pokémon.
      - If a Pokémon is detected, attempts to fight.
    """
    print("Task 2: Main logic running...")
    loop_counter = 0

    while not kill_event.is_set():
        loop_counter += 1

        # Every 10 loops, check for disconnection
        if loop_counter % 10 == 1:
            if check_for_disconnect():
                # If we just reconnected, go back to top of loop
                continue

        # Check for the 'vs' menu
        if detect_vs_menu():
            # Handle fainted Pokémon first
            if not handle_fainted_pokemon():
                # If fainted Pokémon couldn't be handled, skip next actions
                continue

            # If at least one Pokémon is detected, attempt to fight
            if detect_pokemon():
                spam_left_click()

        # Small delay to avoid hogging CPU with continuous locateOnScreen checks
        time.sleep(0.2)

    print("Main logic stopped.")


if __name__ == "__main__":
    # Create threads
    ad_thread = threading.Thread(target=spam_a_and_d, args=(kill_event,), daemon=True)
    logic_thread = threading.Thread(target=main_logic, args=(kill_event,), daemon=True)

    ad_thread.start()
    logic_thread.start()

    print("Press '\\' to stop the script.")

    # Main thread watches for the kill key
    while True:
        time.sleep(0.1)  # Reduce busy waiting
        if keyboard.is_pressed("\\"):
            print("Kill key detected. Stopping all threads...")
            kill_event.set()
            break

    # Wait for both threads to complete
    ad_thread.join()
    logic_thread.join()

    print("All threads terminated. Exiting program.")
