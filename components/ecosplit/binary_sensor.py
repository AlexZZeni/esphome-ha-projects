import esphome.codegen as cg
from esphome.components import binary_sensor
import esphome.config_validation as cv
from esphome.const import (
    DEVICE_CLASS_CONNECTIVITY,
    DEVICE_CLASS_POWER,
    DEVICE_CLASS_RUNNING,
    ENTITY_CATEGORY_DIAGNOSTIC,
)

from . import CONF_ECOSPLIT_ID, ECOSPLIT_CHILD_SCHEMA, SOURCE_CONTROLLER, SOURCE_UNIT

CONF_ONLINE = "online"

# Chave no YAML: (quadro, byte, máscara, esquema). Mapa em docs/carrier-ecosplit/protocolo.md.
BINARY_SENSORS = {
    "power": (SOURCE_CONTROLLER, 5, 0x80, binary_sensor.binary_sensor_schema(device_class=DEVICE_CLASS_POWER)),
    "evaporator_fan": (SOURCE_UNIT, 17, 0x08, binary_sensor.binary_sensor_schema(device_class=DEVICE_CLASS_RUNNING)),
}
# Bits do byte 17 ainda não identificados.
for mask in (0x01, 0x02, 0x04):
    BINARY_SENSORS[f"unit_state_bit_{mask:02x}"] = (
        SOURCE_UNIT,
        17,
        mask,
        binary_sensor.binary_sensor_schema(entity_category=ENTITY_CATEGORY_DIAGNOSTIC),
    )

CONFIG_SCHEMA = ECOSPLIT_CHILD_SCHEMA.extend(
    {
        cv.Optional(CONF_ONLINE): binary_sensor.binary_sensor_schema(
            device_class=DEVICE_CLASS_CONNECTIVITY, entity_category=ENTITY_CATEGORY_DIAGNOSTIC
        ),
        **{cv.Optional(key): schema for key, (_, _, _, schema) in BINARY_SENSORS.items()},
    }
)


async def to_code(config):
    hub = await cg.get_variable(config[CONF_ECOSPLIT_ID])
    if CONF_ONLINE in config:
        sens = await binary_sensor.new_binary_sensor(config[CONF_ONLINE])
        cg.add(hub.set_online_binary_sensor(sens))
    for key, (source, index, mask, _) in BINARY_SENSORS.items():
        if key in config:
            sens = await binary_sensor.new_binary_sensor(config[key])
            cg.add(hub.add_binary_sensor(sens, source, index, mask))
