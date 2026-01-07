import serial
import serial.tools.list_ports
import random
import time
import pyautogui
import sys
import re
from termcolor import colored

class ArduinoMouse:
    def __init__(self, filter_length=3):
        self.serial_port = serial.Serial()
        self.serial_port.baudrate = 115200
        self.serial_port.timeout = 1
        self.serial_port.port = self.find_serial_port()
        self.filter_length = filter_length
        self.x_history = [0] * filter_length
        self.y_history = [0] * filter_length
        
        try:
            self.serial_port.open()
            print(colored('[Success]', 'green'), colored(f'Connected to Arduino on {self.serial_port.port}', 'white'))
            
            # Test connection
            time.sleep(2)  # Give Arduino time to reset
            self.serial_port.write(b'\n')  # Send newline to test
            
        except serial.SerialException as e:
            print(colored('[Error]', 'red'), colored(f'Serial port error: {e}', 'white'))
            print(colored('[Info]', 'blue'), colored('Trying alternative detection methods...', 'white'))
            
            # Try alternative detection
            self.try_alternative_connection()
        except Exception as e:
            print(colored('[Error]', 'red'), colored(f'Unexpected error: {e}', 'white'))
            time.sleep(5)
            sys.exit()

    def find_serial_port(self):
        """Find Arduino port - supports both normal and spoofed Arduino"""
        
        # Get all available ports
        all_ports = list(serial.tools.list_ports.comports())
        
        if not all_ports:
            print(colored('[Warning]', 'yellow'), colored('No COM ports found', 'white'))
            return None
        
        print(colored('[Info]', 'blue'), colored(f'Found {len(all_ports)} COM port(s):', 'white'))
        for port in all_ports:
            print(f"  • {port.device}: {port.description}")
        
        # Priority 1: Look for spoofed Arduino (Logitech G102)
        for port in all_ports:
            # Check hardware ID for Logitech VID:PID
            if "046D:C08B" in port.hwid or "046D:C085" in port.hwid:
                print(colored('[Success]', 'green'), colored(f'Found spoofed Arduino (Logitech G102) on {port.device}', 'white'))
                return port.device
        
        # Priority 2: Look for Arduino in description (normal mode)
        for port in all_ports:
            if "Arduino" in port.description:
                print(colored('[Success]', 'green'), colored(f'Found Arduino on {port.device}', 'white'))
                return port.device
        
        # Priority 3: Look for USB Serial Device (common for spoofed devices)
        for port in all_ports:
            if "USB Serial Device" in port.description:
                print(colored('[Info]', 'blue'), colored(f'Found USB Serial Device on {port.device} (may be spoofed Arduino)', 'white'))
                
                # Check if it might be Arduino by trying to connect
                try:
                    test_serial = serial.Serial(port.device, 115200, timeout=1)
                    test_serial.write(b'\n')
                    time.sleep(0.1)
                    test_serial.close()
                    print(colored('[Success]', 'green'), colored(f'Confirmed Arduino on {port.device}', 'white'))
                    return port.device
                except:
                    continue
        
        # Priority 4: Use COM9 specifically (from your detection)
        for port in all_ports:
            if port.device == "COM9" or port.device == "COM3" or port.device == "COM4":
                print(colored('[Info]', 'blue'), colored(f'Trying common Arduino port {port.device}', 'white'))
                
                # Try to connect to verify
                try:
                    test_serial = serial.Serial(port.device, 115200, timeout=1)
                    test_serial.write(b'\n')
                    time.sleep(0.1)
                    test_serial.close()
                    print(colored('[Success]', 'green'), colored(f'Arduino confirmed on {port.device}', 'white'))
                    return port.device
                except:
                    continue
        
        # If still not found, let user choose
        print(colored('[Warning]', 'yellow'), colored('Could not auto-detect Arduino', 'white'))
        print(colored('[Info]', 'blue'), colored('Please select your Arduino COM port:', 'white'))
        
        for i, port in enumerate(all_ports, 1):
            print(f"  {i}. {port.device}: {port.description}")
        
        try:
            choice = int(input("\nSelect port number: ")) - 1
            if 0 <= choice < len(all_ports):
                selected_port = all_ports[choice].device
                print(colored('[Info]', 'blue'), colored(f'Selected {selected_port}', 'white'))
                return selected_port
            else:
                print(colored('[Error]', 'red'), colored('Invalid selection', 'white'))
        except:
            pass
        
        return None

    def try_alternative_connection(self):
        """Try alternative connection methods"""
        print(colored('[Info]', 'blue'), colored('Trying alternative connection...', 'white'))
        
        # Common Arduino ports to try
        common_ports = ['COM9', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM10']
        
        for port_name in common_ports:
            try:
                print(colored('[Info]', 'blue'), colored(f'Trying {port_name}...', 'white'))
                self.serial_port.port = port_name
                self.serial_port.open()
                
                # Test connection
                self.serial_port.write(b'\n')
                time.sleep(0.1)
                
                print(colored('[Success]', 'green'), colored(f'Connected to Arduino on {port_name}', 'white'))
                return
                
            except serial.SerialException:
                continue
            except Exception as e:
                print(colored('[Warning]', 'yellow'), colored(f'Error trying {port_name}: {e}', 'white'))
        
        # If all fails, show error and exit
        print(colored('[Error]', 'red'), colored('Failed to connect to Arduino. Please:', 'white'))
        print("  1. Check Arduino is connected via USB")
        print("  2. Check Device Manager for correct COM port")
        print("  3. Close Arduino IDE and other serial programs")
        print("  4. Try unplugging and re-plugging Arduino")
        print("  5. Run the arduino_detector.py script to identify your port")
        
        time.sleep(10)
        sys.exit()

    def move(self, x, y):
        try:
            # Add to history for smoothing
            self.x_history.append(x)
            self.y_history.append(y)
            self.x_history.pop(0)
            self.y_history.pop(0)

            # Calculate smoothed values
            smooth_x = int(sum(self.x_history) / self.filter_length)
            smooth_y = int(sum(self.y_history) / self.filter_length)

            # Convert to Arduino format (0-255, with offset for negative)
            finalx = smooth_x + 256 if smooth_x < 0 else smooth_x
            finaly = smooth_y + 256 if smooth_y < 0 else smooth_y
            
            # Send command
            if self.serial_port.is_open:
                self.serial_port.write(b"M" + bytes([int(finalx), int(finaly)]))
            else:
                print(colored('[Warning]', 'yellow'), colored('Serial port not open', 'white'))
                
        except serial.SerialException as e:
            print(colored('[Error]', 'red'), colored(f'Move command failed: {e}', 'white'))
            self.reconnect()
        except Exception as e:
            print(colored('[Error]', 'red'), colored(f'Unexpected error in move: {e}', 'white'))

    def flick(self, x, y):
        try:
            # Convert to Arduino format
            x_arduino = x + 256 if x < 0 else x
            y_arduino = y + 256 if y < 0 else y
            
            # Send command
            if self.serial_port.is_open:
                self.serial_port.write(b"M" + bytes([int(x_arduino), int(y_arduino)]))
            else:
                print(colored('[Warning]', 'yellow'), colored('Serial port not open', 'white'))
                
        except serial.SerialException as e:
            print(colored('[Error]', 'red'), colored(f'Flick command failed: {e}', 'white'))
            self.reconnect()
        except Exception as e:
            print(colored('[Error]', 'red'), colored(f'Unexpected error in flick: {e}', 'white'))

    def click(self):
        try:
            # Add random delay for human-like clicking
            delay = random.uniform(0.01, 0.1)
            
            # Send click command
            if self.serial_port.is_open:
                self.serial_port.write(b"C")
                time.sleep(delay)
            else:
                print(colored('[Warning]', 'yellow'), colored('Serial port not open', 'white'))
                
        except serial.SerialException as e:
            print(colored('[Error]', 'red'), colored(f'Click command failed: {e}', 'white'))
            self.reconnect()
        except Exception as e:
            print(colored('[Error]', 'red'), colored(f'Unexpected error in click: {e}', 'white'))

    def reconnect(self):
        """Try to reconnect to Arduino"""
        print(colored('[Info]', 'blue'), colored('Attempting to reconnect...', 'white'))
        
        try:
            if self.serial_port.is_open:
                self.serial_port.close()
            
            time.sleep(1)
            
            # Try to reopen
            self.serial_port.open()
            time.sleep(2)  # Give Arduino time to reset
            
            print(colored('[Success]', 'green'), colored('Reconnected to Arduino', 'white'))
            
        except Exception as e:
            print(colored('[Error]', 'red'), colored(f'Reconnection failed: {e}', 'white'))
            print(colored('[Info]', 'blue'), colored('Will retry on next command', 'white'))

    def close(self):
        """Close serial connection"""
        try:
            if hasattr(self, 'serial_port') and self.serial_port.is_open:
                self.serial_port.close()
                print(colored('[Info]', 'blue'), colored('Serial port closed', 'white'))
        except:
            pass

    def __del__(self):
        self.close()


# Test function
if __name__ == "__main__":
    print("Testing ArduinoMouse connection...")
    
    try:
        mouse = ArduinoMouse()
        
        # Test commands
        print("\nTesting mouse movement...")
        mouse.move(10, 10)
        time.sleep(0.5)
        
        print("Testing click...")
        mouse.click()
        time.sleep(0.5)
        
        print("Testing flick...")
        mouse.flick(20, 20)
        
        print("\n✅ All tests completed successfully!")
        
        mouse.close()
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
    
    input("\nPress Enter to exit...")