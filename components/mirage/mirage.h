#pragma once

#include "esphome/components/climate_ir/climate_ir.h"

namespace esphome::mirage {

const float MIRAGE_TEMP_MIN = 16.0f;
const float MIRAGE_TEMP_MAX = 32.0f;

// Ar-condicionado com controle remoto Mirage de 14 bytes (modelo KKG9AC1).
class MirageClimate final : public climate_ir::ClimateIR {
 public:
  MirageClimate()
      : climate_ir::ClimateIR(MIRAGE_TEMP_MIN, MIRAGE_TEMP_MAX, 1.0f, true, true,
                              {climate::CLIMATE_FAN_AUTO, climate::CLIMATE_FAN_LOW, climate::CLIMATE_FAN_MEDIUM,
                               climate::CLIMATE_FAN_HIGH},
                              {climate::CLIMATE_SWING_OFF, climate::CLIMATE_SWING_VERTICAL}) {}

 protected:
  static constexpr uint8_t SWING_MIDDLE = 7;

  void transmit_state() override;
  bool on_receive(remote_base::RemoteReceiveData data) override;

  // Posição fixa da aleta usada com o swing desligado. Acompanha a última escolhida no controle original.
  uint8_t fixed_swing_{SWING_MIDDLE};
};

}  // namespace esphome::mirage
