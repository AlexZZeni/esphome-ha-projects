import esphome.codegen as cg
from esphome.components import sensor
import esphome.config_validation as cv
from esphome.const import (
    DEVICE_CLASS_CURRENT,
    DEVICE_CLASS_FREQUENCY,
    DEVICE_CLASS_TEMPERATURE,
    DEVICE_CLASS_VOLTAGE,
    ENTITY_CATEGORY_DIAGNOSTIC,
    STATE_CLASS_MEASUREMENT,
    UNIT_AMPERE,
    UNIT_CELSIUS,
    UNIT_HERTZ,
    UNIT_VOLT,
)

from . import (
    CONF_ECOSPLIT_ID,
    DECODE_LOW_7,
    DECODE_QUARTER,
    DECODE_RAW,
    DECODE_TEMPERATURE,
    DECODE_TENTHS_16,
    DECODE_TIMES_4,
    ECOSPLIT_CHILD_SCHEMA,
    SOURCE_CONTROLLER,
    SOURCE_UNIT,
)


def _temperature(accuracy=0):
    return sensor.sensor_schema(
        unit_of_measurement=UNIT_CELSIUS,
        accuracy_decimals=accuracy,
        device_class=DEVICE_CLASS_TEMPERATURE,
        state_class=STATE_CLASS_MEASUREMENT,
    )


def _current():
    return sensor.sensor_schema(
        unit_of_measurement=UNIT_AMPERE,
        accuracy_decimals=2,
        device_class=DEVICE_CLASS_CURRENT,
        state_class=STATE_CLASS_MEASUREMENT,
    )


def _raw():
    return sensor.sensor_schema(
        accuracy_decimals=0,
        state_class=STATE_CLASS_MEASUREMENT,
        entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
    )


# Chave no YAML: (quadro, byte, conversão, esquema). Mapa em docs/carrier-ecosplit/protocolo.md.
SENSORS = {
    "target_temperature": (SOURCE_CONTROLLER, 5, DECODE_LOW_7, _temperature()),
    "room_temperature": (SOURCE_CONTROLLER, 6, DECODE_TENTHS_16, _temperature(1)),
    "outdoor_temperature": (SOURCE_UNIT, 7, DECODE_TEMPERATURE, _temperature()),
    "condenser_temperature": (SOURCE_UNIT, 8, DECODE_TEMPERATURE, _temperature()),
    "suction_temperature": (SOURCE_UNIT, 9, DECODE_TEMPERATURE, _temperature()),
    "discharge_1_temperature": (SOURCE_UNIT, 10, DECODE_TEMPERATURE, _temperature()),
    "discharge_2_temperature": (SOURCE_UNIT, 11, DECODE_TEMPERATURE, _temperature()),
    "heatsink_temperature": (SOURCE_UNIT, 12, DECODE_TEMPERATURE, _temperature()),
    "compressor_1_current": (SOURCE_UNIT, 14, DECODE_QUARTER, _current()),
    "compressor_2_current": (SOURCE_UNIT, 15, DECODE_QUARTER, _current()),
    "inverter_frequency": (
        SOURCE_UNIT,
        18,
        DECODE_RAW,
        sensor.sensor_schema(
            unit_of_measurement=UNIT_HERTZ,
            accuracy_decimals=0,
            device_class=DEVICE_CLASS_FREQUENCY,
            state_class=STATE_CLASS_MEASUREMENT,
        ),
    ),
    "inverter_current": (SOURCE_UNIT, 19, DECODE_QUARTER, _current()),
    "dc_bus_voltage": (
        SOURCE_UNIT,
        20,
        DECODE_TIMES_4,
        sensor.sensor_schema(
            unit_of_measurement=UNIT_VOLT,
            accuracy_decimals=0,
            device_class=DEVICE_CLASS_VOLTAGE,
            state_class=STATE_CLASS_MEASUREMENT,
        ),
    ),
}

# Bytes ainda não identificados, publicados como estão para acompanhar no histórico.
UNKNOWN_CONTROLLER_BYTES = [8, 9]
UNKNOWN_UNIT_BYTES = [5, 6, 13, 16, 17, 21, 22, 23, 24, 25, 26, 27, 28]
for index in UNKNOWN_CONTROLLER_BYTES:
    SENSORS[f"controller_byte_{index}"] = (SOURCE_CONTROLLER, index, DECODE_RAW, _raw())
for index in UNKNOWN_UNIT_BYTES:
    SENSORS[f"unit_byte_{index}"] = (SOURCE_UNIT, index, DECODE_RAW, _raw())

CONFIG_SCHEMA = ECOSPLIT_CHILD_SCHEMA.extend(
    {cv.Optional(key): schema for key, (_, _, _, schema) in SENSORS.items()}
)


async def to_code(config):
    hub = await cg.get_variable(config[CONF_ECOSPLIT_ID])
    for key, (source, index, decode, _) in SENSORS.items():
        if key in config:
            sens = await sensor.new_sensor(config[key])
            cg.add(hub.add_sensor(sens, source, index, decode))
