/*
 * Tangible NFC Interactive Storytelling Game
 * Step 3: Arduino RC522 UID Reader Firmware
 *
 * Reads NFC card UIDs and sends them over USB serial to the Python host.
 * No game logic — UID transmission only.
 *
 * Hardware: Arduino Uno + RC522 RFID Reader (MFRC522 library)
 *
 * Wiring (RC522 → Arduino Uno):
 *   SDA (SS)  → Pin 10
 *   SCK       → Pin 13
 *   MOSI      → Pin 11
 *   MISO      → Pin 12
 *   IRQ       → (not connected)
 *   GND       → GND
 *   RST       → Pin 9
 *   3.3V      → 3.3V
 *
 * Serial: 115200 baud, one UID per line (uppercase hex, no prefix)
 * Example: 3AF12491
 */

#include <SPI.h>
#include <MFRC522.h>

#define RST_PIN 9
#define SS_PIN  10
#define BAUD_RATE 115200

MFRC522 mfrc522(SS_PIN, RST_PIN);

bool cardPresent = false;
byte lastUid[10];
byte lastUidSize = 0;

void initReader();
String uidToHexString(const byte *uid, byte uidSize);
bool uidsEqual(const byte *a, byte aSize, const byte *b, byte bSize);
void sendUid(const String &uidHex);
void handleCardDetection();
void handleCardAbsence();

void setup() {
  Serial.begin(BAUD_RATE);
  initReader();
}

void loop() {
  if (!mfrc522.PICC_IsNewCardPresent()) {
    handleCardAbsence();
    return;
  }

  if (!mfrc522.PICC_ReadCardSerial()) {
    return;
  }

  handleCardDetection();

  mfrc522.PICC_HaltA();
  mfrc522.PCD_StopCrypto1();
}

void initReader() {
  SPI.begin();
  mfrc522.PCD_Init();
}

String uidToHexString(const byte *uid, byte uidSize) {
  static const char HEX_CHARS[] = "0123456789ABCDEF";
  String result;
  result.reserve(uidSize * 2);

  for (byte i = 0; i < uidSize; i++) {
    result += HEX_CHARS[(uid[i] >> 4) & 0x0F];
    result += HEX_CHARS[uid[i] & 0x0F];
  }

  return result;
}

bool uidsEqual(const byte *a, byte aSize, const byte *b, byte bSize) {
  if (aSize != bSize) {
    return false;
  }

  for (byte i = 0; i < aSize; i++) {
    if (a[i] != b[i]) {
      return false;
    }
  }

  return true;
}

void sendUid(const String &uidHex) {
  Serial.println(uidHex);
}

void handleCardDetection() {
  const byte *uid = mfrc522.uid.uidByte;
  byte uidSize = mfrc522.uid.size;

  if (!cardPresent || !uidsEqual(uid, uidSize, lastUid, lastUidSize)) {
    sendUid(uidToHexString(uid, uidSize));

    lastUidSize = uidSize;
    for (byte i = 0; i < uidSize; i++) {
      lastUid[i] = uid[i];
    }
  }

  cardPresent = true;
}

void handleCardAbsence() {
  cardPresent = false;
}
