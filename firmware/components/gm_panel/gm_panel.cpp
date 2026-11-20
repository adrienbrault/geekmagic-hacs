#include "gm_panel.h"

#include "esphome/components/network/util.h"
#include "esphome/components/wifi/wifi_component.h"
#include "esphome/core/log.h"

#include <cerrno>
#include <cstring>

#ifdef USE_ESP8266
#include <Esp.h>
extern "C" {
#include <user_interface.h>
}
#endif

namespace esphome::gm_panel {

static const char *const TAG = "gm_panel";

// One loop() call drains the socket for at most this long, so a full frame
// streams in a few calls without starving Wi-Fi, the API or OTA.
static constexpr uint32_t LOOP_BUDGET_US = 20000;

static uint16_t le16(const uint8_t *p) { return p[0] | (p[1] << 8); }
static uint32_t le32(const uint8_t *p) { return p[0] | (p[1] << 8) | (p[2] << 16) | (uint32_t(p[3]) << 24); }
static void put32(uint8_t *p, uint32_t v) {
  p[0] = v;
  p[1] = v >> 8;
  p[2] = v >> 16;
  p[3] = v >> 24;
}

static uint32_t free_heap() {
#ifdef USE_ESP8266
  return ESP.getFreeHeap();
#else
  return 0;
#endif
}

static uint32_t max_free_block() {
#ifdef USE_ESP8266
  return ESP.getMaxFreeBlockSize();
#else
  return 0;
#endif
}

void GMPanel::setup() {
  this->read_stock_wifi_();
  this->spi_setup();
  this->dc_pin_->setup();
  if (this->reset_pin_ != nullptr)
    this->reset_pin_->setup();
  this->init_panel_();
  this->fill_(0x0000);
}

void GMPanel::read_stock_wifi_() {
#ifdef USE_ESP8266
  if (!this->import_stock_wifi_)
    return;
  // The SDK keeps the last station config the stock firmware saved. Read it
  // before ESPHome's Wi-Fi takes over the radio; apply it once Wi-Fi is up.
  struct station_config conf {};
  if (!wifi_station_get_config_default(&conf) || conf.ssid[0] == 0)
    return;
  char ssid[33] = {0};
  char password[65] = {0};
  memcpy(ssid, conf.ssid, 32);
  memcpy(password, conf.password, 64);
  this->stock_ssid_ = ssid;
  this->stock_password_ = password;
#endif
}

void GMPanel::apply_stock_wifi_() {
  this->stock_wifi_applied_ = true;
  if (this->stock_ssid_.empty() || wifi::global_wifi_component == nullptr)
    return;
  if (wifi::global_wifi_component->has_sta()) {
    ESP_LOGD(TAG, "Wi-Fi already configured; stock credentials not needed");
    return;
  }
  ESP_LOGI(TAG, "Joining the stock firmware's network '%s'", this->stock_ssid_.c_str());
  wifi::global_wifi_component->save_wifi_sta(this->stock_ssid_.c_str(), this->stock_password_.c_str());
  this->stock_password_.clear();
}

void GMPanel::command_(uint8_t cmd) {
  this->dc_pin_->digital_write(false);
  this->enable();
  this->write_byte(cmd);
  this->disable();
}

void GMPanel::data_(const uint8_t *data, size_t len) {
  this->dc_pin_->digital_write(true);
  this->enable();
  this->write_array(data, len);
  this->disable();
}

void GMPanel::init_panel_() {
  if (this->reset_pin_ != nullptr) {
    this->reset_pin_->digital_write(true);
    delay(5);
    this->reset_pin_->digital_write(false);
    delay(20);
    this->reset_pin_->digital_write(true);
    delay(120);
  }
  this->command_(0x01);  // SWRESET
  delay(150);
  this->command_(0x11);  // SLPOUT
  delay(120);
  const uint8_t colmod = 0x55;  // 16 bits per pixel
  this->command_(0x3A);
  this->data_(&colmod, 1);
  const uint8_t madctl = 0x00;  // RGB order, no rotation
  this->command_(0x36);
  this->data_(&madctl, 1);
  this->command_(0x21);  // INVON: this panel needs inverted colours
  this->command_(0x13);  // NORON
  this->command_(0x29);  // DISPON
  delay(20);
}

void GMPanel::set_window_(uint16_t x, uint16_t y, uint16_t w, uint16_t h) {
  const uint16_t x1 = x + w - 1;
  const uint16_t y1 = y + h - 1;
  const uint8_t cols[4] = {uint8_t(x >> 8), uint8_t(x), uint8_t(x1 >> 8), uint8_t(x1)};
  const uint8_t rows[4] = {uint8_t(y >> 8), uint8_t(y), uint8_t(y1 >> 8), uint8_t(y1)};
  this->command_(0x2A);  // CASET
  this->data_(cols, 4);
  this->command_(0x2B);  // RASET
  this->data_(rows, 4);
  this->command_(0x2C);  // RAMWR: pixel data follows
}

void GMPanel::fill_(uint16_t rgb565) {
  this->set_window_(0, 0, WIDTH, HEIGHT);
  for (size_t i = 0; i < sizeof(this->buf_); i += 2) {
    this->buf_[i] = rgb565 >> 8;
    this->buf_[i + 1] = rgb565;
  }
  size_t left = size_t(WIDTH) * HEIGHT * 2;
  while (left > 0) {
    const size_t n = left < sizeof(this->buf_) ? left : sizeof(this->buf_) & ~size_t(1);
    this->data_(this->buf_, n);
    left -= n;
  }
}

void GMPanel::start_listening_() {
  auto sock = socket::socket_ip_loop_monitored(SOCK_STREAM, 0);
  if (sock == nullptr)
    return;
  int enable = 1;
  sock->setsockopt(SOL_SOCKET, SO_REUSEADDR, &enable, sizeof(int));
  sock->setblocking(false);
  struct sockaddr_storage server {};
  socklen_t sl = socket::set_sockaddr_any((struct sockaddr *) &server, sizeof(server), this->port_);
  if (sl == 0 || sock->bind((struct sockaddr *) &server, sl) != 0 || sock->listen(1) != 0) {
    ESP_LOGW(TAG, "Could not listen on port %u (errno %d)", this->port_, errno);
    return;
  }
  this->listen_ = std::move(sock);
  ESP_LOGI(TAG, "Listening on port %u", this->port_);
}

void GMPanel::loop() {
  if (!this->stock_wifi_applied_)
    this->apply_stock_wifi_();
  if (this->listen_ == nullptr) {
    if (network::is_connected())
      this->start_listening_();
    return;
  }
  if (this->listen_->ready())
    this->accept_client_();
  if (this->client_ != nullptr)
    this->serve_client_();
}

void GMPanel::accept_client_() {
  struct sockaddr_storage addr {};
  socklen_t len = sizeof(addr);
  auto sock = this->listen_->accept((struct sockaddr *) &addr, &len);
  if (sock == nullptr)
    return;
  // One sender at a time; a new connection replaces the old one (the
  // integration reconnects after a restart without waiting for a timeout).
  if (this->client_ != nullptr)
    this->drop_client_("replaced by a new connection");
  sock->setblocking(false);
  int nodelay = 1;
  sock->setsockopt(IPPROTO_TCP, TCP_NODELAY, &nodelay, sizeof(int));
  this->client_ = std::move(sock);
  this->header_len_ = 0;
  this->remaining_ = 0;
  this->send_hello_();
}

void GMPanel::send_hello_() {
  uint8_t hello[16] = {'G', 'M', 'H', '1', uint8_t(WIDTH), uint8_t(WIDTH >> 8), uint8_t(HEIGHT), uint8_t(HEIGHT >> 8)};
  put32(hello + 8, free_heap());
  put32(hello + 12, max_free_block());
  this->client_->write(hello, sizeof(hello));
}

void GMPanel::drop_client_(const char *why) {
  ESP_LOGD(TAG, "Closing client: %s", why);
  this->client_.reset();
  this->header_len_ = 0;
  this->remaining_ = 0;
}

bool GMPanel::parse_header_() {
  const uint8_t *h = this->header_;
  if (memcmp(h, "GMR1", 4) != 0)
    return false;
  const uint16_t x = le16(h + 4), y = le16(h + 6), w = le16(h + 8), h_ = le16(h + 10);
  const uint32_t len = le32(h + 12);
  if (w == 0 || h_ == 0 || x + w > WIDTH || y + h_ > HEIGHT || len != uint32_t(w) * h_ * 2)
    return false;
  this->set_window_(x, y, w, h_);
  this->remaining_ = len;
  this->rect_started_us_ = micros();
  return true;
}

void GMPanel::serve_client_() {
  const uint32_t start = micros();
  while (this->client_ != nullptr && micros() - start < LOOP_BUDGET_US) {
    if (this->remaining_ == 0) {
      ssize_t n = this->client_->read(this->header_ + this->header_len_, sizeof(this->header_) - this->header_len_);
      if (n == 0) {
        this->drop_client_("closed by peer");
        return;
      }
      if (n < 0) {
        if (errno != EWOULDBLOCK && errno != EAGAIN)
          this->drop_client_("read error");
        return;
      }
      this->header_len_ += n;
      if (this->header_len_ < sizeof(this->header_))
        continue;
      this->header_len_ = 0;
      if (!this->parse_header_()) {
        this->drop_client_("bad header");
        return;
      }
      continue;
    }
    // RAMWR keeps streaming across bursts, so a burst may end mid-pixel.
    size_t want = this->remaining_ < sizeof(this->buf_) ? this->remaining_ : sizeof(this->buf_);
    ssize_t n = this->client_->read(this->buf_, want);
    if (n == 0) {
      this->drop_client_("closed mid-rect");
      return;
    }
    if (n < 0) {
      if (errno != EWOULDBLOCK && errno != EAGAIN)
        this->drop_client_("read error");
      return;
    }
    this->dc_pin_->digital_write(true);
    this->enable();
    this->write_array(this->buf_, n);
    this->disable();
    this->remaining_ -= n;
    this->bytes_ += n;
    if (this->remaining_ == 0) {
      this->rects_++;
      uint8_t ack[12] = {'G', 'M', 'A', '1'};
      put32(ack + 4, micros() - this->rect_started_us_);
      put32(ack + 8, free_heap());
      this->client_->write(ack, sizeof(ack));
    }
  }
}

void GMPanel::dump_config() {
  ESP_LOGCONFIG(TAG, "GeekMagic panel (ST7789 %ux%u)", WIDTH, HEIGHT);
  LOG_PIN("  DC Pin: ", this->dc_pin_);
  LOG_PIN("  Reset Pin: ", this->reset_pin_);
  ESP_LOGCONFIG(TAG, "  Port: %u\n  Import stock Wi-Fi: %s\n  Free heap: %u, max block: %u", this->port_,
                YESNO(this->import_stock_wifi_), free_heap(), max_free_block());
}

}  // namespace esphome::gm_panel
