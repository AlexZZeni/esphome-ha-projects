import esphome.codegen as cg
from esphome.components import uart
import esphome.config_validation as cv
from esphome.const import CONF_ID

DEPENDENCIES = ["uart"]
AUTO_LOAD = ["sensor", "binary_sensor", "text_sensor"]
MULTI_CONF = True

CONF_ECOSPLIT_ID = "ecosplit_id"

ecosplit_ns = cg.esphome_ns.namespace("ecosplit")
Ecosplit = ecosplit_ns.class_("Ecosplit", cg.Component, uart.UARTDevice)

# Mesmos valores do enum Source e do enum Decode em ecosplit.h.
SOURCE_CONTROLLER = 0
SOURCE_UNIT = 1
DECODE_RAW = 0
DECODE_TEMPERATURE = 1
DECODE_QUARTER = 2
DECODE_TIMES_4 = 3
DECODE_TENTHS_16 = 4
DECODE_LOW_7 = 5

CONFIG_SCHEMA = (
    cv.Schema({cv.GenerateID(): cv.declare_id(Ecosplit)})
    .extend(cv.COMPONENT_SCHEMA)
    .extend(uart.UART_DEVICE_SCHEMA)
)

# 9600 baud, 8N1, só recepção: o componente nunca transmite.
FINAL_VALIDATE_SCHEMA = uart.final_validate_device_schema(
    "ecosplit", baud_rate=9600, require_rx=True, data_bits=8, parity="NONE", stop_bits=1
)

ECOSPLIT_CHILD_SCHEMA = cv.Schema({cv.GenerateID(CONF_ECOSPLIT_ID): cv.use_id(Ecosplit)})


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    await uart.register_uart_device(var, config)
