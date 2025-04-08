import csv
import time
import os
import uuid
from pynput import keyboard, mouse
import pygetwindow as gw
import signal
import threading
import mss
import cv2
import numpy as np

PROJECT_NAME = 'TicTacToe'
if not os.path.exists(PROJECT_NAME):
    os.makedirs(PROJECT_NAME)
SESSION_LOG_FILE = os.path.join(PROJECT_NAME, 'session_log.csv')

# Get user input for user_id
USER_ID = input("Enter user ID: ")
KEY_TO_MONITOR = keyboard.Key.f1 #replace with None for single session

# Create a CSV to track session details if it doesn't exist
if not os.path.exists(SESSION_LOG_FILE):
    with open(SESSION_LOG_FILE, 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Session ID', 'User ID', 'Start Time', 'Duration'])

# Function to create a new session
def create_new_session():
    global session_id, session_folder, images_folder, start_time
    session_id = str(uuid.uuid4())
    session_folder = os.path.join(PROJECT_NAME, f'Session-{session_id}')
    os.makedirs(session_folder)
    images_folder = os.path.join(session_folder, 'images')
    os.makedirs(images_folder)
    # Record the start time
    start_time = time.time()
    print(f"{session_folder} started.")

def end_session():
    # Update the session duration in the session_log.csv on interrupt
    end_time = time.time()
    duration = end_time - start_time
    with open(SESSION_LOG_FILE, 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([session_id, USER_ID, start_time, duration])
    print(f"{session_folder} ended.")

def log_to_csv(file_name, data):
    with open(os.path.join(session_folder, file_name), 'a', newline='') as file:
        writer = csv.writer(file)
        try:
            writer.writerow(data)
        except:
            print(data)
            os._exit(0)

def get_window_focus(software_only=False):
    window = gw.getActiveWindow()
    if window:
        title = window.title
        if software_only:
            title = title.split(' - ')[-1]  # Assuming the software name is at the end
        return title.encode('ascii', 'ignore').decode('ascii')  # Remove non-ASCII characters
    return 'Unknown'


key_press_times = {}
mouse_press_times = {}

def on_press(key):
    if key == KEY_TO_MONITOR:  # Keybind to create a new session
        end_session()
        create_new_session()
    else:
        press_time = time.time()
        key_press_times[key] = press_time
        log_to_csv('keyboard.csv', [USER_ID, get_window_focus(), key, 'pressed', press_time])

def on_release(key):
    if not key == KEY_TO_MONITOR:  # Keybind to create a new session
        release_time = time.time()
        press_time = key_press_times.pop(key, None)
        duration = release_time - press_time if press_time else 0
        log_to_csv('keyboard.csv', [USER_ID, get_window_focus(), key, 'released', press_time, release_time, duration])

def on_click(x, y, button, pressed):
    timestamp = time.time()
    window_focus = gw.getActiveWindow()
    if window_focus:
        top = window_focus.top
        left = window_focus.left
        relative_x = x - left
        relative_y = y - top
        if pressed:
            press_time = timestamp
            mouse_press_times[button] = press_time
            log_to_csv('mouse.csv', [USER_ID, get_window_focus(), button, 'pressed', relative_x, relative_y, press_time])
        else:
            release_time = timestamp
            press_time = mouse_press_times.pop(button, None)
            duration = timestamp - press_time if press_time else 0
            log_to_csv('mouse.csv', [USER_ID, get_window_focus(), button, 'released', relative_x, relative_y, press_time, release_time, duration])

def on_move(x, y):
    timestamp = time.time()
    window_focus = gw.getActiveWindow()
    if window_focus:
        top = window_focus.top
        left = window_focus.left
        relative_x = x - left
        relative_y = y - top
        log_to_csv('mouse.csv', [USER_ID, get_window_focus(), 'move', relative_x, relative_y, timestamp])


def capture_screen(fps=30, resolution=(512, 512)):
    frame_interval = 1 / fps
    frame_num = 0
    with mss.mss() as sct:
        while True:
            timestamp = time.time()
            window_focus = gw.getActiveWindow()
            if window_focus:
                monitor_width = window_focus.width
                monitor_height = window_focus.height
                monitor = {
                    "top": window_focus.top,
                    "left": window_focus.left,
                    "width": window_focus.width,
                    "height": window_focus.height,
                }
                frame = sct.grab(monitor)
                frame_filename = f'{images_folder}/frame_{frame_num}.png'
                
                # Convert the frame to a numpy array
                img = np.array(frame)
                
                # Remove the alpha channel (BGRA to BGR)
                img = img[:, :, :3]

                
                # Resize the image to the specified resolution
                resized_img = cv2.resize(img, resolution)
                
                # Save the resized image
                cv2.imwrite(frame_filename, resized_img)
                
                log_to_csv('annotations.csv', [USER_ID, get_window_focus(), monitor_width, monitor_height, timestamp, f'frame_{frame_num}.png'])
            frame_num += 1
            time.sleep(frame_interval)

create_new_session()
keyboard_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
mouse_listener = mouse.Listener(on_click=on_click, on_move=on_move)

keyboard_listener_thread = threading.Thread(target=keyboard_listener.start)
mouse_listener_thread = threading.Thread(target=mouse_listener.start)

keyboard_listener_thread.start()
mouse_listener_thread.start()

def signal_handler(sig, frame):
    end_session()
    os._exit(0)

signal.signal(signal.SIGINT, signal_handler)

# Wait for the listeners to finish
keyboard_listener_thread.join()
mouse_listener_thread.join()
capture_screen(fps=30, resolution=(512, 512))

