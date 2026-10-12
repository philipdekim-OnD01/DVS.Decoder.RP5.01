#!/usr/bin/env python3
"""S5KRC1S manual table 13: balance ON/OFF thresholds for hand contours."""
import argparse
import json
from smbus2 import SMBus, i2c_msg

REGS = (0x0157, 0x0166, 0x0167, 0x0168, 0x392C)

def read(bus, reg):
    address = i2c_msg.write(0x10, [reg >> 8, reg & 255])
    value = i2c_msg.read(0x10, 1); bus.i2c_rdwr(address, value)
    return list(value)[0]

def write(bus, reg, value):
    bus.i2c_rdwr(i2c_msg.write(0x10, [reg >> 8, reg & 255, value]))
    actual = read(bus, reg)
    if actual != value: raise RuntimeError(f'0x{reg:04X}: readback {actual:02X} != {value:02X}')

def apply(bus):
    before = {reg: read(bus, reg) for reg in REGS}
    # This profile uses the existing REF=15 and high-range threshold banks.
    if before[0x0157] & 0x1C != 0x1C or before[0x0166] & 0x3F != 15:
        raise RuntimeError('Unsupported REF/bank settings; original sensor settings preserved')
    target = {0x0167: (before[0x0167] & 0xC0) | 15,
              0x0168: (before[0x0168] & 0xC0) | 15}
    changed = []
    try:
        for reg, value in target.items():
            if value != before[reg]:
                changed.append(reg); write(bus, reg, value)
    except Exception:
        for reg in reversed(changed): write(bus, reg, before[reg])
        raise
    return {f'0x{reg:04X}': {'before': f'0x{before[reg]:02X}', 'after': f'0x{read(bus, reg):02X}'} for reg in REGS}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    with SMBus(10) as bus:
        result = apply(bus) if args.apply else {f'0x{reg:04X}': f'0x{read(bus,reg):02X}' for reg in REGS}
    print(json.dumps(result, indent=2))
