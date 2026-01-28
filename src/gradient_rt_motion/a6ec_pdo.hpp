#pragma once

#include <cstdint>

namespace gradient::a6ec {

// Identity tuple (16.1) from the committed ESI (must be verified on live bus).
constexpr uint32_t kVendorId = 0x00400000;
constexpr uint32_t kProductCode = 0x00000715;
constexpr uint32_t kRevisionNo = 0x00002EF8;

// Fixed PDO sets (16.2).
constexpr uint16_t kRxPdo = 0x1702; // SM2 outputs
constexpr uint16_t kTxPdo = 0x1B02; // SM3 inputs

// RxPDO 0x1702 layout (16.3) — byte offsets.
constexpr uint16_t kOffControlword = 0;     // 0x6040:0 (16b)
constexpr uint16_t kOffTargetPosition = 2;  // 0x607A:0 (32b)
constexpr uint16_t kOffTargetVelocity = 6;  // 0x60FF:0 (32b) (unused in CSP v1)
constexpr uint16_t kOffTargetTorque = 10;   // 0x6071:0 (16b) (unused in CSP v1)
constexpr uint16_t kOffModeOfOperation = 12; // 0x6060:0 (8b)

// TxPDO 0x1B02 layout (16.4) — byte offsets.
constexpr uint16_t kOffErrorCode = 0;        // 0x603F:0 (16b)
constexpr uint16_t kOffStatusword = 2;       // 0x6041:0 (16b)
constexpr uint16_t kOffPositionActual = 4;   // 0x6064:0 (32b)
constexpr uint16_t kOffTorqueActual = 8;     // 0x6077:0 (16b)
constexpr uint16_t kOffModeDisplay = 10;     // 0x6061:0 (8b)
constexpr uint16_t kOffDigitalInputs = 21;   // 0x60FD:0 (32b)

} // namespace gradient::a6ec

