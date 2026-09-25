/*
  Lab 3 - Convertidor AC-DC monofasico controlado (ESP32-S3, Arduino-ESP32 core 2.x o 3.x)

  Conexiones:
    PIN_ZC    <- salida del divisor de la interfaz (0-3.3 V). Pulso en ALTO alrededor de cada cruce por cero.
    PIN_PULSE -> LED del MOC3021 (con su resistencia de polarizacion, o a traves de un transistor).

  Uso: Serial Monitor a 115200, terminador "Nueva linea".
    Digite un entero 0-180 (angulo de disparo en grados) o "off" para desactivar los pulsos.
*/

#include <Arduino.h>
#include "driver/gpio.h"
#include "esp_timer.h"

#ifndef ESP_ARDUINO_VERSION_MAJOR
#define ESP_ARDUINO_VERSION_MAJOR 2
#endif

constexpr int PIN_ZC    = 4;
constexpr int PIN_PULSE = 5;

constexpr uint32_t PULSE_US           = 500;
constexpr uint32_t HALF_PERIOD_NOM_US = 8333;
constexpr uint32_t WIDTH_NOM_US       = 500;
constexpr uint32_t REJECT_US          = 6000;

enum : uint8_t { IDLE = 0, WAIT = 1, PULSE = 2 };

static hw_timer_t *timer = nullptr;
static volatile uint8_t  state        = IDLE;
static volatile bool     enabled      = false;
static volatile uint16_t alphaDeg     = 90;
static volatile uint32_t halfPeriodUs = HALF_PERIOD_NOM_US;
static volatile uint32_t widthUs      = WIDTH_NOM_US;
static volatile uint32_t tRise = 0, tFall = 0, armedAt = 0;
static volatile bool     haveRise = false;
static volatile uint32_t zcCount  = 0;
static volatile uint32_t nArm = 0, nFire = 0, nBadW = 0, nWd = 0;  // diagnostico

#if ESP_ARDUINO_VERSION_MAJOR >= 3
#define TIMER_ARM(us) do { timerWrite(timer, 0); timerAlarm(timer, (us), false, 0); } while (0)
#else
#define TIMER_ARM(us) do { timerWrite(timer, 0); timerAlarmWrite(timer, (us), false); timerAlarmEnable(timer); } while (0)
#endif

static uint32_t IRAM_ATTR calcDelayUs() {
  return (halfPeriodUs * (uint32_t)alphaDeg) / 180;
}

void IRAM_ATTR onTimer() {
  if (state == WAIT) {
    gpio_set_level((gpio_num_t)PIN_PULSE, 1);
    nFire++;
    state = PULSE;
    TIMER_ARM(PULSE_US);
  } else if (state == PULSE) {
    gpio_set_level((gpio_num_t)PIN_PULSE, 0);
    state = IDLE;
  }
}

void IRAM_ATTR isrZC() {
  uint32_t now = (uint32_t)esp_timer_get_time();

  if (gpio_get_level((gpio_num_t)PIN_ZC)) {
    if ((uint32_t)(now - tRise) < REJECT_US) return;
    tRise = now;
    haveRise = true;
    if (enabled && state == IDLE) {
      uint32_t d = calcDelayUs();
      uint32_t half = widthUs / 2;
      // Angulos pequenos: no hay tiempo de programar desde el flanco de bajada,
      // se programa desde el de subida sumando media anchura del pulso de Vsal.
      if (d < half + 60) {
        state = WAIT;
        armedAt = now;
        nArm++;
        TIMER_ARM(d + half);
      }
    }
  } else {
    if (!haveRise) return;
    haveRise = false;
    uint32_t w = (uint32_t)(now - tRise);
    if (w < 100 || w > 2500) { nBadW++; return; }

    widthUs = (widthUs * 3 + w) / 4;
    uint32_t hp = (uint32_t)(now - tFall);
    tFall = now;
    if (hp > 7000 && hp < 9500) halfPeriodUs = (halfPeriodUs * 7 + hp) / 8;
    zcCount++;

    if (enabled && state == IDLE) {
      // El cruce por cero real es el centro del pulso de Vsal: w/2 antes de este flanco.
      uint32_t d = calcDelayUs();
      uint32_t half = w / 2;
      uint32_t wait = (d > half + 5) ? (d - half) : 5;
      state = WAIT;
      armedAt = now;
      nArm++;
      TIMER_ARM(wait);
    }
  }
}

static void handleSerial() {
  if (!Serial.available()) return;
  String s = Serial.readStringUntil('\n');
  s.trim();
  if (s.length() == 0) return;

  if (s.equalsIgnoreCase("off")) {
    enabled = false;
    Serial.println("Disparo desactivado.");
    return;
  }

  bool numeric = true;
  for (size_t i = 0; i < s.length(); i++) {
    if (!isDigit(s[i])) numeric = false;
  }
  int v = s.toInt();
  if (!numeric || v < 0 || v > 180) {
    Serial.println("Valor invalido. Digite un entero entre 0 y 180, o 'off'.");
    return;
  }

  alphaDeg = (uint16_t)v;
  enabled = true;
  Serial.printf("alfa = %d grados -> retardo = %u us\n", v, (unsigned)calcDelayUs());
}

void setup() {
  Serial.begin(115200);
  Serial.setTimeout(100);

  pinMode(PIN_PULSE, OUTPUT);
  digitalWrite(PIN_PULSE, LOW);
  pinMode(PIN_ZC, INPUT);

#if ESP_ARDUINO_VERSION_MAJOR >= 3
  timer = timerBegin(1000000);
  timerAttachInterrupt(timer, &onTimer);
#else
  timer = timerBegin(0, 80, true);
  timerAttachInterrupt(timer, &onTimer, true);
#endif

  attachInterrupt(digitalPinToInterrupt(PIN_ZC), isrZC, CHANGE);
  Serial.println("Listo. Digite el angulo de disparo (0-180) o 'off'.");
}

void loop() {
  handleSerial();

  if (state != IDLE && (uint32_t)((uint32_t)esp_timer_get_time() - armedAt) > 30000) {
    state = IDLE;
    nWd++;
    digitalWrite(PIN_PULSE, LOW);
  }

  static uint32_t lastPrint = 0, lastCount = 0;
  if (millis() - lastPrint >= 1000) {
    lastPrint = millis();
    uint32_t n = zcCount;
    if (n == lastCount) {
      Serial.println("Sin senal de cruce por cero.");
    } else {
      Serial.printf("f=%.2f Hz  ancho ZC=%u us  alfa=%u  retardo=%u us  disparo=%s  zc=%u arm=%u fire=%u malw=%u wd=%u\n",
                    1e6f / (2.0f * (float)halfPeriodUs), (unsigned)widthUs,
                    (unsigned)alphaDeg, (unsigned)calcDelayUs(), enabled ? "ON" : "OFF",
                    (unsigned)n, (unsigned)nArm, (unsigned)nFire, (unsigned)nBadW, (unsigned)nWd);
    }
    lastCount = n;
  }
}
