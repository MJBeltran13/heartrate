#!/usr/bin/env python3
"""
ECG Data Capture Tool for Heart Rate Monitoring

This script captures ECG data from an ESP32 running the latest_ecg_client_request.ino sketch
and saves it to a CSV file. The script parses both raw ECG values and calculated heart rates.

Usage:
    python ecg_data_capture.py [--port PORT] [--baud BAUD] [--duration DURATION] [--output OUTPUT]

Example:
    python ecg_data_capture.py --port COM6 --baud 115200 --duration 60 --output ecg_data.csv
"""

import argparse
import serial
import time
import csv
import json
import sys
from datetime import datetime

def print_flush(*args, **kwargs):
    """Print and flush immediately."""
    print(*args, **kwargs)
    sys.stdout.flush()

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
            selection = input("Select port number (or press Enter to use the first port): ")
            if not selection:
                return ports[0]
            
            index = int(selection) - 1
            if 0 <= index < len(ports):
                return ports[index]
            else:
                print("Invalid selection. Please try again.")
        except ValueError:
            print("Please enter a number.")

def capture_ecg_data(port, baud_rate, duration, output_file):
    """Capture ECG data from the ESP32 and save to CSV."""
    print_flush(f"Attempting to connect to ESP32 on {port} at {baud_rate} baud...")
    
    try:
        ser = serial.Serial(port, baud_rate, timeout=1)
    except serial.SerialException as e:
        print_flush(f"Error opening serial port {port}: {e}")
        print_flush("Please check if:")
        print_flush("1. The ESP32 is properly connected")
        print_flush("2. No other program is using the port")
        print_flush("3. You have the correct port number")
        return False
    
    print_flush("Successfully connected to ESP32!")
    print_flush("Waiting for device communication...")
    
    # Wait for ESP32 to initialize
    time.sleep(2)
    
    # Prepare for data capture
    start_time = time.time()
    data = []
    sample_count = 0
    last_print_time = start_time
    
    print_flush(f"Starting recording for {duration} seconds...")
    print_flush("Press Ctrl+C to stop recording early.")
    
    try:
        while time.time() - start_time < duration:
            if ser.in_waiting:
                try:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    
                    # Skip empty lines
                    if not line:
                        continue
                    
                    # Check for lead-off detection
                    if "Lead-off detected" in line:
                        print_flush("Warning: Leads are not properly connected!")
                        elapsed = time.time() - start_time
                        data.append([elapsed, None, None, None, "Lead-off detected"])
                        continue
                    
                    # Check for WiFi connection messages
                    if "Connected to Wi-Fi" in line or "Reconnected to Wi-Fi" in line:
                        print_flush(f"ESP32: {line}")
                        continue
                    
                    # Check for data sent confirmation
                    if "Data sent successfully" in line:
                        print_flush(f"ESP32: {line}")
                        continue
                    
                    # Try to parse BPM information
                    if "Fetal BPM:" in line:
                        try:
                            fetal_bpm = int(line.split(":")[1].strip())
                            print_flush(f"Fetal BPM: {fetal_bpm}")
                            continue
                        except (ValueError, IndexError):
                            continue
                    
                    if "Maternal BPM:" in line:
                        try:
                            maternal_bpm = int(line.split(":")[1].strip())
                            print_flush(f"Maternal BPM: {maternal_bpm}")
                            continue
                        except (ValueError, IndexError):
                            continue
                    
                    # Try to parse JSON payload
                    if line.startswith("{") and line.endswith("}"):
                        try:
                            json_data = json.loads(line)
                            
                            timestamp = json_data.get("timestamp", datetime.now().isoformat())
                            bpm = json_data.get("bpm", None)
                            raw_ecg = json_data.get("rawEcg", None)
                            smoothed_ecg = json_data.get("smoothedEcg", None)
                            
                            elapsed = time.time() - start_time
                            data.append([elapsed, raw_ecg, smoothed_ecg, bpm, timestamp])
                            sample_count += 1
                            
                            # Print progress every second
                            current_time = time.time()
                            if current_time - last_print_time >= 1.0:
                                print_flush(f"Captured {sample_count} samples in {elapsed:.1f} seconds")
                                if bpm:
                                    print_flush(f"Current BPM: {bpm}")
                                last_print_time = current_time
                                
                        except json.JSONDecodeError:
                            # Not valid JSON, might be other debug output
                            print_flush(f"Debug: {line}")
                    else:
                        # Other debug output
                        print_flush(f"Debug: {line}")
                
                except Exception as e:
                    print_flush(f"Error processing data: {e}")
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
                writer.writerow(['Time (s)', 'Raw ECG', 'Filtered ECG', 'BPM', 'Timestamp'])
                writer.writerows(data)
            
            total_time = data[-1][0] - data[0][0] if len(data) > 1 else 0
            
            print_flush(f"\nRecording Summary:")
            print_flush(f"- Total samples: {sample_count}")
            print_flush(f"- Recording duration: {total_time:.1f} seconds")
            print_flush(f"- Data saved to: {output_file}")
            return True
        except Exception as e:
            print_flush(f"Error saving data to file: {e}")
            return False
    else:
        print_flush("No data was captured. Please check if:")
        print_flush("1. The electrodes are properly connected")
        print_flush("2. The ESP32 is powered and running")
        print_flush("3. The correct firmware is uploaded to the ESP32")
        return False

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Capture ECG data from ESP32 with AD8232 sensor')
    parser.add_argument('--port', type=str, default=None,
                        help='Serial port (e.g., COM6, /dev/ttyUSB0)')
    parser.add_argument('--baud', type=int, default=115200,
                        help='Baud rate (default: 115200)')
    parser.add_argument('--duration', type=float, default=60.0,
                        help='Recording duration in seconds (default: 60.0)')
    parser.add_argument('--output', type=str, default=None,
                        help='Output CSV file (default: ecg_data_YYYYMMDD_HHMMSS.csv)')
    
    args = parser.parse_args()
    
    # If no port specified, list and select available ports
    if args.port is None:
        ports = list_serial_ports()
        if ports:
            args.port = select_port(ports)
        else:
            print_flush("No serial ports available. Exiting.")
            return
    
    # Determine output file
    if args.output is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.output = f"ecg_data_{timestamp}.csv"
    
    # Capture data
    capture_ecg_data(args.port, args.baud, args.duration, args.output)

if __name__ == "__main__":
    main() 