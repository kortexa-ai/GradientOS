#pragma once

#include <cstdint>

namespace gradient::ds402 {

// DS402 state decode patterns from the plan (16.7).
enum class State : uint8_t {
  Unknown = 0,
  NotReady = 1,
  SwitchOnDisabled = 2,
  ReadyToSwitchOn = 3,
  SwitchedOn = 4,
  OperationEnabled = 5,
  QuickStopActive = 6,
  FaultReactionActive = 7,
  Fault = 8,
};

inline State decode_statusword(uint16_t sw) noexcept {
  // Canonical DS402 mask patterns (common practice).
  if ((sw & 0x004F) == 0x0000) {
    return State::NotReady;
  }
  if ((sw & 0x004F) == 0x0040) {
    return State::SwitchOnDisabled;
  }
  if ((sw & 0x006F) == 0x0021) {
    return State::ReadyToSwitchOn;
  }
  if ((sw & 0x006F) == 0x0023) {
    return State::SwitchedOn;
  }
  if ((sw & 0x006F) == 0x0027) {
    return State::OperationEnabled;
  }
  if ((sw & 0x006F) == 0x0007) {
    return State::QuickStopActive;
  }
  if ((sw & 0x004F) == 0x000F) {
    return State::FaultReactionActive;
  }
  if ((sw & 0x004F) == 0x0008) {
    return State::Fault;
  }
  return State::Unknown;
}

// Controlword constants from the plan (16.8).
constexpr uint16_t CW_SHUTDOWN = 0x0006;
constexpr uint16_t CW_SWITCH_ON = 0x0007;
constexpr uint16_t CW_ENABLE_OP = 0x000F;
constexpr uint16_t CW_DISABLE_OP = 0x0007;
constexpr uint16_t CW_DISABLE_VOLTAGE = 0x0000;
constexpr uint16_t CW_FAULT_RESET = 0x0080;
constexpr uint16_t CW_QUICK_STOP = 0x000B;

// Compute the next controlword for a desired "enable" trajectory.
inline uint16_t controlword_for_enable(State st, bool want_enable, bool want_fault_reset) noexcept {
  if (want_fault_reset && st == State::Fault) {
    return CW_FAULT_RESET;
  }
  if (!want_enable) {
    return CW_DISABLE_VOLTAGE;
  }

  switch (st) {
    case State::SwitchOnDisabled:
      return CW_SHUTDOWN;
    case State::ReadyToSwitchOn:
      return CW_SWITCH_ON;
    case State::SwitchedOn:
      return CW_ENABLE_OP;
    case State::OperationEnabled:
      return CW_ENABLE_OP;
    case State::QuickStopActive:
      // Re-run enable sequence; some drives need explicit shutdown first.
      return CW_SHUTDOWN;
    case State::FaultReactionActive:
      return CW_DISABLE_VOLTAGE;
    case State::Fault:
      // If no reset requested, remain disabled.
      return CW_DISABLE_VOLTAGE;
    case State::NotReady:
    case State::Unknown:
    default:
      return CW_DISABLE_VOLTAGE;
  }
}

} // namespace gradient::ds402

