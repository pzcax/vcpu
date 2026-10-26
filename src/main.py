import socket
import subprocess
import sys
import time
import threading
from collections import deque

HEADER = "\033[95m"
OKBLUE = "\033[94m"
OKCYAN = "\033[96m"
OKGREEN = "\033[92m"
WARNING = "\033[93m"
FAIL = "\033[91m"
ENDC = "\033[0m"
BOLD = "\033[1m"
UNDERLINE = "\033[4m"

class Errors:
    @staticmethod
    def _error(log: str):
        print(f"{FAIL}{log}{ENDC}")

    @staticmethod
    def M101(memorySize):
        Errors._error(
            f"Failure: M101 | Memory size not expected\nMemory size: {memorySize}"
        )
        exit(101)

    @staticmethod
    def M102(address, f, t):  # from, to
        Errors._error(
            f"Failure: M102 | Memory address out of range\nAddress: {address}\nMemory range: {f}-{t}\nNote: This is also the error used for stack overflow and underflow."
        )
        exit(102)

    @staticmethod
    def M103(type):
        Errors._error(
            f"Failure: M103 | Invalid memory region type\nType: {type}"
        )
        exit(103)

    @staticmethod
    def C201(value, high, low):
        Errors._error(
            f"Failure: C201 | Integer out of range\nValue: {value}\nHigh: {high}\nLow: {low}"
        )
        exit(201)

    @staticmethod
    def C202(programReserve, programCounter):
        Errors._error(
            f"Failure: C202 | Program counter exceeded the program memory\nProgram reserve: {programReserve}\nProgram counter: {programCounter}"
        )
        exit(202)

    @staticmethod
    def C203(opcode, programCounter):
        Errors._error(
            f"Failure: C203 | Unknown opcode\nOpcode: {opcode}\nProgram counter: {programCounter}"
        )
        exit(203)

    @staticmethod
    def C204(hexCode):
        Errors._error(
            f"Failure: C204 | Invalid register\nHex code: {hexCode}"
        )
        exit(204)

    @staticmethod
    def C205(termOne, termTwo):
        Errors._error(
            f"Failure: C205 | Division by 0 not allowed\nTerm one: {termOne}\nTerm two: {termTwo}"
        )
        exit(205)

class _Ports:
    @staticmethod
    def console(byte: list[str]):
        value = int(byte[1] + byte[0], 16)
        console.sendall(chr(value).encode())

    keyboardBuffer = deque()
    keyboardLock = threading.Lock()

    @staticmethod
    def keyboard():
        with _Ports.keyboardLock:
            if _Ports.keyboardBuffer:
                return _Ports.keyboardBuffer.popleft()
        return 0

    @staticmethod
    def keyboard_listener():
        while True:
            try:
                data = console.recv(1024)
            except OSError:
                break
            if not data:
                break
            with _Ports.keyboardLock:
                for b in data:
                    _Ports.keyboardBuffer.append(b)


class _SystemMemory:
    def __init__(self, size, programReserve, stackReserve, dataReserve):
        self.size = size  # bytes
        self.programReserve = programReserve  # bytes
        self.stackReserve = stackReserve  # bytes
        self.dataReserve = dataReserve # bytes
        self.memory = []

        print("Creating system...")

        index = 0  # After this loop, self.size will be tuned to the size, not requiring the use of len(self.memory) anymore
        while not (self.size == index):
            index += 1
            self.memory.append("00")

        if self.size == len(self.memory):  # just a check
            print(f"{self.size} Bytes of RAM")
        else:
            Errors.M101(len(self.memory))

    def edit(self, address: int, newValue: str, type: int):  # Taking in RAW bytes. converter later?
        if address < 1 or address > self.size:
            Errors.M102(address, 1, self.size)
            return

        if type == 1:  # program
            if address > self.programReserve:
                Errors.M102(address, 1, self.programReserve)
        elif type == 2:  # stack
            if not (self.programReserve < address <= self.programReserve + self.stackReserve):
                Errors.M102(address, self.programReserve + 1, self.programReserve + self.stackReserve)
        elif type == 3:  # data
            if not (self.programReserve + self.stackReserve < address <= self.programReserve + self.stackReserve + self.dataReserve):
                Errors.M102(address, self.programReserve + self.stackReserve + 1, self.programReserve + self.stackReserve + self.dataReserve)
        else:
            Errors.M103(type)

        self.memory[address-1] = newValue # -1 for python indexing

    def load_into_memory(self, fileName):
        print(f"Loading '{fileName}' into memory...")
        with open(fileName, "r") as f:
            contents = f.read()
            contents = contents.split()

            index = 1
            for token in contents:
                token = token.removeprefix("0x")
                self.edit(index, token, 1)
                index += 1   

    def access_memory(self):
        return self.memory


class _Cpu:
    def __init__(self, registerSize):  # bytes
        self.high = 2 ** (registerSize * 8 - 1) - 1
        self.low = -(2 ** (registerSize * 8 - 1))
        self.stackStart = SystemMemory.programReserve+1
        self.stackEnd = SystemMemory.programReserve + SystemMemory.stackReserve
        self.dataStart = SystemMemory.programReserve + SystemMemory.stackReserve + 1
        self.dataEnd = SystemMemory.programReserve + SystemMemory.stackReserve + SystemMemory.dataReserve

        self.flagGreater = False
        self.flagLesser = False
        self.flagEqual = False

        self.programCounter = 1
        self.running = False

        self.sp: int = self.stackStart # sp, super aids
        self.r1: int = 0 # r1
        self.r2: int = 0 # r2
        self.r3: int = 0 # r3
        self.r4: int = 0 # r4

    REGISTER_MAP = {
        "FB": "sp",
        "FC": "r1",
        "FD": "r2",
        "FE": "r3",
        "FF": "r4",
    }

    def _get_register(self, hexCode: str) -> int:
        name = self.REGISTER_MAP.get(hexCode)
        if name is None:
            Errors.C204(hexCode)
        return getattr(self, name) # type: ignore , it's already handled with C204

    def _edit_register(self, hexCode, newValue: int):
        name = self.REGISTER_MAP.get(hexCode)
        if name is None:
            Errors.C204(hexCode)

        if (not isinstance(newValue, int)) or (newValue < self.low or newValue > self.high):
            Errors.C201(newValue, self.high, self.low)

        setattr(self, name, newValue) # type: ignore , it's already handled with C204

    def _set_flags(self, termOne, termTwo):
        if termOne > termTwo:
            self.flagGreater = True
        else: self.flagGreater = False

        if termOne == termTwo:
            self.flagEqual = True
        else: self.flagEqual = False

        if termOne < termTwo:
            self.flagLesser = True
        else: self.flagLesser = False

    ### START RUN_X FUNCTIONS

    def run_imov(self, operand1, operand2: list[str]): # list for immediates having 2 bytes. non-immediates will have len() of 1
        print(f"imov: {operand1}, {operand2}")

        raw = bytes.fromhex("".join(operand2))
        value = int.from_bytes(raw, byteorder="little", signed=True)
        self._edit_register(operand1, value)

        self.log_register_state()

    def run_mov(self, operand1, operand2):
        print(f"mov: {operand1}, {operand2}")
        
        value = self._get_register(operand2)
        self._edit_register(operand1, value)

        self.log_register_state()


    def run_iadd(self, operand1, operand2: list[str]):
        print(f"iadd: {operand1}, {operand2}")

        raw = bytes.fromhex("".join(operand2))
        immediateValue = int.from_bytes(raw, byteorder="little", signed=True)
        registerValue = self._get_register(operand1)
        self._edit_register(operand1, immediateValue+registerValue)

        self.log_register_state()

    def run_add(self, operand1, operand2):
        print(f"add: {operand1}, {operand2}")

        registerValue1 = self._get_register(operand1)
        registerValue2 = self._get_register(operand2)
        self._edit_register(operand1, registerValue1+registerValue2)

        self.log_register_state()

    def run_isub(self, operand1, operand2: list[str]):
        print(f"isub: {operand1}, {operand2}")

        raw = bytes.fromhex("".join(operand2))
        immediateValue = int.from_bytes(raw, byteorder="little", signed=True)
        registerValue = self._get_register(operand1)
        self._edit_register(operand1, registerValue-immediateValue)

        self.log_register_state()

    def run_sub(self, operand1, operand2):
        print(f"sub: {operand1}, {operand2}")

        registerValue1 = self._get_register(operand1)
        registerValue2 = self._get_register(operand2)
        self._edit_register(operand1, registerValue1-registerValue2)

        self.log_register_state()

    def run_imul(self, operand1, operand2: list[str]):
        print(f"imul: {operand1}, {operand2}")

        raw = bytes.fromhex("".join(operand2))
        immediateValue = int.from_bytes(raw, byteorder="little", signed=True)
        registerValue = self._get_register(operand1)
        self._edit_register(operand1, immediateValue*registerValue)

        self.log_register_state()

    def run_mul(self, operand1, operand2):
        print(f"mul: {operand1}, {operand2}")

        registerValue1 = self._get_register(operand1)
        registerValue2 = self._get_register(operand2)
        self._edit_register(operand1, registerValue1*registerValue2)

        self.log_register_state()

    def run_idiv(self, operand1, operand2: list[str]):
        print(f"idiv: {operand1}, {operand2}")

        raw = bytes.fromhex("".join(operand2))
        immediateValue = int.from_bytes(raw, byteorder="little", signed=True)
        registerValue = self._get_register(operand1)

        if immediateValue == 0:
            Errors.C205(registerValue, immediateValue)

        result = abs(registerValue) // abs(immediateValue)
        if (registerValue < 0) != (immediateValue < 0):
            result = -result

        self._edit_register(operand1, result)

        self.log_register_state()

    def run_div(self, operand1, operand2):
        print(f"div: {operand1}, {operand2}")

        registerValue1 = self._get_register(operand1)
        registerValue2 = self._get_register(operand2)

        if registerValue2 == 0:
            Errors.C205(registerValue1, registerValue2)

        result = abs(registerValue1) // abs(registerValue2)
        if (registerValue1 < 0) != (registerValue2 < 0):
            result = -result

        self._edit_register(operand1, result)

        self.log_register_state()

    def run_icmp(self, operand1, operand2: list[str]):
        print(f"icmp: {operand1}, {operand2}")

        raw = bytes.fromhex("".join(operand2))
        TermTwo = int.from_bytes(raw, byteorder="little", signed=True)
        TermOne = self._get_register(operand1)

        self._set_flags(TermOne, TermTwo)
        self.log_flag_state()

    def run_cmp(self, operand1, operand2):
        print(f"cmp: {operand1}, {operand2}")
        
        termTwo = self._get_register(operand2)
        termOne = self._get_register(operand1)

        self._set_flags(termOne, termTwo)
        self.log_flag_state()

    def run_ijmp(self, operand1: list[str]): # operand1 = immediate = absoluteAddress (int)
        print(f"jump to: {operand1} (integer)")

        raw = bytes.fromhex("".join(operand1))
        absoluteAddress = int.from_bytes(raw, byteorder="little", signed=True)
        
        if absoluteAddress > SystemMemory.programReserve or absoluteAddress < 1:
            Errors.M102(absoluteAddress, 1, SystemMemory.programReserve) 
        # Eventually we need to validate the actual address is an instruction but for now its fine.

        self.programCounter = absoluteAddress

    def run_conditional_jmp(self, operand1, flag): # flag is an opcode. operand1 is the immediate address
        #Cpu.log_register_state()
        if (flag == "0E") and (self.flagEqual == True): # je
            self.run_ijmp(operand1)
        elif (flag == "0F") and (self.flagEqual == False): # jne
            self.run_ijmp(operand1)
        elif (flag == "10") and (self.flagLesser == True): # jl
            self.run_ijmp(operand1)
        elif (flag == "11") and (self.flagLesser == True or self.flagEqual == True): # jle
            self.run_ijmp(operand1)
        elif (flag == "12") and (self.flagGreater == True): # jg
            self.run_ijmp(operand1)
        elif (flag == "13") and (self.flagGreater == True or self.flagEqual == True): # jge
            self.run_ijmp(operand1)
        else:
            self.programCounter += 2 + 1

    def run_ipush(self, operand1: list[str]):
        print(f"ipush: {operand1}")
        if self.sp + 1 > self.stackEnd:
            Errors.M102(self.sp+1, self.stackStart, self.stackEnd)

        SystemMemory.edit(self.sp, operand1[0], 2)
        SystemMemory.edit(self.sp+1, operand1[1], 2)

        self.sp += 2

        self.log_register_state()

    def run_push(self, operand1):
        print(f"push: {operand1}")
        if self.sp + 1 > self.stackEnd:
            Errors.M102(self.sp+1, self.stackStart, self.stackEnd)

        value = self._get_register(operand1)
        raw = value.to_bytes(2, byteorder="little", signed=True)

        SystemMemory.edit(self.sp, f"{raw[0]:02X}", 2)
        SystemMemory.edit(self.sp+1, f"{raw[1]:02X}", 2)

        self.sp += 2

        self.log_register_state()

    def run_pop(self, operand1):
        print(f"pop: {operand1}")
        if self.sp - 2 < self.stackStart:
            Errors.M102(self.sp-2, self.stackStart, self.stackEnd)

        self.sp -= 2

        hex = [SystemMemory.memory[self.sp-1], SystemMemory.memory[self.sp]]
        raw = bytes.fromhex("".join(hex))
        value = int.from_bytes(raw, byteorder="little", signed=True)

        self._edit_register(operand1, value)

        self.log_register_state()

    def run_istore(self, operand1: list[str], operand2: list[str]): # address (immediate), value (immediate)
        print(f"istore: {operand1}, {operand2}")

        raw1 = bytes.fromhex("".join(operand1))
        address = int.from_bytes(raw1, byteorder="little", signed=True)

        if address > self.dataEnd < self.dataStart:
            Errors.M102(address, self.dataStart, self.dataEnd) 

        SystemMemory.edit(address, operand2[0], 3)
        SystemMemory.edit(address+1, operand2[1], 3)

    def run_store(self, operand1: list[str], operand2): # address (immediate), register (value)
        print(f"store: {operand1}, {operand2}")

        raw1 = bytes.fromhex("".join(operand1))
        address = int.from_bytes(raw1, byteorder="little", signed=False)

        if address < self.dataStart or address + 1 > self.dataEnd:
            Errors.M102(address, self.dataStart, self.dataEnd)

        value = self._get_register(operand2)
        raw = value.to_bytes(2, byteorder="little", signed=True)

        SystemMemory.edit(address, f"{raw[0]:02X}", 3)
        SystemMemory.edit(address+1, f"{raw[1]:02X}", 3)

    def run_load(self, operand1, operand2: list[str]): # register, address (immediate)
        print(f"load: {operand1}, {operand2}")

        raw = bytes.fromhex("".join(operand2))
        address = int.from_bytes(raw, byteorder="little", signed=False)

        if address < self.dataStart or address + 1 > self.dataEnd:
            Errors.M102(address, self.dataStart, self.dataEnd)

        hex = [SystemMemory.memory[address - 1], SystemMemory.memory[address]]
        raw = bytes.fromhex("".join(hex))
        value = int.from_bytes(raw, byteorder="little", signed=True)

        self._edit_register(operand1, value)

        self.log_register_state()

    def run_loadr(self, operand1, operand2): # register, register (address)
        print(f"load: {operand1}, {operand2}")

        address = self._get_register(operand2)

        if address < self.dataStart or address + 1 > self.dataEnd:
            Errors.M102(address, self.dataStart, self.dataEnd)

        hex = [SystemMemory.memory[address - 1], SystemMemory.memory[address]]
        raw = bytes.fromhex("".join(hex))
        value = int.from_bytes(raw, byteorder="little", signed=True)

        self._edit_register(operand1, value)

        self.log_register_state()

    def run_iout(self, operand1: list[str], operand2: list[str]): # port (immediate), input (immediate)
        raw = bytes.fromhex("".join(operand1))
        port = int.from_bytes(raw, byteorder="little", signed=True)

        if port == 1:
            _Ports.console(operand2)

    def run_out(self, operand1: list[str], operand2): # port (immediate), input (register)
        raw = bytes.fromhex("".join(operand1))
        port = int.from_bytes(raw, byteorder="little", signed=True)

        value = self._get_register(operand2)
        byte = value.to_bytes(2, byteorder="little", signed=True)

        if port == 1:
            _Ports.console([f"{item:02X}" for item in byte])

    def run_in(self, operand1, operand2: list[str]): # register, port (immediate)
        raw = bytes.fromhex("".join(operand2))
        port = int.from_bytes(raw, byteorder="little", signed=True)

        if port == 2:
            value = _Ports.keyboard()
            self._edit_register(operand1, value)
            self.log_register_state()


    def run_halt(self):
        self.running = False
        
    ### STOP RUN_X FUNCTIONS

    def program_loop(self):
        print("Starting program loop")
        self.running = True

        OPCODE_MAP = {
            "00" : self.run_halt,
            "01" : self.run_imov,
            "02" : self.run_mov,
            "03" : self.run_iadd,
            "04" : self.run_add,
            "05" : self.run_isub,
            "06" : self.run_sub,
            "07" : self.run_imul,
            "08" : self.run_mul,
            "09" : self.run_idiv,
            "0A" : self.run_div,
            "0B" : self.run_icmp,
            "0C" : self.run_cmp,
            "0D" : self.run_ijmp,
            "0E" : self.run_conditional_jmp,
            "0F" : self.run_conditional_jmp,
            "10" : self.run_conditional_jmp,
            "11" : self.run_conditional_jmp,
            "12" : self.run_conditional_jmp,
            "13" : self.run_conditional_jmp,
            "14" : self.run_ipush,
            "15" : self.run_push,
            "16" : self.run_pop,
            "17" : self.run_istore,
            "18" : self.run_store,
            "19" : self.run_load,
            "1A" : self.run_loadr,
            "1D" : self.run_iout,
            "1E" : self.run_out,
            "1F" : self.run_in
        }

        while self.running == True:
            if self.programCounter > SystemMemory.programReserve:
                Errors.C202(SystemMemory.programReserve, self.programCounter)
                
            mem = SystemMemory.memory # READ ONLY. When modifying, use SystemMemory.memory
            origin = self.programCounter-1

            opcode = mem[origin]
            instruction = OPCODE_MAP.get(opcode)

            if (instruction is (None)):
                Errors.C203(opcode, self.programCounter)

            elif opcode == "00": #
                instruction()
            elif opcode in ("01", "03", "05", "07", "09", "0B", "19", "1F"): # register, immediate
                instruction(mem[origin+1], [mem[origin+2], mem[origin+3]])
                self.programCounter += 3 + 1 
            elif opcode in ("14"): # immediate
                instruction([mem[origin+1], mem[origin+2]])
                self.programCounter += 2 + 1
            elif opcode in ("15", "16"): # register
                instruction(mem[origin+1])
                self.programCounter += 1 + 1
            elif opcode in ("17", "1D"): # immediate, immediate
                instruction([mem[origin+1], mem[origin+2]], [mem[origin+3], mem[origin+4]])
                self.programCounter += 4 + 1
            elif opcode in ("18", "1E"): # immediate, register
                instruction([mem[origin+1], mem[origin+2]], mem[origin+3])
                self.programCounter += 3 + 1
            
            elif opcode == "0D": # jmp
                instruction([mem[origin+1], mem[origin+2]])
            elif opcode in ("0E", "0F", "10", "11", "12", "13"): # conditional jmps are speciall
                instruction([mem[origin+1], mem[origin+2]], opcode)

            else: # register, register
                instruction(mem[origin+1], mem[origin+2])
                self.programCounter += 2 + 1
                
    def log_register_state(self):
        print(f"SP: {self.sp}")
        print(f"R1: {self.r1}")
        print(f"R2: {self.r2}")
        print(f"R3: {self.r3}")
        print(f"R4: {self.r4}")

    def log_flag_state(self):
        print(f"Greater: {self.flagGreater}")
        print(f"Equal: {self.flagEqual}")
        print(f"Lesser: {self.flagLesser}")

    def log_memory_ranges(self):
        print(f"Stack: {self.stackStart}-{self.stackEnd}")
        print(f"Data: {self.dataStart}-{self.dataEnd}")

HOST = "127.0.0.1"
PORT = 5000

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen(1)

subprocess.Popen(
    [sys.executable, "-u", "src/console.py"],
    creationflags=subprocess.CREATE_NEW_CONSOLE
)

console, _ = server.accept()

threading.Thread(target=_Ports.keyboard_listener, daemon=True).start()

SystemMemory = _SystemMemory(250, 192, 32, 26)
Cpu = _Cpu(2)


SystemMemory.load_into_memory("in.bin")
Cpu.log_memory_ranges()
Cpu.program_loop()

#Cpu.log_register_state()
#print(SystemMemory.access_memory())