import esphome.codegen as cg
from esphome.components import text_sensor
import esphome.config_validation as cv
from esphome.const import CONF_MODE

from . import CONF_ECOSPLIT_ID, ECOSPLIT_CHILD_SCHEMA

CONFIG_SCHEMA = ECOSPLIT_CHILD_SCHEMA.extend({cv.Optional(CONF_MODE): text_sensor.text_sensor_schema()})


async def to_code(config):
    hub = await cg.get_variable(config[CONF_ECOSPLIT_ID])
    if CONF_MODE in config:
        sens = await text_sensor.new_text_sensor(config[CONF_MODE])
        cg.add(hub.set_mode_text_sensor(sens))
