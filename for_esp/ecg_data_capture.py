#!/usr/bin/env python3
"""
ECG Raw Data Capture Tool

This script captures raw ECG data from an Arduino connected to an AD8232 ECG sensor
and saves it to a CSV file.

Usage:
    python ecg_data_capture.py [--port PORT] [--baud BAUD] [--duration DURATION] [--output OUTPUT]

Example:
    python ecg_data_capture.py --port COM3 --baud 115200 --duration 30 --output ecg_data.csv
"""

import argparse
import serial
import time
import csv
import os
import sys
from datetime import datetime

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
    """Capture raw ECG data from the Arduino and save to CSV."""
    print(f"Connecting to {port} at {baud_rate} baud...")
    
    try:
        ser = serial.Serial(port, baud_rate, timeout=1)
    except serial.SerialException as e:
        print(f"Error opening serial port: {e}")
        return False
    
    # Wait for Arduino to reset
    time.sleep(2)
    
    # Clear any existing data
    while ser.in_waiting:
        ser.readline()
    
    # Prepare for data capture
    start_time = time.time()
    data = []
    sample_count = 0
    
    print(f"Recording for {duration} seconds...")
    print("Press Ctrl+C to stop recording early.")
    
    try:
        while time.time() - start_time < duration:
            if ser.in_waiting:
                line = ser.readline().decode('utf-8').strip()
                
                # Skip status updates and debug messages
                if line.startswith("---") or line.startswith("Debug:") or line.startswith("Leads off!"):
                    continue
                
                # Parse CSV data
                try:
                    parts = line.split(',')
                    if len(parts) >= 1:  # We only need the raw ECG value
                        time_sec = time.time() - start_time
                        raw_value = float(parts[0])
                        
                        data.append([time_sec, raw_value])
                        sample_count += 1
                        
                        # Print progress every second
                        if sample_count % 1000 == 0:
                            elapsed = time.time() - start_time
                            print(f"Captured {sample_count} samples in {elapsed:.1f} seconds")
                except (ValueError, IndexError):
                    # Skip invalid lines
                    continue
    
    except KeyboardInterrupt:
        print("\nRecording stopped by user.")
    finally:
        ser.close()
    
    # Save data to CSV
    if data:
        with open(output_file, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Time (s)', 'Raw ECG Value'])
            writer.writerows(data)
        
        print(f"Captured {sample_count} samples")
        print(f"Data saved to {output_file}")
        return True
    else:
        print("No data captured.")
        return False

def main():
    """Main function."""
    args = parse_arguments()
    
    # Determine serial port
    if args.port is None:
        ports = list_serial_ports()
        port = select_port(ports)
        if port is None:
            print("No port selected. Exiting.")
            return
    else:
        port = args.port
    
    # Determine output file
    if args.output is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.output = f"ecg_raw_data_{timestamp}.csv"
    
    # Capture data
    capture_raw_data(port, args.baud, args.duration, args.output)

if __name__ == "__main__":
    main() 