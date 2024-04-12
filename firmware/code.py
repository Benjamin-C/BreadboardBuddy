import math
import board
import digitalio
import pwmio
import microcontroller

fwversion = "1.0 4/11/24"

print()

debugCmds = False

class AssignablePin():
    def __init__(self, hwpin: microcontroller.Pin, num: int):
        self.hwpin: microcontroller.Pin = hwpin
        self._num: int = num
        self._numPrefix: str = None
        self._mode = "None"
        self._strPrefix: str = ""

    @property
    def num(self):
        return self._num

    @property
    def numPrefix(self):
        return self._numPrefix

    def digitalRead(self) -> bool:
        return False
    
    def getValue(self) -> any:
        return "err"
    
    def getMode(self) -> str:
        return self._mode
    
    def __str__(self):
        return f"{self._strPrefix}{self.num}"

class DigitalPin(AssignablePin):

    MODE_OUTPUT = "OUTPUT"
    MODE_INPUT = "INPUT"
    MODE_PULLUP = "PULLUP"
    MODE_PULLDOWN = "PULLDOWN"
    MODE_PWM = "PWM"

    PWM_MAX = 65535

    def __init__(self, hwpin: microcontroller.Pin, num: int, mode: str = "input"):
        super().__init__(hwpin=hwpin, num=num)
        self._numPrefix = ""
        self._strPrefix = "Digc"
        self._mayChangeMode = True
        self._pin = None
        self._setMode(mode)
    
    @property
    def mayChangeMode(self):
        return self._mayChangeMode
    
    @property
    def mode(self):
        return self._mode
    
    @mode.setter
    def mode(self, modestr):
        self.setMode(modestr)

    def _deinit(self):
        # Deinit specific pin types
        if isinstance(self._pin, pwmio.PWMOut):
            self._pin.deinit()
        elif isinstance(self._pin, digitalio.DigitalInOut):
            self._pin.deinit()
        # Clear the pin
        self._pin = None

    def _setDIO(self):
        # Only set up if we aren't already set up
        if not isinstance(self._pin, digitalio.DigitalInOut):
            # Deinit any other existing pin modes
            self._deinit()
            # Initialize DigitalInOut
            self._pin = digitalio.DigitalInOut(self.hwpin)

    def _setPWM(self):
        # If we're not already set up as PWM
        if not isinstance(self._pin, pwmio.PWMOut):
            # Deinit any current mode
            self._deinit()
            # Initialize PWM
            self._pin = pwmio.PWMOut(self.hwpin)

    def setMode(self, modestr: str):
        ''' Sets the mode of this pin.
        Returns True if the mode was changed or if it was already the new mode
        Returns False if the mode wasn't changed due to an invalid mode
        Raises a RuntimeError if you aren't allowed to change the mode
        '''
        if self._mayChangeMode:
            return self._setMode(modestr)
        else:
            raise RuntimeError("You can't change the mode of this")
    
    def _setMode(self, modestr: str):
        modestr = modestr.upper()
        if modestr == 'OUTPUT' or modestr == "OUT":
            self._setDIO()
            self._pin.direction = digitalio.Direction.OUTPUT
            self._mode = self.MODE_OUTPUT
        elif modestr == 'INPUT' or modestr == "IN":
            self._setDIO()
            self._pin.direction = digitalio.Direction.INPUT
            self._pin.pull = None
            self._mode = self.MODE_INPUT
        elif modestr == 'PULLUP':
            self._setDIO()
            self._pin.direction = digitalio.Direction.INPUT
            self._pin.pull = digitalio.Pull.UP
            self._mode = self.MODE_PULLUP
        elif modestr == 'PULLDOWN':
            self._setDIO()
            self._pin.direction = digitalio.Direction.INPUT
            self._pin.pull = digitalio.Pull.DOWN
            self._mode = self.MODE_PULLDOWN
        elif modestr == "PWM":
            self._setPWM()
            self._mode = self.MODE_PWM
        else:
            return False
        return True

    def setValue(self, value):
        self._pin.value = value

    def getValue(self) -> any:
        return ("H" if self._pin.value else "L") if self._mode != DigitalPin.MODE_PWM else f"{self._pin.duty_cycle/self.PWM_MAX:0.3f}"
    
    def digitalRead(self) -> bool:
        if self._mode != self.MODE_PWM:
            return self._pin.value
        else:
            return self._pin.duty_cycle > self.PWM_MAX/2
    
class LEDPin(DigitalPin):
    def __init__(self, hwpin: microcontroller.Pin, num=0):
        super().__init__(hwpin=hwpin, num=num, mode="output")
        self._numPrefix = "led"
        self._strPrefix = "Led"
        self._mayChangeMode = False

class Command():
    def __init__(self):
        pass

    def onInstruction(self, pins: list[AssignablePin], names: list[str], arg: list[str]):
        self.onQuestion(pins, names, arg)

    def onQuestion(self, pins: list[AssignablePin], names: list[str], arg: list[str]):
        pass

# commands = {"help": HelpCommand(), "mode": ModeCommand(), "read": ReadCommand(), "set": SetCommand(), "binary": BinaryCommand()}


class HelpCommand(Command):
    def onQuestion(self, pins: list[AssignablePin], names: list[str], arg: list[str]):
        print("BreadBoard Buddy firmware v{fwversion}")
        print("Commands:")
        print("  `mode? <pins>`")
        print("  `mode <pins> <modes>`")
        print("    Gets/sets the mode of digital pins. Modes are OUTPUT, INPUT, PULLUP, PULLDOWN")
        print("  `read? <pins>`")
        print("    Reads the values from pins")
        print("  `set <pins> <values>`")
        print("    Sets the values of digital pins")
        print("  `binary? <pins> [base]`")
        print("  `binary <pins> <value> [base]`")
        print("    Gets/sets pins to a value optionally in a given base. Bases are BIN, OCT, DEC, HEX.")
        print("    Pins are specified MSB first, and numbers may be truncated from the MSB end if needed")
        print("Pins can be specified as:")
        print("  Numbers. Valid numbers are 0-15, LED")
        print("  Ranges with a start and end pin seperated by a dash. Pins will be used in the order specified")
        print("  Comma seperated lists combining any of the above")
        print("  EX: 1,5,8-15")
        print("")
        print("Visit https://github.com/Benjamin-C/BreadboardBuddy/blob/main/docs/docs.pdf")

class ModeCommand(Command):
    def onInstruction(self, pins, names, arg):
        # Check if any modes were given
        if len(arg) < 1:
            print("You must specify the mode to set")
            return
        # Get the list of all modes
        modes = arg[0].split(",")
        # Throw an error if there is an invalid number of errors.
        if len(modes) < 0 or (len(modes) != 1 and len(modes) != len(pins)):
            print("You must specify either a single mode for all pins, or a mode for each pin")
            print("There was a fatal error, aborting")
            return
        # Try to set the mode for each pin
        changed = False
        for i in range(len(pins)):
            pin = pins[i]
            # Check if the pins are digital
            if isinstance(pin, DigitalPin):
                # Set the mode or say why we can't
                try:
                    if pin.setMode(modes[i] if len(modes) > 1 else modes[0]):
                        changed = True
                    else:
                        print(f"Invalid mode for pin {names[i]}, skipping")
                        continue
                except:
                    print(f"You can't change the mode for pin {names[i]}, skipping")
                    continue
            else:
                print(f"Pin {names[i]} is not digital, skipping")
                continue
        if changed:
            print("OK")
    
    def onQuestion(self, pins, names, arg):
        # Print the mode of all pins
        print(",".join([p.getMode() for p in pins]))

class DigitalCommand(Command):
    def __init__(self):
        super().__init__()
        self.setcmd = SetCommand()

    def onInstruction(self, pins: list[AssignablePin], names: list[str], arg: list[str]):
        self.setcmd.onInstruction(pins, names, arg)
    
    def onQuestion(self, pins: list[AssignablePin], names: list[str], arg: list[str]):
        answer = ""
        for i in range(len(pins)):
            pin = pins[i]
            # Check if the pins are digital
            if isinstance(pin, DigitalPin):
                answer += "H" if pin.digitalRead() else "L"
        print(answer)

class ReadCommand(Command):
    def onQuestion(self, pins: list[AssignablePin], names: list[str], arg: list[str]):
        print(",".join([p.getValue() for p in pins]))
        return super().onQuestion(pins, names, arg)
    
class SetCommand(Command):
    def onInstruction(self, pins: list[AssignablePin], names: list[str], arg: list[str]):
        # Check if any modes were given
        if len(arg) < 1:
            print("You must specify the mode to set")
            return
        # Get the list of all modes
        values = arg[0].split(",")
        # Throw an error if there is an invalid number of errors.
        if len(values) < 0 or (len(values) != 1 and len(values) != len(pins)):
            print("You must specify either a single mode for all pins, or a mode for each pin")
            print("There was a fatal error, aborting")
            return
        # Try to set the mode for each pin
        changed = False
        for i in range(len(pins)):
            pin = pins[i]
            val = values[i] if len(values) > 1 else values[0]
            # Check if the pins are digital
            if isinstance(pin, DigitalPin):
                # Set the mode or say why we can't
                if pin.mode == DigitalPin.MODE_OUTPUT:
                    v = parseHighLow(val)
                    if v is not None:
                        pin.setValue(v)
                        changed = True
                        continue
                    else:
                        print(f"Invalid value {val} for pin {names[i]}, skipping")
                        continue
                elif pin.mode == DigitalPin.MODE_PWM:
                    v = parseHighLow(val)
                    if v is not None:
                        pin.setValue(DigitalPin.PWM_MAX if v else 0)
                        changed = True
                        continue
                    else:
                        print(f"Invalid value {val} for pin {names[i]}, skipping")
                        continue
                else:
                    # Setting input pins has no effect
                    continue
            else:
                print(f"Pin {names[i]} is not digital, skipping")
                continue
        if changed:
            print("OK")

    def onQuestion(self, pins: list[AssignablePin], names: list[str], arg: list[str]):
        print('Use "read" to read from pins')

class BinaryCommand(Command):
    def calcBase(self, arg):
        ''' Reads the base from the first element of the array, or returns 2 if it doesn't exist or isn't on the list '''
        base = 2
        if len(arg) > 0:
            arg[0] = arg[0].upper()
            if arg[0] == 'DEC':
                base = 10
            elif arg[0] == 'HEX':
                base = 16
            elif arg[0] == 'OCT':
                base = 8
            elif arg[0] == 'BIN':
                base = 2
            else:
                print("Unknown base specified, assuming binary.")
        return base
    
    def onInstruction(self, pins: list[AssignablePin], names: list[str], arg: list[str]):
        # Check we have a number
        if len(arg) == 0:
            print('You must specify a value to set, or use "binary?" to read values. Aborting.')
            return
        # Get the base
        base = self.calcBase(arg[1:])
        # Parse the value from the given base
        value = 0
        try:
            value = int(arg[0], base)
        except:
            print(f"Invalid number {arg[0]} for base {base}. Aborting.")
            return
        # Check we can write to all the pins
        for i in range(len(pins)):
            if not isinstance(pins[i], DigitalPin):
                print(f"Pin {names[i]} is not a writable pin. Aborting.")
                return
        # Write to the pins, MSB first
        for pin in pins[::-1]:
            pin.setValue(value % 2)
            value //= 2
        print("OK")
    
    def onQuestion(self, pins: list[AssignablePin], names: list[str], arg: list[str]):
        # Get the desired base
        base = self.calcBase(arg)
        # Calculate how many digits to pad to
        digitCount = math.ceil(math.log(2**len(pins), base))
        # Read the value
        value = 0
        for pin in pins:
            value <<= 1
            value |= 1 if pin.digitalRead() else 0
        # Print the value
        answer = ""
        for i in range(digitCount):
            d = value % base
            value //= base
            answer = "0123456789ABCDEF"[d] + answer
        print(answer)

# List of all possible commands
commands = {"help": HelpCommand(), "mode": ModeCommand(), "read": ReadCommand(), "set": SetCommand(), "binary": BinaryCommand()}

def parseHighLow(val):
    if val.upper() in ["H", "HIGH", "1", "ON"]:
        return True
    elif val.upper() in ["L", "LOW", "0", "OFF"]:
        return False
    else:
        return None

# Add the pins
pinsByNumber = {}
for i in range(15+1):
    exec(f"pinsByNumber['{i}'] =  DigitalPin(board.GP{i}, {i})")
pinsByNumber['26'] = DigitalPin(board.GP26, 26)
pinsByNumber["led"] = LEDPin(board.LED)

for i in range(4):
    # TODO analog pins go here
    pass

pinsByName = {"d0": pinsByNumber["0"], "d1": pinsByNumber["1"], "d2": pinsByNumber["2"], "d3": pinsByNumber["3"]}

def getPin(name: str) -> AssignablePin:
    # Check if the pin is referenced by number
    name = name.lower()
    if name in pinsByNumber:
        return pinsByNumber[name]
    # Then check if the pin is being specified by a nickname
    elif name in pinsByName:
        return pinsByName[name]
    # If neither, return none
    return None

# testCmds = ["mode? d0-d3,7,9-12,LED", "mode d0-d3,7,LED OUT", "mode 9-12 OUT,OUT,IN,PULLUP", "mode? d0-d3,7,9-12,LED"]
testCmds = ["mode 0-3 output", "set 0-3 h,h,l,l", "read 0-3", "binary? 0-3"]

while True:
    # Get the user's input
    cmd = input("BB> ")
    # if len(testCmds) > 0:
    #     cmd = testCmds[0]
    #     testCmds = testCmds[1:]
    #     print("CMD=" + cmd)

    # Prep variables to parse the command into
    verb = ""
    isQuestion = False
    pins = []
    pinNames = []
    args = []
    error = False
    
    # Parse the command
    words = cmd.split(" ")
    if len(words) >= 1:
        # Collect the verb from the command
        verb = words[0]
        if len(verb) > 0 and verb[-1] == '?':
            isQuestion = True
            verb = verb[:-1]
    if len(words) >= 2:
        # Collect the pins from the command
        for pn in words[1].split(","):
            # First check if the pin was specified by a range
            if '-' in pn:
                # Find the bounds of the range
                bounds = pn.split("-")
                a = getPin(bounds[0])
                b = getPin(bounds[1])
                if a is not None and b is not None:
                    # Make sure the bounds of the range are of the same type
                    if a.numPrefix == b.numPrefix and a.numPrefix is not None:
                        # Add all pins in the range to the pin list
                        for i in range(a.num, b.num+1):
                            # Get the next pin in the range
                            p = getPin(a.numPrefix + str(i))
                            # Make sure that it exists, and error if not
                            if p is not None:
                                pins.append(p)
                                if i == a.num:
                                    pinNames.append(bounds[0])
                                elif i == b.num:
                                    pinNames.append(bounds[1])
                                else:
                                    pinNames.append(p.numPrefix + str(p.num))
                            else:
                                print(f"Invalid pin in range {pn}")
                                error = True
                                break
                        # Added pins, so go to next list item
                        continue
                    # The bounds were not of the same type
                    else:
                        print(f"Invalid range {pn}. You may not mix pin types in a range.")
                        error = True
                        break
                else:
                    print(f"One of the bounds of the range {pn} is invalid")
                    error = True
                    break
            # The pin was not specified by range
            else:
                # Try to get the pin by name or number
                p = getPin(pn)
                # If it exists, add it and go to the next list item
                if p is not None:
                    pins.append(p)
                    pinNames.append(pn)
                    continue
                # If it doesn't exist, throw an error
                else:
                    print(f"Invalid pin name {pn}")
                    error = True
                    break
    if len(words) >= 3:
        # Collect any additional arguments from the command
        args = words[2:]

    if debugCmds:
        print(f"CMD:{verb} Q?{isQuestion} PIN:{len(pins)}[{','.join([str(p) for p in pins])}] PN:{pinNames} ARGS:{args}")

    # Only execute the command if it could be parsed correctly
    if error:
        print("An error occurred during the parsing of the command, aborting")
        continue
    if verb in commands:
        if isQuestion:
            commands[verb].onQuestion(pins, pinNames, args)
        else:
            commands[verb].onInstruction(pins, pinNames, args)
    else:
        print('Please tell me what to do. You can ask "help?" if you need help.')
