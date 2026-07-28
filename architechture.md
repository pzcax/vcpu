# VCPU architecture
This readme will talk about how the cpu is structured.

## References:

### Sizes (for reference)
- 8 bits -> 1 byte (enough for a single ASCII character OR 256 values)
- 125 bytes -> 1 kilobit

### Hexadecimal:
- hexadecminal can be written many ways. These two are the main ones:
    - 0x00 - 0xFF
    - 00 - FF
- It's important to remember that machine code is fundamentally bytes, and hex converts cleanly to bytes.
- The '0x' prefix is simply a notation for humans, and will only be used in writing source code.

## Components

### Registers:
- There will be 4 registers but will expand to 6 for parameters later
- 64 bits (8 bytes) per register

### PC (Program Store)
- The program counter will store the memory address of the next instruction

### Memory
- Byte addressable
- 1 kilobit for now, could expand to 2, 4, 8, 16, etc.

### ALU (Arithmetic Logic Unit)
- Literally just does math for the processor. No access to memory, none of that.
- Handles things like: add, sub, mul, div, and, or, xor, shl, shr

## Notes

### Instruction Format
- Instructions are formatted like so: 
    - opcode
        - 1 byte (written as hexadecimal (0x00 - 0xFF))
    - operand 1
        - 1 byte
    - operand 2
        - 1 byte
    - immediates represented as 2 bytes in decimal format
- opcodes and non-immediates are written as hexadecimal (0x00 - 0xFF)

### ISA (Instruction Set Architecture)
| Opcode | Name 
| ------ | -----
| 0x01   | mov    
| 0x02   | load
| 0x03   | store
| 0x04   | add
| 0x05   | sub
| 0x06   | jmp
| 0x07   | cmp
| 0x08   | halt
| 0x09   | reserved

| ID | Register
| ------  |------ 
| 0x0A    | r1 
| 0x0B    | r2
| 0x0C    | r3
| 0x0D    | r4

### Example program
`MOV  R0, 123`

`MOV` -> `0x01`

`R0`     -> `0xA`

`123`    -> `7B 00`

Full instruction would be 

`0x01 0xA 7B 00` -> `01 10 7B 00`
