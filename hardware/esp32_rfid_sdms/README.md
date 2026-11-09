# ESP32 RFID attendance terminal

This sketch connects an ESP32, MFRC522 reader, I2C LCD, and three LEDs to the existing Flask attendance APIs. It supports the whole school: the card UID is sent to the server, which finds the registered student and uses the student's class and the school's saved attendance windows. Do not set `RFID_DEVICE_CLASS` when this reader must accept cards from many classes.

## Parts and default wiring

Use an ESP32 DevKit, MFRC522/RC522, 20x4 I2C LCD, three LEDs, and one 220-330 ohm resistor per LED. Share GND across all components.

| Module pin | ESP32 pin |
| --- | --- |
| RC522 SDA / SS | GPIO 5 |
| RC522 SCK | GPIO 18 |
| RC522 MOSI | GPIO 23 |
| RC522 MISO | GPIO 19 |
| RC522 RST | GPIO 27 |
| RC522 3.3V / GND | 3V3 / GND |
| LCD SDA / SCL | GPIO 21 / GPIO 22 |
| Red LED anode through resistor | GPIO 32 |
| Yellow LED anode through resistor | GPIO 26 |
| Green LED anode through resistor | GPIO 25 |
| LED cathodes | GND |

RC522 is a 3.3 V device. Do not connect its VCC to 5 V. ESP32 pins are not 5 V tolerant: if the LCD backpack is powered at 5 V and pulls SDA/SCL up to 5 V, use a bidirectional I2C level shifter. LCD address defaults to `0x27`; change it to `0x3F` if needed. For a 16x2 LCD, set `LCD_COLUMNS` to 16 and `LCD_ROWS` to 2.

## Arduino IDE setup

1. Install ESP32 board support in Arduino IDE and select the correct ESP32 board and port.
2. Install libraries: **MFRC522** (miguelbalboa), **ArduinoJson** (Benoit Blanchon), and **LiquidCrystal_I2C** (a library exposing `LiquidCrystal_I2C` with `init()` and `backlight()`). WiFi, HTTPClient, SPI, and Wire come with the ESP32 board package.
3. Open `esp32_rfid_sdms.ino` and set Wi-Fi SSID/password, `SERVER_BASE_URL`, and `DEVICE_TOKEN` near the top.
4. Set the same long random `RFID_DEVICE_TOKEN` on the Flask server. Keep both real values private; do not commit them.
5. For local HTTP, use the Flask server's LAN address, for example `http://192.168.1.20:5000`, and make sure the ESP32 can reach that host/port. Do not use `localhost` or `127.0.0.1` as the server URL.
6. For production HTTPS, set an `https://` URL and replace the PEM placeholder with the certificate authority chain that validates the server certificate. The sketch refuses HTTPS requests until a real CA certificate is supplied; it does not disable TLS verification.
7. Flash the ESP32 and open Serial Monitor at 115200 baud.

The firmware does not enroll cards. An unassigned UID is queued by the app for staff registration; the red/yellow/green LEDs indicate the result. A student card must be assigned in the app before it can record that student's attendance.

## Existing Flask API contract

Configure `RFID_DEVICE_TOKEN` in the server environment. The app rejects device calls with HTTP 503 when the token is missing and HTTP 401 when the `X-Device-Token` header is wrong.

### Submit a card scan

```http
POST /student/rfid-login
Content-Type: application/json
X-Device-Token: <same secret configured on the server>
X-Device-Id: MAIN_GATE_01

{"uid":"A1B2C3D4"}
```

The firmware normalizes the UID to uppercase hex. The server returns a JSON `status` and message. Common statuses are `success` (with `attendance_status` of `Present`, `Late`, or `Absent`), `meeting_checkin`, `pending_registration`, `outside_window`, `access_denied`, `student_inactive`, `lost_card`, and `class_not_allowed`. Server time and attendance windows are authoritative; the firmware does not decide attendance or set a class.

### Poll school attendance for the LCD

```http
GET /student/rfid-status
X-Device-Token: <same secret configured on the server>
X-Device-Id: MAIN_GATE_01
```

Leave the query string empty to display the whole-school summary, appropriate for a reader serving multiple classes. The response includes `class_name` and `class_summary` with `total_students`, `present_count`, `late_count`, `absent_count`, and `unmarked_count`. This endpoint also runs the app's daily absence reconciliation, so polling can trigger the configured server-side reconciliation/notifications. The sketch polls once per minute while idle.

## Indicators

- **Green:** present scan accepted or meeting check-in recorded.
- **Yellow:** late/outside-window scan or an unassigned card awaiting staff registration.
- **Red:** rejected card, inactive/lost card, server/configuration error, or no Wi-Fi connection.
- **All off:** idle attendance summary is displayed.

The LCD shows the whole-school daily totals while idle and the per-scan result for five seconds after a card tap.

## Deployment notes

- Keep the reader and Flask server on a network where the reader can reach the server. Restrict inbound server access using the deployment firewall; avoid exposing development HTTP to the public internet.
- The reader shares the configured device token with the server. If devices require independent revocation, the backend will need per-device token validation before deploying multiple readers with separate credentials.
- The app writes authenticated card scans to `RFIDScanLog`, including UID, server timestamp, reader ID, session, outcome, message, and whether the tap was a duplicate. The device token is not stored in the scan record.
- RFID verification on real hardware is still needed for the exact ESP32 board, LCD address/library, Wi-Fi, reader range, and school's network/TLS certificate.
