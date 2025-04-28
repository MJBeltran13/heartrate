#!/usr/bin/env python3
"""
ECG Raw Data Capture Tool

This script captures raw ECG data from an ESP32 with AD8232 ECG sensor
and saves it to a CSV file. Compatible with ecg_ad8232.ino Arduino sketch.

Usage:
    python ecg_data_capture.py [--port PORT] [--baud BAUD] [--duration DURATION] [--output OUTPUT]

Example:
    python ecg_data_capture.py --port COM6 --baud 115200 --duration 30 --output ecg_data.csv
"""

import argparse
import serial
import time
import csv
import os
import sys
from datetime import datetime

def print_flush(*args, **kwargs):
    """Print and flush immediately."""
    print(*args, **kwargs)
    sys.stdout.flush()

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Capture raw ECG data from Arduino with AD8232 sensor')
    parser.add_argument('--port', type=str, default=None,
                        help='Serial port (e.g., COM3, /dev/ttyUSB0)')
    parser.add_argument('--baud', type=int, default=115200,
                        help='Baud rate (default: 115200)')
    parser.add_argument('--duration', type=float, default=30.0,
                        help='Recording duration in seconds (default: 30.0)')
    parser.add_argument('--output', type=str, default=None,
                        help='Output CSV file (default: ecg_data_YYYYMMDD_HHMMSS.csv)')
    return parser.parse_args()

def list_serial_ports():
    """List available serial ports."""
    import serial.tools.list_ports
    ports = serial.tools.list_ports.comports()
    if not ports:
        print("No serial ports found.")
        return []
    
    print("Available serial ports:")
    for i, port in enumerate(ports):
        print(f"{i+1}. {port.device} - {port.description}")
    return [port.device for port in ports]

def select_port(ports):
    """Let the user select a serial port."""
    if not ports:
        return None
    
    while True:
        try:
            selection = input("Select port number (or press Enter for automatic detection): ")
            if not selection:
                return None
            
            index = int(selection) - 1
            if 0 <= index < len(ports):
                return ports[index]
            else:
                print("Invalid selection. Please try again.")
        except ValueError:
            print("Please enter a number.")

def capture_raw_data(port, baud_rate, duration, output_file):
    """Capture raw ECG data from the ESP32 and save to CSV."""
    print_flush(f"Attempting to connect to ESP32 on {port} at {baud_rate} baud...")
    
    try:
        ser = serial.Serial(port, baud_rate, timeout=1)
    except serial.SerialException as e:
        print_flush(f"Error opening serial port {port}: {e}")
        print_flush("Please check if:")
        print_flush("1. The ESP32 is properly connected")
        print_flush("2. No other program is using the port")
        print_flush("3. You have the correct port number")
        print_flush("4. The Arduino IDE is not using the Serial Monitor")
        return False
    
    print_flush("Successfully connected to ESP32!")
    print_flush("Waiting for device to reset...")
    
    # Wait for ESP32 to reset
    time.sleep(2)
    
    # Clear any existing data and wait for header
    while ser.in_waiting:
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        if line == "ECG Raw Data Monitor Started":
            print_flush("Device initialized successfully")
            break
    
    # Prepare for data capture
    start_time = time.time()
    data = []
    sample_count = 0
    last_print_time = start_time
    expected_sample_rate = 400  # Hz (from Arduino code's 2500 microseconds delay)
    
    print_flush(f"Starting recording for {duration} seconds...")
    print_flush(f"Expected sampling rate: {expected_sample_rate} Hz")
    print_flush("Press Ctrl+C to stop recording early.")
    
    try:
        while time.time() - start_time < duration:
            if ser.in_waiting:
                try:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                
                    # Handle lead-off detection
                    if line == "Leads off!":
                        print_flush("Warning: Leads are not properly connected!")
                        continue
                    
                    # Skip header or empty lines
                    if not line or line == "raw":
                    continue
                
                    # Parse the raw value
                try:
                        raw_value = float(line)
                        time_sec = time.time() - start_time
                        data.append([time_sec, raw_value])
                        sample_count += 1
                        
                        # Print progress every second
                        current_time = time.time()
                        if current_time - last_print_time >= 1.0:
                            elapsed = current_time - start_time
                            current_rate = sample_count / elapsed if elapsed > 0 else 0
                            print_flush(f"Captured {sample_count} samples in {elapsed:.1f} seconds ({current_rate:.1f} Hz)")
                            last_print_time = current_time
                    
                    except ValueError:
                        print_flush(f"Skipping invalid data: {line}")
                        continue
                
                except UnicodeDecodeError:
                    print_flush("Received invalid data from device")
                    continue
    
    except KeyboardInterrupt:
        print_flush("\nRecording stopped by user.")
    finally:
        ser.close()
        print_flush("Serial port closed.")
    
    # Save data to CSV
    if data:
        try:
        with open(output_file, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Time (s)', 'Raw ECG Value'])
            writer.writerows(data)
        
            total_time = data[-1][0] - data[0][0]
            actual_rate = len(data) / total_time if total_time > 0 else 0
            
            print_flush(f"\nRecording Summary:")
            print_flush(f"- Total samples: {sample_count}")
            print_flush(f"- Recording duration: {total_time:.1f} seconds")
            print_flush(f"- Average sampling rate: {actual_rate:.1f} Hz")
            print_flush(f"- Data saved to: {output_file}")
        return True
        except Exception as e:
            print_flush(f"Error saving data to file: {e}")
            return False
    else:
        print_flush("No data was captured. Please check if:")
        print_flush("1. The electrodes are properly connected")
        print_flush("2. The ESP32 is powered and running")
        print_flush("3. The correct Arduino sketch (ecg_ad8232.ino) is uploaded")
        return False

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Capture raw ECG data from ESP32 with AD8232 sensor')
    parser.add_argument('--port', type=str, default=None,
                        help='Serial port (e.g., COM6, /dev/ttyUSB0)')
    parser.add_argument('--baud', type=int, default=115200,
                        help='Baud rate (default: 115200)')
    parser.add_argument('--duration', type=float, default=30.0,
                        help='Recording duration in seconds (default: 30.0)')
    parser.add_argument('--output', type=str, default=None,
                        help='Output CSV file (default: ecg_data_YYYYMMDD_HHMMSS.csv)')
    
    args = parser.parse_args()
    
    # Use COM6 if no port specified
    if args.port is None:
        args.port = 'COM6'
    
    # Determine output file
    if args.output is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.output = f"ecg_raw_data_{timestamp}.csv"
    
    # Capture data
    capture_raw_data(args.port, args.baud, args.duration, args.output)

if __name__ == "__main__":
    main() 