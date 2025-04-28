# ECG Generator, Analyzer, and Data Capture System

This project provides tools for:
1. Generating synthetic maternal and fetal ECG signals with noise
2. Analyzing ECG signals to detect maternal and fetal R peaks and calculate heart rates
3. Capturing real ECG data from an AD8232 sensor connected to an ESP32

## Setup

1. Make sure you have Python 3.7+ installed on your system.

2. Install the required dependencies:
   ```
   py -m pip install -r requirements.txt
   ```

## Quick Start Guide

Here's how to quickly get started with the ECG analysis system:

1. **Generate Sample ECG Data** (if you don't have real data):
   ```
   py ecg_generator.py 

   ```

2. **Analyze ECG Data**:
   ```
   py ecg_analyzer.py --input ecg_data.csv --output analysis_results.csv
   ```

3. **View Results**:
   - Two plots will appear showing the ECG signal and heart rates
   - Check `analysis_results.csv` for detailed results

For real ECG data capture:
1. Set up the hardware as described in the "Hardware Setup" section
2. Upload Arduino code to ESP32
3. Run the capture script:
   ```
   py for_esp/ecg_data_capture.py --port COM3 --duration 30 --output real_ecg.csv
   ```
4. Analyze the captured data:
   ```
   py ecg_analyzer.py --input ecg_data.csv --output real_ecg_analysis.csv
   ```

## Running the ECG Generator

The ECG generator creates synthetic maternal and fetal ECG signals with noise. To run it:

```
py ecg_generator.py
```

This will generate a CSV file containing:
- Time (s)
- Raw ECG Value

## Running the ECG Analyzer

The ECG analyzer detects maternal and fetal R peaks and calculates heart rates from an ECG signal. To run it:

```
py ecg_analyzer.py --input ecg_data.csv --output analysis_results.csv
```

Parameters:
- `--input`: Input CSV file containing ECG data (default: ecg_data.csv)
- `--output`: Output CSV file for analysis results (default: ecg_analysis_results.csv)
- `--sampling-rate`: Sampling rate in Hz (if not specified, will be estimated from the data)
- `--window-size`: Window size for heart rate calculation in seconds (default: 10)

The analyzer will:
1. Load the ECG data from the CSV file
2. Detect maternal R peaks (larger amplitude, slower rate)
3. Detect fetal R peaks (smaller amplitude, faster rate)
4. Calculate heart rates for both maternal and fetal signals
5. Display two plots:
   - ECG signal with detected maternal (red) and fetal (green) R peaks
   - Maternal and fetal heart rates over time
6. Save analysis results to a CSV file containing:
   - Summary information (sampling rate, average heart rates)
   - Maternal R peak locations and values
   - Fetal R peak locations and values
   - Heart rates over time for both signals

The analyzer automatically handles lead-off conditions (when electrodes are disconnected) by:
- Skipping R peak detection during lead-off periods
- Highlighting lead-off periods in red on the plot
- Only calculating heart rates from valid ECG data

## Capturing Real ECG Data

The project includes tools for capturing real ECG data from an AD8232 sensor connected to an ESP32.

### Hardware Setup

1. Connect the AD8232 ECG sensor to the ESP32:
   - AD8232 OUTPUT → ESP32 GPIO 35
   - AD8232 LO+ → ESP32 GPIO 32
   - AD8232 LO- → ESP32 GPIO 33
   - AD8232 3.3V → ESP32 3.3V
   - AD8232 GND → ESP32 GND

2. Connect the ECG electrodes to the AD8232 sensor:
   - RA (Right Arm) → AD8232 +
   - LA (Left Arm) → AD8232 -
   - RL (Right Leg) → AD8232 LO

### Uploading the Arduino Code

1. Open the `for_esp/ecg_ad8232.ino` file in the Arduino IDE
2. Select your ESP32 board from the Tools menu
3. Upload the code to your ESP32

### Capturing ECG Data

To capture ECG data from the sensor:
palitan yung com port sa naka saksak na port 
```
py for_esp/ecg_data_capture.py --port COM1 --duration 30 --output ecg_data.csv
```

Parameters:
- `--port`: Serial port (e.g., COM3, /dev/ttyUSB0)
- `--baud`: Baud rate (default: 115200)
- `--duration`: Recording duration in seconds (default: 30.0)
- `--output`: Output CSV file (default: ecg_data_YYYYMMDD_HHMMSS.csv)

If you don't specify a port, the script will list available ports and let you select one.

## Using the Functions in Your Code

You can also import and use the functions in your own Python scripts:

```python
from ecg_analyzer import analyze_ecg, plot_analysis

# Load ECG data
t, ecg, sampling_rate = load_ecg_from_csv('ecg_data.csv')

# Analyze ECG
(maternal_peaks, fetal_peaks, 
 maternal_heart_rates, fetal_heart_rates,
 maternal_times, fetal_times,
 maternal_avg_hr, fetal_avg_hr,
 lead_off_mask) = analyze_ecg(ecg, sampling_rate)

# Plot results
plot_analysis(t, ecg, maternal_peaks, fetal_peaks,
             maternal_heart_rates, fetal_heart_rates,
             maternal_times, fetal_times,
             maternal_avg_hr, fetal_avg_hr,
             lead_off_mask)
```

## Parameters

### ECG Analyzer Parameters:
- `min_distance`: Minimum distance between maternal R peaks (0.6s, ~100 BPM max)
- `min_distance_fetal`: Minimum distance between fetal R peaks (0.3s, ~200 BPM max)
- `prominence`: Minimum prominence for maternal peaks (0.5)
- `prominence_fetal`: Minimum prominence for fetal peaks (0.2)
- `window_size`: Size of the window for calculating moving average in seconds (default: 10)

### CSV File Format

Input CSV file format:
```
Time (s),Raw ECG Value
0.000,2048
0.002,2052
...
```

Output CSV file format:
```
ECG Analysis Results
Sampling Rate (Hz),400
Maternal Average Heart Rate (BPM),75.2
Fetal Average Heart Rate (BPM),142.8
Number of Maternal R Peaks,125
Number of Fetal R Peaks,237

Maternal R Peaks
Index,Time (s),Raw Value
1,0.824,3245
...

Fetal R Peaks
Index,Time (s),Raw Value
1,0.412,2856
...

Heart Rates
Time (s),Maternal HR (BPM),Fetal HR (BPM)
5.000,74.8,143.2
...
``` 