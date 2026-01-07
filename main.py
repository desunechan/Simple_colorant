import os
import time
import pyautogui
import sys
import ctypes
import threading

# Global variables for tray control
tray_icon = None
colorant_instance = None
app_running = True
keyboard_available = False

# Try to import colorant (silent import)
try:
    from colorant import Colorant
    COLORANT_AVAILABLE = True
except ImportError:
    COLORANT_AVAILABLE = False
    Colorant = None

# Try to import keyboard (silent import)
try:
    import keyboard
    keyboard_available = True
except ImportError:
    keyboard_available = False

# Try to import tray modules (silent import)
try:
    import pystray
    from PIL import Image, ImageDraw
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False

# ========== SILENT HOTKEY HANDLING ==========
class HotkeyManager:
    """Manages hotkey detection without console output"""
    def __init__(self):
        self.last_toggle_time = 0
        self.toggle_debounce = 0.5  # 500ms debounce
        self.callbacks = {}
        
    def setup_hotkey(self, key, callback):
        """Setup a hotkey with callback (silent)"""
        if keyboard_available:
            try:
                keyboard.on_press_key(key, lambda e: self._handle_key(callback))
                return True
            except Exception:
                self.callbacks[key] = callback
                return False
        return False
    
    def _handle_key(self, callback):
        """Handle key press with debouncing"""
        current_time = time.time()
        if current_time - self.last_toggle_time > self.toggle_debounce:
            self.last_toggle_time = current_time
            try:
                callback()
            except Exception:
                pass
    
    def poll_keys(self):
        """Poll for key presses (silent)"""
        if not keyboard_available:
            return
        
        try:
            for key, callback in self.callbacks.items():
                if keyboard.is_pressed(key):
                    current_time = time.time()
                    if current_time - self.last_toggle_time > self.toggle_debounce:
                        self.last_toggle_time = current_time
                        callback()
        except Exception:
            pass

# Global hotkey manager
hotkey_manager = HotkeyManager()

# ========== SILENT RECORDER CONTROL ==========
class RecorderController:
    """Manages the Colorant recorder without console output"""
    def __init__(self):
        self.colorant_instance = None
        self.is_recording = False
        self.xfov = 75
        self.yfov = 75
        self.ingame_sensitivity = 0.23
        self.monitor = pyautogui.size()
        self.center_x = self.monitor.width // 2
        self.center_y = self.monitor.height // 2
        
        # Calculate speeds
        self.flickspeed = 1.07437623 * (self.ingame_sensitivity ** -0.9936827126)
        self.movespeed = 1 / (10 * self.ingame_sensitivity)
        
    def initialize(self):
        """Initialize the Colorant recorder (silent)"""
        if not COLORANT_AVAILABLE:
            self.colorant_instance = self.create_dummy_colorant()
            return True
        
        try:
            self.colorant_instance = Colorant(
                self.center_x - self.xfov // 2,
                self.center_y - self.yfov // 2,
                self.xfov,
                self.yfov,
                self.flickspeed,
                self.movespeed
            )
            return True
        except Exception:
            self.colorant_instance = self.create_dummy_colorant()
            return True
    
    def create_dummy_colorant(self):
        """Create a dummy colorant (silent)"""
        class DummyColorant:
            def __init__(self, *args, **kwargs):
                self.toggled = False
                
            def toggle(self):
                self.toggled = not self.toggled
                return self.toggled
                
            def close(self):
                pass
        
        return DummyColorant(
            self.center_x - self.xfov // 2,
            self.center_y - self.yfov // 2,
            self.xfov,
            self.yfov,
            self.flickspeed,
            self.movespeed
        )
    
    def toggle_recording(self):
        """Toggle recording state (silent)"""
        if self.colorant_instance:
            try:
                self.colorant_instance.toggle()
                self.is_recording = self.colorant_instance.toggled
                return self.is_recording
            except Exception:
                return False
        return False
    
    def cleanup(self):
        """Clean up resources (silent)"""
        if self.colorant_instance:
            try:
                self.colorant_instance.close()
            except:
                pass

# Global recorder controller
recorder_controller = RecorderController()

# ========== SILENT PROCESS NAME SPOOFING ==========
def setup_process_spoofing():
    """Setup process name spoofing without console output"""
    if sys.platform != 'win32':
        return False
    
    if getattr(sys, 'frozen', False):
        return True
    
    try:
        # Try setproctitle
        try:
            import setproctitle
            setproctitle.setproctitle("svchost.exe -k LocalSystemNetworkRestricted")
        except ImportError:
            pass
        
        # Set window title
        try:
            os.system('title svchost.exe')
        except:
            pass
        
        return True
        
    except Exception:
        return False

# ========== TRAY ICON FUNCTIONS ==========
def create_record_icon(is_recording=False):
    """Create a record icon"""
    if not TRAY_AVAILABLE:
        return None
    
    size = 64
    image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    outline_color = (255, 0, 0, 255) if is_recording else (100, 100, 100, 255)
    fill_color = (255, 0, 0, 200) if is_recording else (150, 150, 150, 100)
    
    margin = 8
    draw.ellipse([margin, margin, size - margin, size - margin], 
                fill=fill_color, outline=outline_color, width=3)
    
    if is_recording:
        from PIL import ImageFont
        try:
            font = ImageFont.truetype("arial.ttf", 12)
        except:
            font = ImageFont.load_default()
        
        draw.text((size//2 - 10, size//2 - 6), "REC", fill=(255, 255, 255, 255), font=font)
    
    return image

def update_tray_icon(is_recording):
    """Update the tray icon and tooltip"""
    global tray_icon
    if tray_icon and TRAY_AVAILABLE:
        try:
            new_icon = create_record_icon(is_recording)
            if new_icon:
                tray_icon.icon = new_icon
                
            if is_recording:
                tray_icon.title = "Recording - Press F1 to stop"
            else:
                tray_icon.title = "Press F1 to record"
                
            tray_icon.update_menu()
        except Exception:
            pass

def on_toggle_tray(icon, item):
    """Toggle recording from tray menu"""
    try:
        global recorder_controller
        is_recording = recorder_controller.toggle_recording()
        update_tray_icon(is_recording)
    except Exception:
        pass

def on_exit_tray(icon, item):
    """Exit the application from tray"""
    global app_running, tray_icon, recorder_controller
    app_running = False
    
    # Cleanup
    recorder_controller.cleanup()
    
    if tray_icon:
        try:
            tray_icon.stop()
        except:
            pass
    
    # Exit
    import os
    os._exit(0)

def on_toggle_hotkey():
    """Handle F1 hotkey toggle (silent)"""
    try:
        global recorder_controller, tray_icon
        is_recording = recorder_controller.toggle_recording()
        
        if TRAY_AVAILABLE and tray_icon:
            update_tray_icon(is_recording)
                
    except Exception:
        pass

def create_tray_icon():
    """Create and run system tray icon"""
    if not TRAY_AVAILABLE:
        return
    
    image = create_record_icon(False)
    if image is None:
        return
    
    menu_items = [
        pystray.MenuItem("Start/Stop Record (F1)", on_toggle_tray),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Exit", on_exit_tray)
    ]
    
    global tray_icon
    tray_icon = pystray.Icon(
        "colorant_recorder",
        image,
        "Press F1 to Record",
        menu=pystray.Menu(*menu_items)
    )
    
    try:
        tray_icon.run()
    except Exception:
        pass

# ========== MAIN PROGRAM ==========
def run_main_program():
    """Main program logic (silent)"""
    global app_running, recorder_controller
    
    # Initialize recorder
    if not recorder_controller.initialize():
        return
    
    # Setup hotkey
    hotkey_manager.setup_hotkey('F1', on_toggle_hotkey)
    
    # Main loop
    try:
        while app_running:
            hotkey_manager.poll_keys()
            time.sleep(0.05)
            
    except KeyboardInterrupt:
        pass
    except Exception:
        pass
    finally:
        # Cleanup
        recorder_controller.cleanup()

def run_as_tray():
    """Run the application with system tray (silent)"""
    global app_running
    
    # Setup process spoofing
    setup_process_spoofing()
    
    # Start tray
    if TRAY_AVAILABLE:
        tray_thread = threading.Thread(target=create_tray_icon, daemon=True)
        tray_thread.start()
        time.sleep(1)  # Give tray time to initialize
    
    # Run main program
    run_main_program()

def main():
    """Main entry point - tray-only mode"""
    # Hide console window on Windows
    if sys.platform == 'win32':
        try:
            ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
        except:
            pass
    
    # Always run in tray-only mode
    run_as_tray()

if __name__ == '__main__':
    # Run without any console output
    try:
        main()
    except Exception:
        pass