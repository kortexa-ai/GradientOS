## A6-EC fault/alarm/bus-fault code reference

Source: `docs/resources/A6-EC_series_servo_drive_manual.pdf` (Chapter 10 tables 10-1, 10-2, 10-3).

### Bus fault codes (`0x603F`)

| 0x603F | Name |
|---:|---|
| `0X0000` | No fault |
| `0X0FFF` | Factory fault |
| `0X2312` | Continuous current fault |
| `0X2330` | Short circuit to ground |
| `0X3120` | Control power overvoltage |
| `0X3130` | Phase loss |
| `0X3210` | Main circuit overvoltage |
| `0X3220` | Main circuit undervoltage |
| `0X3230` | Overload |
| `0X4210` | Over-temperature |
| `0X5443` | Forward overtravel |
| `0X5444` | Reverse overtravel |
| `0X5530` | Storage fault |
| `0X6320` | Parameter error |
| `0X7121` | Motor locked-rotor |
| `0X7122` | Motor mismatch |
| `0X7305` | Encoder error |
| `0X7500` | Communication fault |
| `0X7600` | Data storage |
| `0X8220` | Length error |
| `0X8400` | Speed control |
| `0X8611` | Following fault |
| `0X8700` | Synchronization controller |
| `0X8900` | Process data monitoring |

### Factory alarm codes (display code → meaning)

| Code | Meaning | Bus fault (`0x603F`) | Resettable | Class |
|---|---|---|---:|---|
| `ALF0.0` | Emergency stop alarm | `0X0F00` | yes | - |
| `ALF1.0` | Re-power-on required for parameter settings to take effect | `0X6320` | yes | - |
| `ALF1.1` | Frequent parameter storage alarm | `0X5530` | yes | - |
| `ALF1.2` | Torque reached parameter error | `0X6320` | yes | - |
| `ALF1.3` | Too frequent writing of EEPROM by host controller SDO | `0X7600` | yes | Class 3 |
| `ALF2.0` | Forward overtravel alarm | `0X5443` | yes | Class 3 |
| `ALF2.1` | Reverse overtravel alarm | `0X5444` | yes | Class 3 |
| `ALF4.0` | Homing timeout | `0X6320` | yes | Class 3 |
| `ALF4.1` | Homing DI conflict | `0X6320` | yes | Class 3 |
| `ALF4.2` | Homing mode conflict | `0X6320` | yes | Class 3 |
| `ALF5.0` | Braking resistor overload | `0X3210` | yes | Class 3 |
| `ALF5.1` | Too small resistance of external regenerative resistor | `0X6320` | yes | Class 3 |
| `ALF6.1` | Output phase loss | `0X3230` | yes | Class 3 |
| `ALF8.0` | Vibration occurred during auto-tuning | `0X7122` | yes | Class 3 |
| `ALF9.0` | Encoder battery voltage low | `0X7305` | yes | Class 3 |
| `ALFA.0` | Drive high temperature warning | `0X7305` | yes | Class 3 |
| `xxnr` | Servo not ready | `-` | yes | Class 3 |

### Factory fault codes (display code → meaning)

| Code | Meaning | Bus fault (`0x603F`) | Resettable | Class |
|---|---|---|---:|---|
| `Er01.0` | Mismatch of software versions | `0X6100` | no | - |
| `Er01.1` | Mismatch of motor parameters | `0X7122` | no | - |
| `Er02.0` | Product matching fault. No specified drive | `0X6100` | no | - |
| `Er02.1` | Product matching fault. No specified motor | `0X6100` | no | - |
| `Er02.2` | Product matching fault. No specified encoder | `0X6100` | no | - |
| `Er03.0` | System parameter error | `0X6320` | no | - |
| `Er03.1` | Parameter out-of-range | `0X6320` | no | - |
| `Er03.2` | Parameter writing error | `0X6320` | no | Class 1 |
| `Er03.3` | Parameter reading error | `0X6320` | no | Class 1 |
| `Er05.0` | Current loop timeout | `0X7500` | no | Class 1 |
| `Er05.1` | Speed loop timeout | `0X7500` | no | Class 1 |
| `Er05.2` | Position loop timeout | `0X7500` | no | Class 1 |
| `Er05.3` | Serial port data check failure | `0X7500` | no | Class 1 |
| `Er06.0` | Protection from out of control | `0X8400` | no | Class 1 |
| `Er10.0` | P-hardware overcurrent | `0X2312` | no | Class 1 |
| `Er10.1` | N-hardware overcurrent | `0X2312` | no | Class 1 |
| `Er10.2` | U phase software overcurrent | `0X2312` | no | Class 1 |
| `Er10.3` | V phase software overcurrent | `0X2312` | no | Class 1 |
| `Er10.4` | Output short circuited to ground | `0X2330` | no | Class 1 |
| `Er10.5` | Current sampling failure | `0X6100` | no | Class 1 |
| `Er10.6` | Incorrect current parameter setting | `0X6320` | no | Class 1 |
| `Er10.7` | UV current correction failure | `0X6100` | no | Class 1 |
| `Er10.8` | Excessive current zero drift | `0X6100` | no | Class 1 |
| `Er10.9` | Current exception during enabling | `0X2312` | no | Class 1 |
| `Er11.0` | Excessive motor speed upon servo drive power-on | `0XFF00` | no | Class 1 |
| `Er11.1` | Drive over-temperature | `0X2312` | no | Class 1 |
| `Er20.1` | Encoder internal fault | `0X7305` | no | Class 1 |
| `Er20.2` | Encoder reading/writing error | `0X7305` | no | Class 1 |
| `Er20.3` | Encoder data frame loss | `0X7305` | no | Class 1 |
| `Er20.4` | Excessive encoder incremental position | `0X7305` | no | Class 1 |
| `Er20.5` | Abnormal encoder data | `0X7305` | no | Class 1 |
| `Er20.6` | Mismatch of encoder type | `0X7305` | no | Class 1 |
| `Er20.7` | Encoder model not supported | `0X7305` | no | Class 1 |
| `Er20.8` | Encoder battery failure | `0X7305` | no | Class 1 |
| `Er20.9` | Encoder multi-turn error | `0X7305` | no | Class 1 |
| `Er21.0` | Mismatch between encoder pulses per revolution and drive pulses per revolution | `0X7305` | no | Class 1 |
| `Er31.0` | More than ten PDO mapping objects | `0X8220` | no | Class 1 |
| `Er32.0` | EtherCAT peripheral error | `0X6100` | no | Class 1 |
| `Er32.1` | ESI check error in FLASH | `0X7600` | no | Class 1 |
| `Er32.2` | Failure to read data from EEPROM through bus | `0X7600` | no | Class 1 |
| `Er32.3` | Failure of update to EEPROM through bus | `0X7600` | no | Class 1 |
| `Er32.4` | Correctness of checksum in ESC configuration area | `0X7600` | no | Class 1 |
| `Er32.5` | EtherCAT failed to obtain valid XML information | `0X7600` | no | Class 1 |
| `Er40.0` | Drive overload | `0X3230` | yes | Class 1 |
| `Er41.0` | Motor overload | `0X3230` | yes | Class 1 |
| `Er41.1` | Motor over-temperature due to locked- rotor | `0X7121` | yes | Class 1 |
| `Er41.2` | Motor over-temperature | `0X4210` | yes | Class 1 |
| `Er42.1` | Discharge tube temperature too high | `0X4210` | yes | Class 1 |
| `Er42.2` | Heatsink temperature too high | `0X4210` | yes | Class 1 |
| `Er43.0` | Overvoltage | `0X3210` | yes | Class 1 |
| `Er43.1` | Undervoltage | `0X3220` | yes | Class 1 |
| `Er45.0` | S-ON enabling failure | `0XFF00` | yes | Class 1 |
| `Er46.0` | Motor overspeed | `0X8400` | yes | Class 1 |
| `Er47.0` | Excessive position deviation | `0X8611` | yes | Class 1 |
| `Er47.1` | Position deviation overflow | `0X8611` | yes | Class 1 |
| `Er50.1` | D/Q current overflow | `0X6100` | yes | Class 1 |
| `Er51.0` | Offline inertia auto-tuning failure | `0X6310` | yes | Class 1 |
| `Er51.1` | Offline inertia parameter error | `0X6310` | yes | Class 1 |
| `Er52.0` | Angle auto-tuning failure | `0X7122` | yes | Class 1 |
| `Er53.0` | Motor parameter auto-tuning timeout | `0X7122` | yes | Class 1 |
| `Er53.1` | Resistance parameter auto-tuning failure | `0X7122` | yes | Class 1 |
| `Er53.2` | Inductance parameter auto-tuning failure | `0X7122` | yes | Class 1 |
| `Er53.3` | Back EMF parameter auto-tuning failure | `0X7122` | yes | Class 1 |
| `Er54.0` | Current loop auto-tuning failure | `0X7122` | yes | Class 1 |
| `Er55.0` | Excessive vibration | `0X7122` | yes | Class 1 |
| `Er74.0` | EtherCAT synchronization cycle setting error | `0X6320` | yes | Class 1 |
| `Er74.1` | No sync signal | `0X8700` | yes | Class 1 |
| `Er74.2` | Chip synchronization process uncompleted in OP | `0X8700` | yes | Class 1 |
| `Er80.0` | Control power undervoltage | `0X3120` | yes | Class 1 |
| `Er81.0` | Input phase loss 1 | `0X3130` | yes | Class 1 |
| `Er81.1` | Input phase loss 2 | `0X3130` | yes | Class 1 |
| `Er81.2` | Output phase loss (reserved) | `-` | yes | Class 1 |
| `Er82.0` | DI function allocation fault | `0X6320` | yes | Class 1 |
| `Er82.1` | DO function allocation fault | `0X6320` | yes | Class 1 |
| `Er84.0` | Electronic gear ratio setting error | `0X6320` | yes | Class 1 |
| `Er84.1` | Software limit setting error | `0X6320` | yes | Class 1 |
| `Er84.2` | Encoder resolution setting error | `0X7122` | yes | Class 1 |
| `Er84.3` | Home position setting error | `0XFF00` | yes | Class 2 |
| `Er87.1` | One-time excessive position reference increment (One-time increment of the target position is over 5 times of the maximum speed) | `0XFF00` | yes | Class 2 |
| `Er87.2` | Continuous excessive position reference increment (Increment of the target position exceeds the maximum speed for 3 consecutive times) | `0XFF00` | yes | Class 2 |
| `Er87.3` | Overflow of 32-bit sign bit of the target position during limiting | `0XFF00` | yes | Class 2 |
| `Er87.4` | Target position exceeding maximum value of mechanical single-turn position in rotating mode | `0XFF00` | yes | Class 2 |
| `ErA0.1` | Multi-turn overflow fault | `0X7305` | yes | Class 2 |
| `ErC1.0` | Excessive EtherCAT synchronization period error | `0X8700` | yes | Class 2 |
| `ErC1.1` | Synchronization loss | `0X8700` | yes | Class 2 |
| `ErC1.2` | Network status switchover error | `0X8700` | yes | Class 2 |
| `ErC1.4` | Network cable connection unreliable | `0X8700` | yes | Class 2 |
| `ErC1.5` | Data frame loss protection error | `0X8700` | yes | Class 2 |
| `ErC1.6` | Data frame forwarding error | `0X8700` | yes | Class 2 |
| `ErC1.7` | Data update timeout | `0X8700` | yes | Class 2 |
| `ErC1.8` | Watchdog expired | `0X8700` | yes | Class 2 |
| `ErC2.0` | SYNC signal loss | `0X8700` | yes | Class 2 |

