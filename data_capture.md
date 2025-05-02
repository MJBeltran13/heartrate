# ECG Data Capture Documentation

This document provides instructions for capturing ECG data from the ESP32 running the `latest_ecg_client_request.ino` sketch.

## Requirements

- Python 3.6 or higher
- PySerial library (`pip install pyserial`)
- ESP32 with AD8232 ECG sensor running the `latest_ecg_client_request.ino` sketch

## Installation

1. Install the required Python dependencies:
   ```bash
   pip install pyserial
   ```

2. Download the `ecg_data_capture.py` script from this repository

## Usage

The data capture script allows you to collect ECG data directly from the ESP32 for offline analysis or storage. The script connects to the ESP32 via a serial connection, captures the data, and saves it to a CSV file.

### Basic Usage

```bash
python ecg_data_capture.py
```

When run without parameters, the script will:
1. List available serial ports
2. Prompt you to select the appropriate port
3. Record ECG data for 60 seconds (default)
4. Save the data to a timestamped CSV file (e.g., `ecg_data_20230525_123456.csv`)

### Command Line Options

The script accepts several command line options:

```bash
python ecg_data_capture.py --port COM6 --baud 115200 --duration 120 --output my_ecg_data.csv
```

Parameters:
- `--port`: Serial port to use (e.g., COM6, /dev/ttyUSB0)
- `--baud`: Baud rate for serial communication (default: 115200)
- `--duration`: Recording duration in seconds (default: 60)
- `--output`: Output CSV file name (default: `ecg_data_TIMESTAMP.csv`)

## Data Format

The script saves data in a CSV file with the following columns:

| Time (s) | Raw ECG | Filtered ECG | BPM | Timestamp |
|----------|---------|--------------|-----|-----------|
| 0.123    | 2048    | 2050         | 75  | 2023-05-25T12:34:56 |
| 0.556    | 2100    | 2095         | 75  | 2023-05-25T12:34:57 |
| ...      | ...     | ...          | ... | ... |

- **Time (s)**: Elapsed time since recording started (in seconds)
- **Raw ECG**: Raw analog reading from the AD8232 sensor
- **Filtered ECG**: Filtered/smoothed ECG value after signal processing
- **BPM**: Calculated heart rate in beats per minute
- **Timestamp**: ISO 8601 timestamp from the ESP32's internal clock

## Troubleshooting

### Serial Port Issues

If you encounter problems connecting to the ESP32:

1. Make sure the ESP32 is connected to your computer
2. Check that no other program is using the serial port (e.g., Arduino IDE's Serial Monitor)
3. Try a different USB cable or port
4. On Windows, check Device Manager to confirm the correct COM port

### Data Quality Issues

If the captured data appears noisy or incorrect:

1. Check the electrode placement and connections
2. Ensure the subject remains still during recording
3. Move away from sources of electrical interference
4. Check the battery level of the ESP32 if powered by battery

### Other Common Issues

- **Script crashes immediately**: Check if PySerial is properly installed
- **No data captured**: Ensure the ESP32 is running the correct sketch
- **"No such file or directory" error**: Verify the port name is correct

## Data Analysis

Once you've captured ECG data, you can analyze it using:

1. Custom analysis scripts
2. Biomedical signal analysis packages (e.g., NeuroKit2, BioSPPy)
3. General data analysis tools like MATLAB, Python with SciPy, etc.

Example Python code for loading the CSV data:

```python
import pandas as pd
import matplotlib.pyplot as plt

# Load the data
data = pd.read_csv('ecg_data.csv')

# Plot the raw ECG signal
plt.figure(figsize=(12, 6))
plt.plot(data['Time (s)'], data['Raw ECG'])
plt.title('Raw ECG Signal')
plt.xlabel('Time (s)')
plt.ylabel('Amplitude')
plt.grid(True)
plt.show()

# Plot the heart rate over time
plt.figure(figsize=(12, 6))
plt.plot(data['Time (s)'], data['BPM'])
plt.title('Heart Rate')
plt.xlabel('Time (s)')
plt.ylabel('BPM')
plt.grid(True)
plt.show()
```

## Advanced Usage

### Continuous Monitoring

For continuous monitoring over extended periods:

```bash
python ecg_data_capture.py --duration 3600 --output ecg_data_1hour.csv
```

### Batch Processing

You can automate data collection with batch scripts or shell scripts:

```bash
#!/bin/bash
# Capture multiple sessions
python ecg_data_capture.py --duration 60 --output session1.csv
sleep 10
python ecg_data_capture.py --duration 60 --output session2.csv
sleep 10
python ecg_data_capture.py --duration 60 --output session3.csv
``` 