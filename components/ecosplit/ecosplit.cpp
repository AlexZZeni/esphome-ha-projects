#include "ecosplit.h"

#include <cmath>

#include "esphome/core/hal.h"
#include "esphome/core/helpers.h"
#include "esphome/core/log.h"

namespace esphome::ecosplit {

static const char *const TAG = "ecosplit";

// Formato do quadro: 9A 56 | origem | destino | tamanho | dados | XOR | soma.
static const uint8_t HEADER_0 = 0x9A;
static const uint8_t HEADER_1 = 0x56;
static const uint8_t MIN_FRAME_SIZE = 7;
static const size_t MAX_BUFFER = 64;

static const uint8_t ADDR_CONTROLLER = 0xC1;
static const uint8_t ADDR_UNIT = 0x01;
static const uint8_t ADDR_ALL = 0xFE;
static const uint8_t CONTROLLER_FRAME_SIZE = 13;
static const uint8_t UNIT_FRAME_SIZE = 31;

static const uint8_t CONTROLLER_MODE_BYTE = 10;
static const uint8_t TEMPERATURE_OFFSET = 55;

// Sem quadro válido por este tempo, os valores deixam de valer. O ciclo normal é de 656 ms.
static const uint32_t OFFLINE_TIMEOUT_MS = 5000;

static bool checksum_ok(const uint8_t *frame, uint8_t size) {
  uint8_t xor_value = 0;
  uint8_t sum = 0;
  for (uint8_t i = 0; i < size - 2; i++) {
    xor_value ^= frame[i];
    sum += frame[i];
  }
  sum += xor_value;
  return frame[size - 2] == xor_value && frame[size - 1] == sum;
}

static float decode_value(const uint8_t *frame, uint8_t index, uint8_t decode) {
  uint8_t value = frame[index];
  switch (decode) {
    case DECODE_TEMPERATURE:
      return static_cast<float>(value) - TEMPERATURE_OFFSET;
    case DECODE_QUARTER:
      return value * 0.25f;
    case DECODE_TIMES_4:
      return value * 4.0f;
    case DECODE_TENTHS_16:
      return ((static_cast<uint16_t>(value) << 8) | frame[index + 1]) / 10.0f;
    case DECODE_LOW_7:
      return value & 0x7F;
    default:
      return value;
  }
}

static const char *mode_name(uint8_t mode) {
  switch (mode) {
    case 1:
      return "Frio";
    case 2:
      return "Aquecer";
    case 3:
      return "Ventilar";
    default:
      return "Desconhecido";
  }
}

void Ecosplit::loop() {
  uint8_t byte;
  while (this->available() && this->read_byte(&byte)) {
    this->buffer_.push_back(byte);
    this->parse_buffer_();
  }
  if (this->online_ && millis() - this->last_frame_ms_ > OFFLINE_TIMEOUT_MS) {
    ESP_LOGW(TAG, "Nenhum quadro válido há %u ms", (unsigned) OFFLINE_TIMEOUT_MS);
    this->set_online_(false);
  } else if (!this->online_published_ && millis() > OFFLINE_TIMEOUT_MS) {
    // Nunca chegou um quadro desde que ligou: avisa o Home Assistant em vez de ficar sem estado.
    ESP_LOGW(TAG, "Nenhum quadro válido desde que a placa ligou. Confira A, B e GND");
    this->set_online_(false);
  }
}

// Acha quadros completos no buffer e descarta bytes que não formam um quadro válido.
void Ecosplit::parse_buffer_() {
  while (!this->buffer_.empty()) {
    if (this->buffer_[0] != HEADER_0 || (this->buffer_.size() > 1 && this->buffer_[1] != HEADER_1)) {
      this->buffer_.erase(this->buffer_.begin());
      continue;
    }
    if (this->buffer_.size() < 5)
      return;
    uint8_t size = this->buffer_[4];
    if (size < MIN_FRAME_SIZE || size > MAX_BUFFER) {
      this->invalid_frames_++;
      this->buffer_.erase(this->buffer_.begin());
      continue;
    }
    if (this->buffer_.size() < size)
      return;
    if (!checksum_ok(this->buffer_.data(), size)) {
      this->invalid_frames_++;
      ESP_LOGV(TAG, "Quadro com verificação errada: %s", format_hex_pretty(this->buffer_.data(), size).c_str());
      this->buffer_.erase(this->buffer_.begin());
      continue;
    }
    this->handle_frame_(this->buffer_.data(), size);
    this->buffer_.erase(this->buffer_.begin(), this->buffer_.begin() + size);
  }
}

void Ecosplit::handle_frame_(const uint8_t *frame, uint8_t size) {
  this->valid_frames_++;
  this->last_frame_ms_ = millis();
  if (!this->online_)
    this->set_online_(true);

  uint8_t src = frame[2];
  uint8_t dst = frame[3];
  ESP_LOGV(TAG, "%02X -> %02X: %s", src, dst, format_hex_pretty(frame, size).c_str());

  if (src == ADDR_CONTROLLER && dst == ADDR_ALL && size == CONTROLLER_FRAME_SIZE) {
    this->publish_source_(SOURCE_CONTROLLER, frame);
    uint8_t mode = frame[CONTROLLER_MODE_BYTE];
    if (this->mode_sensor_ != nullptr && mode != this->last_mode_) {
      this->last_mode_ = mode;
      this->mode_sensor_->publish_state(mode_name(mode));
    }
  } else if (src == ADDR_UNIT && dst == ADDR_ALL && size == UNIT_FRAME_SIZE) {
    this->publish_source_(SOURCE_UNIT, frame);
  }
}

// Publica só o que mudou, para não encher o histórico do Home Assistant a cada 656 ms.
void Ecosplit::publish_source_(uint8_t source, const uint8_t *frame) {
  for (auto &binding : this->sensors_) {
    if (binding.source != source)
      continue;
    float value = decode_value(frame, binding.index, binding.decode);
    if (value != binding.last) {
      binding.last = value;
      binding.sensor->publish_state(value);
    }
  }
  for (auto &binding : this->binary_sensors_) {
    if (binding.source != source)
      continue;
    int8_t state = (frame[binding.index] & binding.mask) ? 1 : 0;
    if (state != binding.last) {
      binding.last = state;
      binding.sensor->publish_state(state);
    }
  }
}

void Ecosplit::set_online_(bool online) {
  this->online_ = online;
  if (this->online_sensor_ != nullptr && (!this->online_published_ || this->online_sensor_->state != online)) {
    this->online_published_ = true;
    this->online_sensor_->publish_state(online);
  }
  if (online)
    return;
  // Sem comunicação, os últimos valores não valem mais. Eles voltam no próximo quadro.
  for (auto &binding : this->sensors_) {
    binding.last = NAN;
    binding.sensor->publish_state(NAN);
  }
  for (auto &binding : this->binary_sensors_)
    binding.last = -1;
  this->last_mode_ = 0;
  if (this->mode_sensor_ != nullptr)
    this->mode_sensor_->publish_state("Sem comunicação");
}

void Ecosplit::dump_config() {
  ESP_LOGCONFIG(TAG,
                "Carrier Ecosplit (só escuta):\n"
                "  Sensores: %u\n"
                "  Sensores binários: %u\n"
                "  Quadros válidos: %u, descartados: %u",
                (unsigned) this->sensors_.size(), (unsigned) this->binary_sensors_.size(),
                (unsigned) this->valid_frames_, (unsigned) this->invalid_frames_);
}

}  // namespace esphome::ecosplit
