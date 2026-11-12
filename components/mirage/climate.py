import esphome.codegen as cg
from esphome.components import climate_ir, remote_base

AUTO_LOAD = ["climate_ir"]

mirage_ns = cg.esphome_ns.namespace("mirage")
MirageClimate = mirage_ns.class_("MirageClimate", climate_ir.ClimateIR)

CONFIG_SCHEMA = climate_ir.climate_ir_with_receiver_schema(MirageClimate)


async def to_code(config):
    remote_base.request_protocol("mirage")
    await climate_ir.new_climate_ir(config)
