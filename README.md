# MIL-STD-1553 Bus Protocol Simulator

**West-Tek Solutions**

A layered Python simulation of the MIL-STD-1553B serial data bus protocol, built as a defense tech portfolio project. Demonstrates Bus Controller / Remote Terminal communication, dual-redundancy failover, and fault simulation across a full protocol stack.

---

## What is MIL-STD-1553?

MIL-STD-1553 is a military serial data bus standard originally developed for the F-16 in 1973. It defines how avionics subsystems communicate over a shared wire — radar, navigation, weapons, flight controls — and is still used today in the F-35, Predator drones, the Space Launch System, and virtually every serious defense platform.

Key characteristics:

- **1 Mbit/s** half-duplex serial bus
- **Master/slave architecture** — one Bus Controller (BC) initiates all communication; up to 31 Remote Terminals (RTs) respond only when commanded
- **20-bit words** — 3-bit sync + 16-bit payload + 1 parity bit
- **Dual redundancy** — two physically independent buses (Bus A / Bus B); automatic failover if primary bus fails
- **Deterministic timing** — no bus contention possible by design

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    demo.py                          │
│           (scripted BC↔RT scenarios)                │
└───────────────────────┬─────────────────────────────┘
                        │
          ┌─────────────┴──────────────┐
          │                            │
┌─────────▼──────────┐      ┌──────────▼─────────┐
│   Bus_Controller   │      │    RT_Simulator     │
│  (bus_controller.py)│      │  (rt_simulator.py)  │
└─────────┬──────────┘      └──────────┬──────────┘
          │                            │
          └─────────────┬──────────────┘
                        │
┌───────────────────────▼─────────────────────────────┐
│              BC_Message_Layer                        │
│         (bc_message_layer.py)                        │
│   Frame sequencing · Word count · T/R direction      │
└───────────────────────┬─────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────┐
│              BC_Data_Link_Layer                      │
│         (bc_data_link_layer.py)                      │
│   20-bit frame encode/decode · Sync · Parity         │
└───────────────────────┬─────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────┐
│              BC_Physical_Layer                       │
│         (bc_physical_layer.py)                       │
│   UDP socket simulation · Bus A/B dual redundancy    │
└─────────────────────────────────────────────────────┘
```

### Simulated bus mapping

| Bus   | BC sends to | BC listens on |
| ----- | ----------- | ------------- |
| Bus A | port 2001   | port 2000     |
| Bus B | port 2003   | port 2002     |

---

## Word Format

Each word is exactly 20 bits:

```
[ 3-bit sync ][ 16-bit payload ][ 1-bit parity ]

Command / Status sync : 100
Data word sync        : 001
```

Command word payload layout:

```
Bit  0     : RT address MSB
Bits 1–4   : RT address nibble
Bit  5     : T/R bit  (1 = RT transmit, 0 = RT receive)
Bit  6     : Sub-address MSB
Bits 7–10  : Sub-address nibble
Bit  11    : Word count MSB
Bits 12–15 : Word count nibble
```

---

## Files

| File                    | Description                                                         |
| ----------------------- | ------------------------------------------------------------------- |
| `bus_controller.py`     | Bus Controller — initiates all communication                        |
| `rt_simulator.py`       | Remote Terminal — responds to BC commands, holds subaddress buffers |
| `bc_message_layer.py`   | Message layer — frame sequencing, word count management             |
| `bc_data_link_layer.py` | Data link layer — 20-bit frame encode/decode                        |
| `bc_physical_layer.py`  | Physical layer — UDP socket simulation                              |
| `demo.py`               | Entry point — runs all demonstration scenarios                      |

---

## Setup

```bash
# Clone the repo
git clone https://github.com/btwest/MIL-STD-1553-SIM.git
cd MIL-STD-1553-SIM

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# No external dependencies — standard library only
python demo.py
```

---

## Demo Scenarios

Running `python demo.py` executes four scenarios in sequence:

### Scenario 1 — BC → RT Write

The BC sends the string `NAVIGATE` to RT-02 subaddress 01. The RT receives the data words, updates its subaddress buffer, and acknowledges with a status word.

### Scenario 2 — BC → RT Read

The BC polls RT-02 subaddress 01. The RT responds with a status word followed by data words containing the current buffer contents.

### Scenario 3 — Full Telemetry Poll

The BC sequentially polls all three RT subaddresses, simulating a mission computer reading avionics telemetry:

| Subaddress | Data       | Meaning            |
| ---------- | ---------- | ------------------ |
| 01         | `HDG095`   | Heading 095°       |
| 02         | `ALT32000` | Altitude 32,000 ft |
| 03         | `SPD04800` | Airspeed 480 knots |

### Scenario 4 — Fault Simulation

The RT is restarted with `drop_response=True`, simulating a terminal that has gone offline. The BC transmits a command, receives no status word within the timeout window, and marks RT-02 as unresponsive — demonstrating the fault tolerance behavior required by MIL-STD-1553B.

---

## Notes

**Timing:** Real MIL-STD-1553 operates at 1 Mbit/s with a 4 µs inter-message gap and a 14 µs no-response timeout. This simulator uses `time.sleep()` delays in the range of seconds for demo visibility.

**Parity:** The parity bit is simulated as always-valid (`1`). Real implementations use odd parity computed over the 16-bit payload.

**Dual redundancy:** The physical layer supports Bus A and Bus B with automatic failover on transmission error, matching the MIL-STD-1553B §4.2 requirement that all terminals connect to both buses.
