#include "mirage.h"

#include <cmath>

#include "esphome/components/remote_base/mirage_protocol.h"
#include "esphome/core/helpers.h"
#include "esphome/core/log.h"

namespace esphome::mirage {

static const char *const TAG = "mirage.climate";

// Quadro de 14 bytes; o checksum é acrescentado pelo MirageProtocol. Layout conforme a documentação do
// IRremoteESP8266 (ir_Mirage.h), conferido com capturas do controle original.
static const size_t FRAME_SIZE = 14;
static const uint8_t HEADER = 0x56;
static const uint8_t TEMP_OFFSET = 0x5C;
// Bytes fixos em todas as capturas.
static const uint8_t BYTE8 = 0x0C;
static const uint8_t BYTE10 = 0x0C;

// Byte 4, bits 4-7.
static const uint8_t MODE_HEAT = 1;
static const uint8_t MODE_COOL = 2;
static const uint8_t MODE_DRY = 3;
static const uint8_t MODE_AUTO = 4;
static const uint8_t MODE_FAN = 5;

// Byte 4, bits 0-1, na ordem em que o botão de ventilação percorre as velocidades.
static const uint8_t FAN_AUTO = 0;
static const uint8_t FAN_HIGH = 1;
static const uint8_t FAN_LOW = 2;
static const uint8_t FAN_MEDIUM = 3;

// Byte 5, bits 1-7: posição da aleta (3 a 11 fixa, 13 em movimento). A partir de 0x5F, o ar está desligado.
static const uint8_t SWING_AUTO = 13;
static const uint8_t POWER_OFF_MIN = 0x5F;
// Valor que o controle envia no byte 5 para desligar, independente do swing.
static const uint8_t BYTE5_OFF = 0xC0;

// No modo desumidificar, o controle sempre envia 17 °C.
static const uint8_t DRY_TEMP = 17;

void MirageClimate::transmit_state() {
  remote_base::MirageData frame;
  frame.data.assign(FRAME_SIZE, 0);
  auto &d = frame.data;
  d[0] = HEADER;
  d[8] = BYTE8;
  d[10] = BYTE10;

  uint8_t mode;
  switch (this->mode) {
    case climate::CLIMATE_MODE_HEAT:
      mode = MODE_HEAT;
      break;
    case climate::CLIMATE_MODE_DRY:
      mode = MODE_DRY;
      break;
    case climate::CLIMATE_MODE_FAN_ONLY:
      mode = MODE_FAN;
      break;
    case climate::CLIMATE_MODE_HEAT_COOL:
      mode = MODE_AUTO;
      break;
    default:
      mode = MODE_COOL;
      break;
  }

  uint8_t fan;
  switch (this->fan_mode.value_or(climate::CLIMATE_FAN_AUTO)) {
    case climate::CLIMATE_FAN_LOW:
      fan = FAN_LOW;
      break;
    case climate::CLIMATE_FAN_MEDIUM:
      fan = FAN_MEDIUM;
      break;
    case climate::CLIMATE_FAN_HIGH:
      fan = FAN_HIGH;
      break;
    default:
      fan = FAN_AUTO;
      break;
  }

  uint8_t celsius = roundf(clamp(this->target_temperature, MIRAGE_TEMP_MIN, MIRAGE_TEMP_MAX));
  if (mode == MODE_DRY)
    celsius = DRY_TEMP;

  d[1] = celsius + TEMP_OFFSET;
  d[4] = (mode << 4) | fan;
  if (this->mode == climate::CLIMATE_MODE_OFF) {
    d[5] = BYTE5_OFF;
  } else {
    uint8_t swing = this->swing_mode == climate::CLIMATE_SWING_VERTICAL ? SWING_AUTO : this->fixed_swing_;
    d[5] = swing << 1;
  }

  this->transmit_<remote_base::MirageProtocol>(frame);
}

bool MirageClimate::on_receive(remote_base::RemoteReceiveData data) {
  auto decoded = remote_base::MirageProtocol().decode(data);
  if (!decoded.has_value() || decoded->data.size() != FRAME_SIZE || decoded->data[0] != HEADER)
    return false;
  const auto &d = decoded->data;

  uint8_t swing = d[5] >> 1;
  if (swing >= POWER_OFF_MIN) {
    this->mode = climate::CLIMATE_MODE_OFF;
    this->publish_state();
    return true;
  }

  uint8_t mode = d[4] >> 4;
  switch (mode) {
    case MODE_HEAT:
      this->mode = climate::CLIMATE_MODE_HEAT;
      break;
    case MODE_COOL:
      this->mode = climate::CLIMATE_MODE_COOL;
      break;
    case MODE_DRY:
      this->mode = climate::CLIMATE_MODE_DRY;
      break;
    case MODE_AUTO:
      this->mode = climate::CLIMATE_MODE_HEAT_COOL;
      break;
    case MODE_FAN:
      this->mode = climate::CLIMATE_MODE_FAN_ONLY;
      break;
    default:
      ESP_LOGW(TAG, "Modo desconhecido: %u", mode);
      return false;
  }

  // A temperatura do modo desumidificar é fixa e não reflete a escolhida pelo usuário.
  if (mode != MODE_DRY)
    this->target_temperature = d[1] - TEMP_OFFSET;

  switch (d[4] & 0x03) {
    case FAN_LOW:
      this->fan_mode = climate::CLIMATE_FAN_LOW;
      break;
    case FAN_MEDIUM:
      this->fan_mode = climate::CLIMATE_FAN_MEDIUM;
      break;
    case FAN_HIGH:
      this->fan_mode = climate::CLIMATE_FAN_HIGH;
      break;
    default:
      this->fan_mode = climate::CLIMATE_FAN_AUTO;
      break;
  }

  if (swing == SWING_AUTO) {
    this->swing_mode = climate::CLIMATE_SWING_VERTICAL;
  } else {
    this->swing_mode = climate::CLIMATE_SWING_OFF;
    this->fixed_swing_ = swing;
  }

  this->publish_state();
  return true;
}

}  // namespace esphome::mirage
