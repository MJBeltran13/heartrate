#define AD8232_OUTPUT 35  // AD8232 OUTPUT to ESP32 ADC pin
#define LO_PLUS 32       // LO+ pin (lead-off detection)
#define LO_MINUS 33      // LO- pin (lead-off detection)

const int filterWindow = 20;  // Increased window size for better smoothing
int ecgBuffer[filterWindow]; // Array to store recent ECG values
int ecgIndex = 0;
long ecgSum = 0;

int bpmArray[10];        // Array to store BPM values
int bpmIndex = 0;
long previousTime = 0;
bool pulseDetected = false;

void setup() {
  Serial.begin(115200);
  pinMode(AD8232_OUTPUT, INPUT);
  pinMode(LO_PLUS, INPUT);
  pinMode(LO_MINUS, INPUT);

  // Initialize ECG buffer
  for (int i = 0; i < filterWindow; i++) {
    ecgBuffer[i] = 0;
  }

  // Initialize BPM array
  for (int i = 0; i < 10; i++) {
    bpmArray[i] = -1;
  }

  Serial.println("Waiting for fetal heartbeat...");
}

void loop() {
  int ecgValue = analogRead(AD8232_OUTPUT);  // Read filtered ECG
  int normalizedEcg = ecgValue - 512;        // Normalize around 0

  // Apply moving average filter
  ecgSum -= ecgBuffer[ecgIndex]; 
  ecgBuffer[ecgIndex] = normalizedEcg; 
  ecgSum += normalizedEcg;
  ecgIndex = (ecgIndex + 1) % filterWindow;
  int smoothedEcg = ecgSum / filterWindow;

  // Adaptive peak detection threshold
  static int baseline = 0;
  baseline = (baseline * 9 + smoothedEcg) / 10;
  int peakThreshold = baseline + 10; // Lowered threshold for fECG

  // Check lead-off detection
  if (digitalRead(LO_PLUS) == 1 || digitalRead(LO_MINUS) == 1) {
    resetBPMArray();
    Serial.println("Lead-off detected");
    delay(500);
    return;
  }

  // Detect fetal heartbeats using peak detection
  long currentTime = millis();
  if (smoothedEcg > peakThreshold && !pulseDetected) {
    pulseDetected = true;
    long timeBetweenBeats = currentTime - previousTime;
    previousTime = currentTime;

    // Adjusted time range for fetal BPM (120–160 BPM)
    if (timeBetweenBeats > 375 && timeBetweenBeats < 500) {
      int bpm = 60000 / timeBetweenBeats;
      addBpmToArray(bpm);
      int averageBPM = getAverageBPM();
      if (averageBPM >= 120 && averageBPM <= 160) {
        Serial.print("Fetal BPM: ");
        Serial.println(averageBPM);  // Print BPM
        Serial.print("fECG: ");
        Serial.print(smoothedEcg);
        Serial.print("\tFetal BPM: ");
        Serial.println(averageBPM);  // For Serial Plotter
      }
    }
  }

  if (smoothedEcg < peakThreshold) {
    pulseDetected = false;
  }

  delay(10);
}

void addBpmToArray(int bpm) {
  bpmArray[bpmIndex] = bpm;
  bpmIndex = (bpmIndex + 1) % 10;
}

int getAverageBPM() {
  int sum = 0, count = 0;
  for (int i = 0; i < 10; i++) {
    if (bpmArray[i] != -1) {
      sum += bpmArray[i];
      count++;
    }
  }
  return count > 0 ? sum / count : 0;
}

void resetBPMArray() {
  for (int i = 0; i < 10; i++) {
    bpmArray[i] = -1;
  }
  bpmIndex = 0;
}