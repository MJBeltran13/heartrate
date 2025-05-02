# Heart Rate Monitoring System

This project implements a dual heart rate monitoring system using an ESP32 microcontroller and the AD8232 ECG sensor. It's designed to detect and measure both maternal and fetal heart rates.

## Hardware Requirements

- ESP32 development board
- AD8232 ECG sensor (Single Lead Heart Rate Monitor)
- Electrodes compatible with the AD8232
- USB cable for ESP32 programming
- Power source for portable operation (optional)

## Software Requirements

- Arduino IDE (1.8.x or later)
- Required Arduino libraries:
  - WiFi.h
  - HTTPClient.h
  - time.h

## Installation

1. Clone this repository or download the source files
2. Open `latest_ecg_client_request.ino` in the Arduino IDE
3. Install any required libraries via the Arduino Library Manager
4. Configure your Wi-Fi credentials and Firebase settings in the code:
   ```cpp
   // Replace with your Wi-Fi credentials
   const char* ssid = "YOUR_WIFI_SSID";
   const char* password = "YOUR_WIFI_PASSWORD";

   // Replace with your Firebase URL and authentication key
   const String FIREBASE_URL = "YOUR_FIREBASE_URL";
   const String FIREBASE_AUTH = "YOUR_FIREBASE_AUTH_KEY";
   ```
5. Connect your ESP32 to your computer
6. Select the correct board and port in the Arduino IDE
7. Upload the sketch to your ESP32

## Connecting the AD8232 to ESP32

| AD8232 Pin | ESP32 Pin |
|------------|-----------|
| GND        | GND       |
| 3.3V       | 3.3V      |
| OUTPUT     | Pin 35 (Analog input) |
| LO-        | Not connected* |
| LO+        | Not connected* |

*The LO- and LO+ pins can be connected to ESP32 digital pins if you want to implement lead-off detection using GPIO pins rather than the current analog value detection method.

## Electrode Placement

For optimal signal quality:
- Ensure skin is clean and free of oils
- Place electrodes according to the manufacturer's recommendations
- For maternal ECG: Standard 3-lead placement
- For fetal ECG: Refer to medical guidelines or your healthcare provider

## Operation

Once powered on, the ESP32 will:
1. Connect to the configured Wi-Fi network
2. Synchronize time with an NTP server
3. Begin reading ECG data from the AD8232 sensor
4. Process the raw signals to detect both maternal and fetal heart rates
5. Transmit the data to Firebase for storage/visualization
6. Output diagnostic information via the Serial Monitor (115200 baud)

## Adjusting Parameters

The code includes several parameters that can be adjusted to optimize heart rate detection:

```cpp
// ECG Processing Constants
const int SAMPLING_RATE = 200;  // Hz - Typical ECG sampling rate
const int BUFFER_SIZE = 32;     // Number of samples for filtering

// Peak Detection Parameters 
const int MATERNAL_MIN_DISTANCE = (SAMPLING_RATE * 0.6);
const int FETAL_MIN_DISTANCE = (SAMPLING_RATE * 0.4);
const float MATERNAL_PROMINENCE = 0.5;
const float FETAL_PROMINENCE = 0.15;
```

- `SAMPLING_RATE`: Higher values give better resolution but require more processing
- `BUFFER_SIZE`: Larger buffers give better filtering but increase latency
- `MATERNAL/FETAL_MIN_DISTANCE`: Controls maximum heart rate (lower = higher max BPM)
- `MATERNAL/FETAL_PROMINENCE`: Adjusts sensitivity to peaks (lower = more sensitive)

## Data Visualization and Storage

The device sends data to a Firebase Realtime Database in the following format:

```json
{
  "deviceId": "esp32",
  "bpm": 120,
  "timestamp": "2023-05-25T12:34:56",
  "rawEcg": 2048,
  "smoothedEcg": 2050
}
```

You can create a web or mobile application to visualize this data in real-time.

## Troubleshooting

- **No Wi-Fi Connection**: Check your SSID and password
- **"Lead-off detected"**: Check electrode placement and connections
- **No heart rate detected**: Adjust prominence and min_distance parameters
- **Inconsistent readings**: Try repositioning electrodes or adjusting filter parameters
- **High noise levels**: Check for electrical interference sources nearby

## Data Capture with Python

You can use the included Python script to capture ECG data directly from the ESP32 for analysis:

```bash
python ecg_data_capture.py --port COM6 --duration 60
```

See the [Data Capture Documentation](data_capture.md) for more details.

## License

[Specify your license here, e.g., MIT, GPL, etc.]

## Acknowledgments

- AD8232 Heart Rate Monitor by SparkFun
- ESP32 Community and Documentation
- [Add any other acknowledgments here] 