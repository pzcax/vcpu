# VCPU architecture
This readme will talk about how the cpu is structured.

## References:

### Hexadecimal:
- hexadecminal can be written many ways. These two are the main ones:
    - 0x00 - 0xFF
    - 00 - FF
- It's important to remember that machine code is fundamentally bytes, and hex converts cleanly to bytes.
- The '0x' prefix is simply a notation for humans, and will only be used in writing source code.

## Components

### Registers:
- There will be 4 registers but will expand to 6 for parameters later
- 16 bits (2 bytes) per register

### PC (Program Store)
- The program counter will store the absolute memory address of the next instruction

### Memory
- Byte addressable 
- 2 kilobit for now, could expand to 4, 8, 16, etc.
- Starts at 1. 0 based indexing is only internal for python, but publicly, use 1 based indexing.

## Notes

### Instruction Format
- Instructions are formatted like so: 
    - opcode
        - 1 byte
    - operand 1
        - 1 byte
    - operand 2
        - 1 byte (immediates represented as 2 bytes in little endian, signed, integer)
- opcodes and non-immediates are written as hexadecimal (0x00 - 0xFF)

### ISA (Instruction Set Architecture)
| Opcode | Name 
| ------ | -----
| 0x00   | halt
| 0x01   | imov    
| 0x02   | mov
| 0x03   | iadd
| 0x04   | add
| 0x05   | isub
| 0x06   | sub
| 0x07   | imul
| 0x08   | mul
| 0x09   | idiv
| 0x0A   | div
| 0x0B   | icmp
| 0x0C   | cmp
| 0x0D   | ijmp
| 0x0E   | je
| 0x0F   | jne
| 0x10   | jl
| 0x11   | jle
| 0x12   | jg
| 0x13   | jge
| 0x14   | ipush
| 0x15   | push
| 0x16   | pop
| 0x17   | istore
| 0x18   | store
| 0x19   | load
| 0x1A   | loadr
| 0x1B   | call
| 0x1C   | ret
| 0x1D   | iout
| 0x1E   | out
| 0x1F   | in

All jmp opcodes take in one immediate operand

cmp sets flags, and jmp opcodes simply jump to that absolute memory address if the relevant flags are true.

Be aware that 0x17-0x1A do not follow standard naming conventions. 

| ID | Register
| ------  |------
| 0xFB    | SP
| 0xFC    | R1 
| 0xFD    | R2
| 0xFE    | R3
| 0xFF    | R4

### Ports

Ports connect the CPU to devices.

| Port | Device | Purpose
| ---  | ------ | ------
| 1    | Console| Display a character
| 2    | Keyboard| Read key buffer