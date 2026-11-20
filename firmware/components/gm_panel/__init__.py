"""gm_panel: a framebuffer pushed over TCP, written straight to the ST7789.

Home Assistant renders every pixel (Blitz); the device only moves rectangles
of RGB565 from a socket into the panel's own memory. Nothing is buffered in
RAM beyond one TCP segment, and nothing touches flash.
"""

import esphome.codegen as cg
from esphome import pins
from esphome.components import socket, spi
import esphome.config_validation as cv
from esphome.const import CONF_DC_PIN, CONF_ID, CONF_PORT, CONF_RESET_PIN

DEPENDENCIES = ["spi", "network", "wifi"]
AUTO_LOAD = ["socket"]

CONF_IMPORT_STOCK_WIFI = "import_stock_wifi"

gm_panel_ns = cg.esphome_ns.namespace("gm_panel")
GMPanel = gm_panel_ns.class_("GMPanel", cg.Component, spi.SPIDevice)

CONFIG_SCHEMA = cv.All(
    cv.Schema(
        {
            cv.GenerateID(): cv.declare_id(GMPanel),
            cv.Required(CONF_DC_PIN): pins.gpio_output_pin_schema,
            cv.Optional(CONF_RESET_PIN): pins.gpio_output_pin_schema,
            cv.Optional(CONF_PORT, default=8811): cv.port,
            # Join the network the stock GeekMagic firmware was on, from the
            # credentials the ESP8266 SDK keeps in flash, when ESPHome has none.
            cv.Optional(CONF_IMPORT_STOCK_WIFI, default=True): cv.boolean,
        }
    )
    .extend(cv.COMPONENT_SCHEMA)
    .extend(spi.spi_device_schema(cs_pin_required=False, default_mode="MODE3", default_data_rate=40e6)),
    socket.consume_sockets(1, "gm_panel", socket.SocketType.TCP_LISTEN),
    socket.consume_sockets(1, "gm_panel"),
)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    await spi.register_spi_device(var, config)
    cg.add(var.set_dc_pin(await cg.gpio_pin_expression(config[CONF_DC_PIN])))
    if CONF_RESET_PIN in config:
        cg.add(var.set_reset_pin(await cg.gpio_pin_expression(config[CONF_RESET_PIN])))
    cg.add(var.set_port(config[CONF_PORT]))
    cg.add(var.set_import_stock_wifi(config[CONF_IMPORT_STOCK_WIFI]))
