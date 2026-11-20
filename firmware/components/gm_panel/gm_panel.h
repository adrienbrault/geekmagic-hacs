#pragma once

#include "esphome/components/socket/socket.h"
#include "esphome/components/spi/spi.h"
#include "esphome/core/component.h"
#include "esphome/core/hal.h"

#include <memory>
#include <string>

namespace esphome::gm_panel {

// Wire protocol v1 (little-endian), one client at a time:
//   device -> client on connect  "GMH1" u16 width u16 height u32 free_heap u32 max_free_block
//   client -> device per rect     "GMR1" u16 x u16 y u16 w u16 h u32 len, then len bytes of
//                                 RGB565 in panel byte order (big-endian), len == w*h*2
//   device -> client per rect     "GMA1" u32 elapsed_us u32 free_heap
// A malformed header closes the connection.
static constexpr uint16_t WIDTH = 240;
static constexpr uint16_t HEIGHT = 240;

class GMPanel : public Component,
                public spi::SPIDevice<spi::BIT_ORDER_MSB_FIRST, spi::CLOCK_POLARITY_HIGH,
                                      spi::CLOCK_PHASE_TRAILING, spi::DATA_RATE_40MHZ> {
 public:
  void set_dc_pin(GPIOPin *pin) { this->dc_pin_ = pin; }
  void set_reset_pin(GPIOPin *pin) { this->reset_pin_ = pin; }
  void set_port(uint16_t port) { this->port_ = port; }
  void set_import_stock_wifi(bool import) { this->import_stock_wifi_ = import; }

  void setup() override;
  void loop() override;
  void dump_config() override;
  // Before Wi-Fi: the panel is up (and the stock credentials read) before
  // anything else touches the radio.
  float get_setup_priority() const override { return setup_priority::HARDWARE; }

 protected:
  void command_(uint8_t cmd);
  void data_(const uint8_t *data, size_t len);
  void init_panel_();
  void set_window_(uint16_t x, uint16_t y, uint16_t w, uint16_t h);
  void fill_(uint16_t rgb565);
  void read_stock_wifi_();
  void apply_stock_wifi_();
  void start_listening_();
  void accept_client_();
  void serve_client_();
  bool parse_header_();
  void drop_client_(const char *why);
  void send_hello_();

  GPIOPin *dc_pin_{nullptr};
  GPIOPin *reset_pin_{nullptr};
  uint16_t port_{8811};
  bool import_stock_wifi_{true};

  std::string stock_ssid_;
  std::string stock_password_;
  bool stock_wifi_applied_{false};

  std::unique_ptr<socket::ListenSocket> listen_;
  std::unique_ptr<socket::Socket> client_;

  uint8_t header_[16];
  size_t header_len_{0};
  uint32_t remaining_{0};
  uint32_t rect_started_us_{0};
  uint8_t buf_[1460];

  uint32_t rects_{0};
  uint32_t bytes_{0};
};

}  // namespace esphome::gm_panel
