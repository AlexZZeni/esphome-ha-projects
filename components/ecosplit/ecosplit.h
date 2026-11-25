#pragma once

#include <vector>

#include "esphome/components/binary_sensor/binary_sensor.h"
#include "esphome/components/sensor/sensor.h"
#include "esphome/components/text_sensor/text_sensor.h"
#include "esphome/components/uart/uart.h"
#include "esphome/core/component.h"

namespace esphome::ecosplit {

// Quadro de onde vem cada valor.
enum Source : uint8_t {
  SOURCE_CONTROLLER = 0,  // C1 -> FE, 13 bytes: pedidos do controlador da parede
  SOURCE_UNIT = 1,        // 01 -> FE, 31 bytes: leituras da placa da evaporadora
};

// Conversão do byte (ou dos bytes) para o valor publicado. Mapa em docs/modelos.md.
enum Decode : uint8_t {
  DECODE_RAW = 0,          // byte como está
  DECODE_TEMPERATURE = 1,  // °C + 55
  DECODE_QUARTER = 2,      // passos de 0,25
  DECODE_TIMES_4 = 3,      // passos de 4
  DECODE_TENTHS_16 = 4,    // 16 bits, byte mais alto primeiro, em décimos
  DECODE_LOW_7 = 5,        // bits 0 a 6
};

// Escuta o barramento RS-485 entre o controlador e a placa da evaporadora, sem nunca transmitir.
class Ecosplit : public Component, public uart::UARTDevice {
 public:
  void loop() override;
  void dump_config() override;
  float get_setup_priority() const override { return setup_priority::DATA; }

  void add_sensor(sensor::Sensor *sensor, uint8_t source, uint8_t index, uint8_t decode) {
    this->sensors_.push_back({sensor, source, index, decode, NAN});
  }
  void add_binary_sensor(binary_sensor::BinarySensor *sensor, uint8_t source, uint8_t index, uint8_t mask) {
    this->binary_sensors_.push_back({sensor, source, index, mask, -1});
  }
  void set_mode_text_sensor(text_sensor::TextSensor *sensor) { this->mode_sensor_ = sensor; }
  void set_online_binary_sensor(binary_sensor::BinarySensor *sensor) { this->online_sensor_ = sensor; }

 protected:
  struct SensorBinding {
    sensor::Sensor *sensor;
    uint8_t source;
    uint8_t index;
    uint8_t decode;
    float last;
  };
  struct BinarySensorBinding {
    binary_sensor::BinarySensor *sensor;
    uint8_t source;
    uint8_t index;
    uint8_t mask;
    int8_t last;  // -1 = ainda não publicado
  };

  void parse_buffer_();
  void handle_frame_(const uint8_t *frame, uint8_t size);
  void publish_source_(uint8_t source, const uint8_t *frame);
  void set_online_(bool online);

  std::vector<uint8_t> buffer_;
  std::vector<SensorBinding> sensors_;
  std::vector<BinarySensorBinding> binary_sensors_;
  text_sensor::TextSensor *mode_sensor_{nullptr};
  binary_sensor::BinarySensor *online_sensor_{nullptr};
  uint8_t last_mode_{0};
  bool online_{false};
  bool online_published_{false};
  uint32_t last_frame_ms_{0};
  uint32_t valid_frames_{0};
  uint32_t invalid_frames_{0};
};

}  // namespace esphome::ecosplit
