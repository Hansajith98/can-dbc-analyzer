# CAN Bus DBC Signal Decoder and Analyzer

A professional Python-based tool for decoding and analyzing CAN bus data from automotive networks using DBC (Database CAN) files.

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.10+-green.svg)

---

## Table of Contents

- [Overview](#-overview)
- [What is CAN Bus?](#-what-is-can-bus)
- [What is a DBC File?](#-what-is-a-dbc-file)
- [Features](#-features)
- [Project Structure](#-project-structure)
- [Installation](#-installation)
- [Quick Start](#-quick-start)

---

## 🎯 Overview

This project provides a complete toolchain for automotive CAN bus analysis:

1. **Load DBC database files** - Parse message and signal definitions
2. **Read CAN log files** - Support for Vector ASC format
3. **Decode CAN frames** - Convert raw bytes to physical values
4. **Store and analyze signals** - Organize time-series data
5. **Export to CSV** - Long and wide format support
6. **Visualize signals** - Publication-quality plots

---

## What is CAN Bus?

**CAN (Controller Area Network)** is a robust vehicle bus standard designed for automotive applications.

### Key Characteristics:

- **Multi-master protocol**: Any ECU can transmit
- **Message-based**: Data organized in frames with IDs
- **Real-time**: Deterministic message prioritization
- **Robust**: Built-in error detection and fault confinement
- **Efficient**: Up to 1 Mbps on standard CAN

### CAN Frame Structure:

```
┌─────────────┬──────────┬─────┬──────────────┬─────┬───────┐
│ Arbitration │ Control  │ RTR │     Data     │ CRC │  ACK  │
│     ID      │   Field  │     │   (0-8 bytes)│     │       │
└─────────────┴──────────┴─────┴──────────────┴─────┴───────┘
  11 or 29 bits    6 bits   1 bit   0-64 bits   16 bits 2 bits
```

---

## What is a DBC File?

**DBC (Database CAN)** files define the structure of CAN messages in a human-readable format.

### DBC File Purpose:

- Define **message IDs** and their names
- Specify **signal positions** within messages
- Provide **scaling formulas** (factor, offset)
- Document **units** (RPM, km/h, °C)
- Include **value tables** (enumerations)

### DBC Signal Definition:

```
SG_ RPM : 0|16@1+ (0.25,0) [0|8000] "RPM" Gateway
    │     │  │  │   │   │    │   │     │       │
    │     │  │  │   │   │    │   │     │       └─ Receiver
    │     │  │  │   │   │    │   │     └───────── Unit
    │     │  │  │   │   │    │   └─────────────── Max value
    │     │  │  │   │   │    └─────────────────── Min value
    │     │  │  │   │   └──────────────────────── Offset
    │     │  │  │   └──────────────────────────── Factor (scale)
    │     │  │  └──────────────────────────────── Value type (+ = unsigned)
    │     │  └─────────────────────────────────── Byte order (1 = big-endian)
    │     └────────────────────────────────────── Length (bits)
    └──────────────────────────────────────────── Start bit position
```


## Features

### Core Functionality

- **DBC Parser**: Load and validate CAN database files
- **ASC Log Reader**: Parse Vector ASCII log format
- **Frame Decoder**: Convert raw CAN data to physical values
- **Signal Store**: Organize time-series data by signal name
- **CSV Export**: Long format (database) and wide format (plotting)
- **Visualization**: Multiple plot types with matplotlib

### Advanced Features

- **Filtering**: By time range, CAN IDs, or signal names
- **Statistics**: Min, max, mean, count for each signal
- **Professional Plots**: Publication-ready visualizations
- **Error Handling**: Graceful handling of malformed data
- **Logging**: Configurable verbose mode for debugging
- **CLI Interface**: Comprehensive command-line tool

---

## Installation

### Prerequisites

- **Python 3.10 or higher**
- **pip** (Python package manager)
- **git** (optional, for cloning)

### Step 1: Clone or Download

```bash
# Clone repository
git clone https://github.com/Hansajith98/can-dbc-analyzer.git
cd can-dbc-analyzer

```

### Step 2: Create Virtual Environment (Recommended)

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

---


### Basic Usage

Decode all signals from a CAN log:

```bash
python src/main.py --dbc dbc/example_vehicle.dbc --log logs/drive_log.asc
```

This will:
1. Load the DBC database
2. Read the CAN log file
3. Decode all frames
4. Export to `output/decoded_signals.csv`
5. Generate plots in `output/plots/`

### View Results

```bash
# View CSV in terminal
cat output/decoded_signals.csv | head -20

# Open plots (on Linux)
xdg-open output/plots/

# Open plots (on Mac)
open output/plots/

# Open plots (on Windows)
start output/plots/
```

---

### Plot Types

#### 1. Single Signal Plot
- **Filename**: `<signal_name>.png`
- **Content**: Time-series of one signal
- **Example**: `rpm.png` shows RPM over time

#### 2. Combined Plot
- **Filename**: `combined_signals.png`
- **Content**: Multiple signals on same axes (dual y-axis if different units)
- **Example**: Speed and RPM together

#### 3. Subplots
- **Filename**: `subplots.png`
- **Content**: Stacked subplots, one per signal
- **Example**: RPM, Speed, Temperature stacked vertically

#### 4. Overview Dashboard
- **Filename**: `overview_dashboard.png`
- **Content**: Comprehensive 3-panel view
- **Panels**: Speed/RPM, Temp/Load, Gear

---

## Theory Concepts Covered,

### CAN Bus Concepts
- Message-based communication
- Arbitration and priorities
- Frame structure (standard vs extended)
- Error detection (CRC, ACK)

### DBC Database Format
- Message definitions
- Signal encoding (start bit, length, byte order)
- Scaling and physical units
- Value tables and enumerations

### Python Best Practices
- Modular design
- Type hints and dataclasses
- Error handling
- Logging and debugging
- Command-line interfaces

### Data Analysis
- Time-series processing
- Statistical summaries
- CSV export formats
- Data visualization

---

## Author

**Deshitha Hansajith**  
January 2026
