/*
 * Lycée Academics RFID attendance terminal
 * ESP32 + MFRC522 + I2C 20x4 LCD + red/yellow/green LEDs
 *
 * Uses the existing Flask endpoints:
 *   POST /student/rfid-login  JSON {"uid":"..."}, header X-Device-Token
 *   GET  /student/rfid-status header X-Device-Token
 *
 * This is a school-wide reader: do not set RFID_DEVICE_CLASS on the server.
 * The server looks up each card's registered student/class and owns all
 * attendance-window and status decisions.
 */

#include <WiFi.h>
#include <WiFiClient.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <SPI.h>
#include <MFRC522.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

// ---------- Site configuration: edit these values before flashing ----------
const char *WIFI_SSID = "YOUR_WIFI_NAME";
const char *WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// Example: http://192.168.1.20:5000  (local LAN only)
// Production should use https:// and the issuing CA certificate below.
const char *SERVER_BASE_URL = "http://192.168.1.20:5000";
const char *DEVICE_TOKEN = "vF6xDw2Rh-0NAIWaezrW4QNVajQrm7J78Cn1IOnEO98";

const char *DEVICE_ID = "MAIN_GATE_01"; // Unique label shown in scan history

// Paste the trusted root/intermediate CA PEM for your HTTPS server here.
// Leave empty only when using plain HTTP on a trusted private LAN.
static const char ROOT_CA_CERT[] PROGMEM = R"CERT(
-----BEGIN CERTIFICATE-----
PASTE_YOUR_SERVER_CA_CERTIFICATE_HERE
-----END CERTIFICATE-----
)CERT";

// ---------- Wiring defaults (change to match your board) -------------------
constexpr uint8_t PIN_RFID_SS = 5;   // RC522 SDA / SS
constexpr uint8_t PIN_RFID_RST = 27; // RC522 RST; separate from I2C SCL
constexpr uint8_t PIN_SPI_SCK = 18;
constexpr uint8_t PIN_SPI_MISO = 19;
constexpr uint8_t PIN_SPI_MOSI = 23;
constexpr uint8_t PIN_I2C_SDA = 21;
constexpr uint8_t PIN_I2C_SCL = 22;

constexpr uint8_t PIN_LED_RED = 32;
constexpr uint8_t PIN_LED_YELLOW = 26;
constexpr uint8_t PIN_LED_GREEN = 25;
constexpr uint8_t LCD_I2C_ADDRESS = 0x27; // Common alternatives: 0x3F
constexpr uint8_t LCD_COLUMNS = 20;       // Change to 16 for a 16x2 LCD
constexpr uint8_t LCD_ROWS = 4;           // Change to 2 for a 16x2 LCD

constexpr unsigned long WIFI_RETRY_MS = 10000;
constexpr unsigned long STATUS_POLL_MS = 60000;
constexpr unsigned long CARD_REPEAT_GUARD_MS = 2500;
constexpr unsigned long RESULT_SCREEN_MS = 5000;
constexpr uint16_t HTTP_TIMEOUT_MS = 6000;

MFRC522 reader(PIN_RFID_SS, PIN_RFID_RST);
LiquidCrystal_I2C lcd(LCD_I2C_ADDRESS, LCD_COLUMNS, LCD_ROWS);
WiFiClient plainClient;
WiFiClientSecure secureClient;

unsigned long lastWifiAttempt = 0;
unsigned long lastStatusPoll = 0;
unsigned long resultScreenUntil = 0;
unsigned long lastCardScan = 0;
String lastCardUid;

String apiUrl(const char *path) {
  String base(SERVER_BASE_URL);
  while (base.endsWith("/")) base.remove(base.length() - 1);
  return base + path;
}

void setLeds(bool red, bool yellow, bool green) {
  digitalWrite(PIN_LED_RED, red ? HIGH : LOW);
  digitalWrite(PIN_LED_YELLOW, yellow ? HIGH : LOW);
  digitalWrite(PIN_LED_GREEN, green ? HIGH : LOW);
}

void lcdLine(uint8_t row, String value) {
  if (row >= LCD_ROWS) return;
  value.replace('\r', ' ');
  value.replace('\n', ' ');
  if (value.length() > LCD_COLUMNS) value = value.substring(0, LCD_COLUMNS);
  while (value.length() < LCD_COLUMNS) value += ' ';
  lcd.setCursor(0, row);
  lcd.print(value);
}

void showScreen(const String &line0, const String &line1 = "",
                const String &line2 = "", const String &line3 = "") {
  lcdLine(0, line0);
  if (LCD_ROWS > 1) lcdLine(1, line1);
  if (LCD_ROWS > 2) lcdLine(2, line2);
  if (LCD_ROWS > 3) lcdLine(3, line3);
}

bool secureUrl() {
  return String(SERVER_BASE_URL).startsWith("https://");
}

bool configureHttp(HTTPClient &http, const String &url) {
  http.setConnectTimeout(HTTP_TIMEOUT_MS);
  http.setTimeout(HTTP_TIMEOUT_MS);
  if (secureUrl()) {
    String ca(ROOT_CA_CERT);
    if (ca.indexOf("PASTE_YOUR_SERVER_CA_CERTIFICATE_HERE") >= 0 || ca.length() < 100) {
      Serial.println("HTTPS selected but a real server CA certificate is not configured.");
      return false;
    }
    secureClient.setCACert(ROOT_CA_CERT);
    return http.begin(secureClient, url);
  }
  return http.begin(plainClient, url);
}

bool configured() {
  const String ssid(WIFI_SSID);
  const String password(WIFI_PASSWORD);
  const String token(DEVICE_TOKEN);
  const String base(SERVER_BASE_URL);
  return ssid.length() > 0 && ssid != "YOUR_WIFI_NAME" &&
         password != "YOUR_WIFI_PASSWORD" && token.length() >= 32 &&
         !token.startsWith("REPLACE_WITH_") &&
         (base.startsWith("http://") || base.startsWith("https://"));
}

void beginWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  lastWifiAttempt = millis();
  showScreen("LYCEE ATTENDANCE", "Connecting to Wi-Fi", "Please wait...");
}

void keepWiFiConnected() {
  if (WiFi.status() == WL_CONNECTED) return;
  if (millis() - lastWifiAttempt >= WIFI_RETRY_MS) {
    lastWifiAttempt = millis();
    WiFi.disconnect();
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  }
  setLeds(true, false, false);
  showScreen("Wi-Fi unavailable", "Reconnecting...", "Attendance needs", "server connection");
}

void showScanResult(int httpCode, const String &body, const String &uid) {
  DynamicJsonDocument response(3072);
  DeserializationError parseError = deserializeJson(response, body);
  String status = parseError ? "error" : response["status"].as<String>();
  String message = parseError ? "Invalid server response" : response["message"].as<String>();
  String student = parseError ? "" : response["student"].as<String>();
  String attendance = parseError ? "" : response["attendance_status"].as<String>();
  String className = parseError ? "" : response["class_name"].as<String>();

  Serial.printf("RFID API HTTP %d, status=%s, uid=%s\n", httpCode, status.c_str(), uid.c_str());
  if (message.length()) Serial.println(message);

  if (status == "success" && attendance.equalsIgnoreCase("Present")) {
    setLeds(false, false, true);
    showScreen("PRESENT", student, className, message);
  } else if (status == "success" && attendance.equalsIgnoreCase("Late")) {
    setLeds(false, true, false);
    showScreen("LATE ARRIVAL", student, className, message);
  } else if (status == "success" && attendance.equalsIgnoreCase("Absent")) {
    setLeds(true, false, false);
    showScreen("ATTENDANCE: ABSENT", student, className, message);
  } else if (status == "meeting_checkin") {
    setLeds(false, false, true);
    showScreen("MEETING CHECK-IN", student, className, message);
  } else if (status == "pending_registration") {
    setLeds(false, true, false);
    showScreen("CARD NOT ASSIGNED", "UID queued for", "office registration", uid);
  } else if (status == "outside_window" || status == "access_denied") {
    setLeds(false, true, false);
    showScreen("OUTSIDE SCAN TIME", student, className, message);
  } else {
    setLeds(true, false, false);
    showScreen("SCAN NOT ACCEPTED", student.length() ? student : status,
               message.length() ? message : ("HTTP " + String(httpCode)), uid);
  }
  resultScreenUntil = millis() + RESULT_SCREEN_MS;
}

void submitCard(const String &uid) {
  if (WiFi.status() != WL_CONNECTED) {
    setLeds(true, false, false);
    showScreen("No server link", "Card not submitted", "Please try again");
    resultScreenUntil = millis() + RESULT_SCREEN_MS;
    return;
  }

  HTTPClient http;
  if (!configureHttp(http, apiUrl("/student/rfid-login"))) {
    setLeds(true, false, false);
    showScreen("API configuration", "failed", "Check server URL/CA");
    resultScreenUntil = millis() + RESULT_SCREEN_MS;
    return;
  }
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Device-Token", DEVICE_TOKEN);
  http.addHeader("X-Device-Id", DEVICE_ID);
  StaticJsonDocument<128> payload;
  payload["uid"] = uid;
  String requestBody;
  serializeJson(payload, requestBody);

  showScreen("Card detected", "Sending to school", uid);
  int httpCode = http.POST(requestBody);
  String body = httpCode > 0 ? http.getString() : "";
  http.end();

  if (httpCode <= 0) {
    setLeds(true, false, false);
    showScreen("Server unavailable", "Scan not recorded", "Check network", uid);
    Serial.printf("POST failed: %s\n", HTTPClient::errorToString(httpCode).c_str());
    resultScreenUntil = millis() + RESULT_SCREEN_MS;
    return;
  }
  showScanResult(httpCode, body, uid);
}

void pollSchoolStatus() {
  if (WiFi.status() != WL_CONNECTED) return;
  HTTPClient http;
  if (!configureHttp(http, apiUrl("/student/rfid-status"))) return;
  http.addHeader("X-Device-Token", DEVICE_TOKEN);
  http.addHeader("X-Device-Id", DEVICE_ID);
  int httpCode = http.GET();
  String body = httpCode > 0 ? http.getString() : "";
  http.end();
  lastStatusPoll = millis();

  if (httpCode != 200) {
    Serial.printf("Status poll failed: HTTP %d\n", httpCode);
    return; // Keep the last useful LCD message; a scan gives a clear error.
  }

  DynamicJsonDocument response(3072);
  if (deserializeJson(response, body)) return;
  JsonObject summary = response["class_summary"].as<JsonObject>();
  if (summary.isNull()) return;

  String area = response["class_name"] | "All classes";
  int total = summary["total_students"] | 0;
  int present = summary["present_count"] | 0;
  int late = summary["late_count"] | 0;
  int absent = summary["absent_count"] | 0;
  int unmarked = summary["unmarked_count"] | 0;

  setLeds(false, false, false);
  showScreen(area, "P:" + String(present) + " L:" + String(late) + " A:" + String(absent),
             "Unmarked: " + String(unmarked), "Total: " + String(total) + "  Tap card");
}

String readCardUid() {
  String uid;
  for (byte index = 0; index < reader.uid.size; index++) {
    if (reader.uid.uidByte[index] < 0x10) uid += '0';
    uid += String(reader.uid.uidByte[index], HEX);
  }
  uid.toUpperCase();
  return uid;
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_LED_RED, OUTPUT);
  pinMode(PIN_LED_YELLOW, OUTPUT);
  pinMode(PIN_LED_GREEN, OUTPUT);
  setLeds(false, false, false);

  Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL);
  lcd.init();
  lcd.backlight();
  showScreen("LYCEE RFID", "Starting reader...");

  SPI.begin(PIN_SPI_SCK, PIN_SPI_MISO, PIN_SPI_MOSI, PIN_RFID_SS);
  reader.PCD_Init();
  delay(50);
  reader.PCD_AntennaOn();

  if (!configured()) {
    setLeds(true, false, false);
    showScreen("SETUP REQUIRED", "Edit Wi-Fi, server", "and 32+ char token", "Then flash ESP32");
    Serial.println("Set Wi-Fi credentials, SERVER_BASE_URL, and DEVICE_TOKEN in the sketch.");
    return;
  }
  beginWiFi();
}

void loop() {
  if (!configured()) return;
  if (WiFi.status() != WL_CONNECTED) {
    keepWiFiConnected();
    delay(50);
    return;
  }

  if (millis() - lastStatusPoll >= STATUS_POLL_MS && millis() >= resultScreenUntil) {
    pollSchoolStatus();
  }

  if (reader.PICC_IsNewCardPresent() && reader.PICC_ReadCardSerial()) {
    String uid = readCardUid();
    if (uid != lastCardUid || millis() - lastCardScan >= CARD_REPEAT_GUARD_MS) {
      lastCardUid = uid;
      lastCardScan = millis();
      submitCard(uid);
    }
    reader.PICC_HaltA();
    reader.PCD_StopCrypto1();
  }

  if (resultScreenUntil && millis() >= resultScreenUntil) {
    resultScreenUntil = 0;
    pollSchoolStatus();
  }
  delay(20);
}
