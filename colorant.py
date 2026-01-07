import cv2
import numpy as np
import threading
import time
import win32api
import pyautogui
import psutil

from capture import Capture
from mouse import ArduinoMouse
from fov_window import show_detection_window, toggle_window

class Colorant:
    LOWER_COLOR = np.array([140,120,180])
    UPPER_COLOR = np.array([160,200,255])
    
    def __init__(self, x, y, xfov, yfov, FLICKSPEED, MOVESPEED):
        self.arduinomouse = ArduinoMouse()
        self.grabber = Capture(x, y, xfov, yfov)
        self.flickspeed = FLICKSPEED
        self.movespeed = MOVESPEED
        
        # State variables
        self.toggled = False  # Aimbot ON/OFF
        self.window_toggled = False
        self.running = True
        
        # Auto mode control
        self.auto_mode_active = False  # Starts OFF, activated by F1
        
        # Vanguard tracking
        self.last_vanguard_check = 0
        self.vanguard_check_interval = 2.0
        self.vanguard_was_active = False  # Track if Vanguard was active
        
        # Start threads
        self.listen_thread = threading.Thread(target=self.listen, daemon=True)
        self.vanguard_monitor_thread = threading.Thread(target=self.monitor_vanguard, daemon=True)
        
        self.listen_thread.start()
        self.vanguard_monitor_thread.start()
        
    def find_vanguard_process(self):
        """Find Vanguard processes by name"""
        vanguard_processes = []
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
                try:
                    proc_name = proc.info['name'].lower()
                    if 'vgc' in proc_name or 'vanguard' in proc_name or 'riot' in proc_name:
                        vanguard_processes.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except:
            pass
        return vanguard_processes
    
    def get_vanguard_cpu_usage(self):
        """Get total CPU usage of Vanguard processes"""
        total_cpu = 0.0
        vanguard_procs = self.find_vanguard_process()
        
        for proc in vanguard_procs:
            try:
                cpu = proc.cpu_percent(interval=0.0)
                total_cpu += cpu
            except:
                continue
        
        return total_cpu, len(vanguard_procs) > 0
    
    def monitor_vanguard(self):
        """Monitor Vanguard CPU usage and auto-toggle"""
        while self.running:
            try:
                current_time = time.time()
                
                # Only check if auto mode is active (F1 enabled it)
                if not self.auto_mode_active:
                    time.sleep(1.0)
                    continue
                
                # Check at intervals
                if current_time - self.last_vanguard_check >= self.vanguard_check_interval:
                    vanguard_cpu, vanguard_running = self.get_vanguard_cpu_usage()
                    self.last_vanguard_check = current_time
                    
                    # Auto-toggle logic - 0% CPU = ON, any CPU = OFF
                    if vanguard_running:
                        if vanguard_cpu > 0:  # Any CPU usage
                            if self.toggled:  # Only if aimbot is ON
                                self.toggled = False
                                self.vanguard_was_active = True
                                self._pause_capture()
                        else:  # 0% CPU
                            if not self.toggled and self.vanguard_was_active:
                                self.toggled = True
                                self.vanguard_was_active = False
                                self._resume_capture()
                    else:  # Vanguard not running
                        if not self.toggled and self.vanguard_was_active:
                            self.toggled = True
                            self.vanguard_was_active = False
                            self._resume_capture()
                        elif not self.toggled and self.auto_mode_active:
                            self.toggled = True
                            self.vanguard_was_active = False
                            self._resume_capture()
                
                time.sleep(0.5)
                
            except Exception as e:
                time.sleep(2.0)
    
    def _pause_capture(self):
        """Pause screen capture if supported"""
        try:
            if hasattr(self.grabber, 'pause'):
                self.grabber.pause()
        except:
            pass
    
    def _resume_capture(self):
        """Resume screen capture if supported"""
        try:
            if hasattr(self.grabber, 'resume'):
                self.grabber.resume()
        except:
            pass
    
    def toggle(self):
        """F1 toggle - enables/disables both aimbot AND auto mode"""
        if self.toggled:
            # Turning OFF - disable aimbot and auto mode
            self.toggled = False
            self.auto_mode_active = False  # Disable auto mode
            self.vanguard_was_active = False
            self._pause_capture()
        else:
            # Turning ON - enable aimbot and auto mode
            self.toggled = True
            self.auto_mode_active = True  # Enable auto mode
            self.vanguard_was_active = False
            self._resume_capture()
        
        return self.toggled
    
    def close(self):
        """Stop the listen thread and cleanup"""
        self.running = False
        
        # Stop capture if supported
        try:
            if hasattr(self.grabber, 'stop'):
                self.grabber.stop()
        except:
            pass
        
        if hasattr(self, 'listen_thread'):
            self.listen_thread.join(timeout=1.0)
        if hasattr(self, 'vanguard_monitor_thread'):
            self.vanguard_monitor_thread.join(timeout=1.0)
            
        if hasattr(self.arduinomouse, 'close'):
            self.arduinomouse.close()
    
    def listen(self):
        """Listen for key presses"""
        while self.running:
            try:
                # Check for window toggle (F2)
                if win32api.GetAsyncKeyState(0x71) < 0:  # F2 key
                    toggle_window(self)
                    time.sleep(0.2)
                
                # Process actions if toggled ON
                elif self.toggled:
                    if (win32api.GetAsyncKeyState(0xA0) < 0 or
                        win32api.GetAsyncKeyState(0x01) < 0 or
                        win32api.GetAsyncKeyState(0x11) < 0 or
                        win32api.GetAsyncKeyState(0x46) < 0 or
                        win32api.GetAsyncKeyState(0x20) < 0):
                        self.process("move")
                        
                    elif win32api.GetAsyncKeyState(0x12) < 0:
                        self.process("click")
                        
                    elif win32api.GetAsyncKeyState(0x76) < 0:
                        self.process("flick")
                
                time.sleep(0.01)
                
            except Exception as e:
                time.sleep(0.1)
    
    def process(self, action):
        """Process movement/click actions"""
        # Safety check
        if not self.toggled:
            return
            
        try:
            screen = self.grabber.get_screen()
            hsv = cv2.cvtColor(screen, cv2.COLOR_BGR2HSV)
            mask = cv2.inRange(hsv, self.LOWER_COLOR, self.UPPER_COLOR)
            dilated = cv2.dilate(mask, None, iterations=5)
            contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            if not contours:
                return

            contour = max(contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(contour)
            center = (x + w // 2, y + h // 2)
            y_offset = int(h * 0.1)

            if action == "move":
                cX = center[0]
                cY = y + y_offset
                x_diff = cX - self.grabber.xfov // 2
                y_diff = cY - self.grabber.yfov // 2
                self.arduinomouse.move(x_diff * self.movespeed, y_diff * self.movespeed)

            elif action == "click" and abs(center[0] - self.grabber.xfov // 2) <= 4 and abs(center[1] - self.grabber.yfov // 2) <= 10:
                self.arduinomouse.click()

            elif action == "flick":
                cX = center[0] + 2
                cY = y + y_offset
                x_diff = cX - self.grabber.xfov // 2
                y_diff = cY - self.grabber.yfov // 2
                flickx = x_diff * self.flickspeed
                flicky = y_diff * self.flickspeed
                self.arduinomouse.flick(flickx, flicky)
                self.arduinomouse.click()
                self.arduinomouse.flick(-(flickx), -(flicky))
                
        except Exception as e:
            pass