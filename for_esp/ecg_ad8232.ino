#define ECG_PIN 35   // AD8232 OUTPUT to ESP32 ADC pin
#define LO_PLUS 32   // LO+ pin (lead-off detection)
#define LO_MINUS 33  // LO- pin (lead-off detection)

// Signal processing parameters
const int SAMPLES_TO_AVERAGE = 8;     // For basic noise reduction
const float GAIN = 20.0;              // Amplification factor for low signals

// Moving average filter
float samples[SAMPLES_TO_AVERAGE];
int sampleIndex = 0;
float filteredValue = 0;

// DC removal
float dcLevel = 0;
const float DC_ALPHA = 0.95;  // DC removal filter coefficient

void setup() {
  Serial.begin(115200);
  pinMode(ECG_PIN, INPUT);
  pinMode(LO_PLUS, INPUT);
  pinMode(LO_MINUS, INPUT);

  // Initialize sample buffer
  for (int i = 0; i < SAMPLES_TO_AVERAGE; i++) {
    samples[i] = 0;
  }

  Serial.println("ECG Raw Data Monitor Started");
  // Only output the raw value for compatibility with Python script
  Serial.println("raw");
}

void loop() {
  // Check electrode connection
  if (digitalRead(LO_PLUS) == HIGH || digitalRead(LO_MINUS) == HIGH) {
    Serial.println("Leads off!");
    delay(10);
    return;
  }

  // Read raw ECG value
  float rawValue = analogRead(ECG_PIN);

  // DC removal (high-pass filter)
  dcLevel = (DC_ALPHA * dcLevel) + ((1 - DC_ALPHA) * rawValue);
  float dcRemoved = rawValue - dcLevel;

  // Amplify the signal
  float amplifiedValue = dcRemoved * GAIN;

  // Simple moving average filter
  samples[sampleIndex] = amplifiedValue;
  sampleIndex = (sampleIndex + 1) % SAMPLES_TO_AVERAGE;

  float sum = 0;
  for (int i = 0; i < SAMPLES_TO_AVERAGE; i++) {
    sum += samples[i];
  }
  filteredValue = sum / SAMPLES_TO_AVERAGE;

  // Output only the raw value for compatibility with Python script
  Serial.println(rawValue);

  delayMicroseconds(2500);  // 400Hz sampling rate
}