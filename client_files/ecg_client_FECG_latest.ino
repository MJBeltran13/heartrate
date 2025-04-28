#include <WiFi.h>
#include <HTTPClient.h>
#include <time.h>

// --- Wi-Fi Configuration ---
const char* ssid = "PLDTHOMEFIBRgky9c";
const char* password = "PLDTWIFIry2fp";

// --- Firebase Configuration ---
const String FIREBASE_URL = "https://ecgdata-f042a-default-rtdb.asia-southeast1.firebasedatabase.app/ecg_readings.json";
const String FIREBASE_AUTH = "AIzaSyA0OGrnWnNx0LDPGzDZHdrzajiRGEjr3AM";

// --- Time Configuration ---
const char* ntpServer = "pool.ntp.org";
const long gmtOffset_sec = 0;
const int daylightOffset_sec = 0;

// --- Pin Definitions ---
#define AD8232_OUTPUT 35

// --- ECG Processing Constants ---
const int SAMPLING_RATE = 200;  // Hz
const int BUFFER_SIZE = 32;     // Buffer for filtering
const float NYQUIST = SAMPLING_RATE / 2.0;

// Constants from analyzer2.py
const int MATERNAL_MIN_DISTANCE = (SAMPLING_RATE * 0.6);  // ~100 BPM max
const int FETAL_MIN_DISTANCE = (SAMPLING_RATE * 0.3);     // ~200 BPM max
const float MATERNAL_PROMINENCE = 0.5;
const float FETAL_PROMINENCE = 0.2;

// Circular buffers for filtering
float ecgBuffer[BUFFER_SIZE];
int bufferIndex = 0;

// Peak detection variables
unsigned long lastMaternalPeak = 0;
unsigned long lastFetalPeak = 0;
bool maternalPeakDetected = false;
bool fetalPeakDetected = false;
int maternalBpm = 0;
int fetalBpm = 0;

void setup() {
  Serial.begin(115200);

  // Initialize buffer
  for(int i = 0; i < BUFFER_SIZE; i++) {
    ecgBuffer[i] = 0;
  }

  // Connect to Wi-Fi
  WiFi.begin(ssid, password);
  Serial.print("Connecting to Wi-Fi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n✅ Connected to Wi-Fi");
  Serial.println("IP Address: " + WiFi.localIP().toString());

  // Sync time
  configTime(gmtOffset_sec, daylightOffset_sec, ntpServer);
  struct tm timeinfo;
  if (!getLocalTime(&timeinfo)) {
    Serial.println("❌ Failed to get time");
  }
}

float bandpassFilter(int rawEcg, bool isFetalFilter) {
  // Update circular buffer
  ecgBuffer[bufferIndex] = rawEcg;
  bufferIndex = (bufferIndex + 1) % BUFFER_SIZE;
  
  float filtered = 0;
  
  // Approximate Butterworth filter using weighted moving average
  // Weights are calculated based on frequency response
  for (int i = 0; i < BUFFER_SIZE; i++) {
    float weight;
    if (isFetalFilter) {
      // Fetal: 10-40 Hz bandpass approximation
      weight = 0.03 * (1 - abs(i - BUFFER_SIZE/2.0)/(BUFFER_SIZE/2.0));
    } else {
      // Maternal: 5-15 Hz bandpass approximation
      weight = 0.05 * (1 - abs(i - BUFFER_SIZE/2.0)/(BUFFER_SIZE/2.0));
    }
    filtered += ecgBuffer[(bufferIndex - i + BUFFER_SIZE) % BUFFER_SIZE] * weight;
  }
  
  return filtered;
}

void detectPeaks(float filteredEcg, bool isFetal) {
  static float maxValue = 0;
  static float minValue = 4095;
  unsigned long currentTime = millis();
  
  // Update min/max for adaptive thresholding
  if (filteredEcg > maxValue) maxValue = filteredEcg;
  if (filteredEcg < minValue) minValue = filteredEcg;
  
  float prominence = isFetal ? FETAL_PROMINENCE : MATERNAL_PROMINENCE;
  float threshold = minValue + (maxValue - minValue) * prominence;
  
  if (isFetal) {
    // Fetal peak detection
    if (filteredEcg > threshold && !fetalPeakDetected &&
        (currentTime - lastFetalPeak) >= FETAL_MIN_DISTANCE &&
        (currentTime - lastMaternalPeak) >= (SAMPLING_RATE * 0.1)) {  // 100ms from maternal
      
      fetalPeakDetected = true;
      if (lastFetalPeak != 0) {
        unsigned long interval = currentTime - lastFetalPeak;
        fetalBpm = 60000 / interval;
      }
      lastFetalPeak = currentTime;
    } else if (filteredEcg < threshold * 0.8) {
      fetalPeakDetected = false;
    }
  } else {
    // Maternal peak detection
    if (filteredEcg > threshold && !maternalPeakDetected &&
        (currentTime - lastMaternalPeak) >= MATERNAL_MIN_DISTANCE) {
      
      maternalPeakDetected = true;
      if (lastMaternalPeak != 0) {
        unsigned long interval = currentTime - lastMaternalPeak;
        maternalBpm = 60000 / interval;
      }
      lastMaternalPeak = currentTime;
    } else if (filteredEcg < threshold * 0.8) {
      maternalPeakDetected = false;
    }
  }
  
  // Decay max/min values slowly for adaptive threshold
  maxValue *= 0.995;
  minValue *= 1.005;
}

void loop() {
  // --- Read ECG ---
  int rawEcg = analogRead(AD8232_OUTPUT);
  
  // Check for lead-off condition
  if (rawEcg >= 4095) {
    Serial.println("Lead-off detected");
    delay(100);
    return;
  }
  
  // --- Apply filters and detect peaks ---
  float maternalFiltered = bandpassFilter(rawEcg, false);
  float fetalFiltered = bandpassFilter(rawEcg, true);
  
  detectPeaks(maternalFiltered, false);  // Detect maternal peaks first
  detectPeaks(fetalFiltered, true);      // Then detect fetal peaks
  
  // --- Get Timestamp ---
  time_t now = time(nullptr);
  struct tm* timeinfo = localtime(&now);
  char timestamp[30];
  strftime(timestamp, sizeof(timestamp), "%Y-%m-%dT%H:%M:%S", timeinfo);

  // --- Create JSON Payload ---
  String json = "{";
  json += "\"deviceId\":\"esp32\",";
  json += "\"bpm\":" + String(fetalBpm) + ",";  // Using fetal BPM as main BPM
  json += "\"timestamp\":\"" + String(timestamp) + "\",";
  json += "\"rawEcg\":" + String(rawEcg) + ",";
  json += "\"smoothedEcg\":" + String((int)fetalFiltered);  // Using fetal filtered signal
  json += "}";

  // --- Send to Firebase ---
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(FIREBASE_URL + "?auth=" + FIREBASE_AUTH);
    http.addHeader("Content-Type", "application/json");

    int httpResponseCode = http.PUT(json);

    if (httpResponseCode > 0) {
      Serial.println("✅ Data sent successfully!");
      Serial.println("Fetal BPM: " + String(fetalBpm));
      Serial.println("Maternal BPM: " + String(maternalBpm));
    } else {
      Serial.print("❌ Error sending data: ");
      Serial.println(httpResponseCode);
    }

    http.end();
  } else {
    Serial.println("❌ Wi-Fi disconnected. Trying to reconnect...");
    reconnectWiFi();
  }

  delay(5000); // Wait 5 seconds
}

// --- Wi-Fi Reconnect Helper ---
void reconnectWiFi() {
  WiFi.disconnect();
  WiFi.reconnect();
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n✅ Reconnected to Wi-Fi!");
}