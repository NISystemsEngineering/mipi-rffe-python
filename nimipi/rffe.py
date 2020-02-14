import nidigital, enum

class __BitOrder(enum.Enum): # created because beta version of nidigital does not define this enum
    MSB_FIRST = 2500
    LSB_FIRST = 2501


class __DataMapping(enum.Enum): # created because beta version of nidigital does not define this enum
    BROADCAST = 2600
    SITE_UNIQUE = 2601


class RffeException(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message


class __Command(enum.Enum):
    REG_0_WRITE = 0
    REG_WRITE = 1
    REG_READ = 2
    REG_READ_HR = 3
    REG_WRITE_EXT = 4
    REG_READ_EXT = 5
    REG_READ_EXT_HR = 6
    REG_WRITE_EXT_LONG = 7
    REG_READ_EXT_LONG = 8
    REG_READ_EXT_LONG_HR = 9


class RegisterData:
    def __init__(self, slave_address, register_address, write_data, byte_count):
        self.slave_address = slave_address
        self.register_address = register_address
        self.write_data = write_data
        self.byte_count = byte_count


def __data_check_logic(register_data, upper_byte_count_limit, upper_address_limit):
    """ Checks that register data is in range of provided constraints. """
    assert isinstance(register_data, RegisterData)
    slave_address_in_range = register_data.slave_address in range(0x0, 0x10)
    register_address_in_range = register_data.register_address in range(0x0, upper_address_limit + 1)
    byte_count_in_range = register_data.byte_count in range(0, upper_byte_count_limit + 1)
    if slave_address_in_range and register_address_in_range and byte_count_in_range:
        return
    if not slave_address_in_range:
        raise RffeException(5000, "Slave address out of range. Expected [0x00, 0x10), found " + "0x{:02X}.".format(register_data.slave_address))
    if not register_address_in_range:
        raise RffeException(5000, "Register address out of range. Expected [0x00, " + "0x{:02X}".format(upper_address_limit) + "], found " + "0x{:02X}.".format(register_data.register_address) + " Check that the address is valid based on the selected command.")
    if not byte_count_in_range:
        raise RffeException(5000, "Byte count out of range. Expected [0, " + str(upper_byte_count_limit) + "], found " + str(register_data.byte_count) + '.')
    raise RffeException(5000, "Unknown exception occured at __data_check_logic.")


def __data_check(command, register_data):
    """ Checks that register data is in range based on command type. """
    if command == __Command.REG_0_WRITE:
        return __data_check_logic(register_data, 1, 0xFFFF) # addr not used, set to max
    if command == __Command.REG_WRITE:
        return __data_check_logic(register_data, 1, 0x1F)
    if command == __Command.REG_READ or command == __Command.REG_READ_HR:
        return __data_check_logic(register_data, 1, 0x1F)
    if command.value in range(__Command.REG_WRITE_EXT.value, __Command.REG_READ_EXT_HR.value + 1):
        return __data_check_logic(register_data, 16, 0xFF)
    if command.value in range(__Command.REG_WRITE_EXT_LONG.value, __Command.REG_READ_EXT_LONG_HR.value + 1):
        return __data_check_logic(register_data, 8, 0xFFFF)
    raise RffeException(5000, "The specified command " + command.name + " is not supported.")


def __create_waveforms(session, pin_name, command):
    """ Creates 1 bit sample width source and 8 bit sample width capture waveforms, using appropriate name for the command. """
    assert isinstance(session, nidigital.Session)
    if command == __Command.REG_0_WRITE:
        source_waveform_name = "Reg0Write"
    elif command == __Command.REG_WRITE:
        source_waveform_name = "RegWrite"
    elif command == __Command.REG_WRITE_EXT:
        source_waveform_name = "RegWriteExt"
    elif command == __Command.REG_WRITE_EXT_LONG:
        source_waveform_name = "RegWriteExtLong"
    elif command == __Command.REG_READ or command == __Command.REG_READ_HR:
        source_waveform_name = "RegRead"
    elif command == __Command.REG_READ_EXT or command == __Command.REG_READ_EXT_HR:
        source_waveform_name = "RegReadExt"
    elif command == __Command.REG_READ_EXT_LONG or command == __Command.REG_READ_EXT_LONG_HR:
        source_waveform_name = "RegReadExtLong"
    else:
        raise RffeException(5000, "The specified command " + command.name + " is not supported.")
    session.create_source_waveform_serial(pin_name, source_waveform_name, __DataMapping.BROADCAST.value, 1, __BitOrder.MSB_FIRST.value)
    session.create_capture_waveform_serial(pin_name, source_waveform_name, 8, __BitOrder.MSB_FIRST.value)
    return source_waveform_name


def __parity_calc(input_string):
    """ Calculates and returns an odd parity bit.
        For an even number of 1s, this function returns a 1.
        For an odd number of 1s, this function returns a 0. """
    assert isinstance(input_string, str)
    return str(1 - input_string.count('1') % 2)


def __convert_string_to_numeric_array(string):
    """ Converts a numeric string to an array of integers. """
    return [int(char) for char in string]


def __create_source_waveform_data(command, register_data):
    """ Creates data to write into source waveform. """
    assert isinstance(register_data, RegisterData)
    if command == __Command.REG_0_WRITE:
        # For Reg0Write, build 4 bit SA and 7 bit Data with parity.
        # COMMAND/ADDRESS/DATA FRAME
        slave_address_bit_string = "{:04b}".format(register_data.slave_address)
        register_data_bit_string = "{:07b}".format(register_data.write_data[0]) # only take first element of register data
        # Separate concatenated string w/o command bits due to pattern structure
        command_bits = '1'
        parity_bit = __parity_calc(slave_address_bit_string + command_bits + register_data_bit_string)
        data_frame = slave_address_bit_string + register_data_bit_string + parity_bit
        return (1, __convert_string_to_numeric_array(data_frame))
    if command == __Command.REG_WRITE:
        # For RegWrite, build 4 bit SA, 5 bit Addr, and 8 bit Data with parity.
        # COMMAND/ADDRESS FRAME
        slave_address_bit_string = "{:04b}".format(register_data.slave_address)
        register_address_bit_string = "{:05b}".format(register_data.register_address)
        register_data_bit_string = "{:08b}".format(register_data.write_data[0]) # only take first element of register data
        # Separate concatenated string w/o command bits due to pattern structure
        command_bits = "010" # Add command bits for parity check
        parity_bit = __parity_calc(slave_address_bit_string + command_bits + register_address_bit_string)
        data_frame = slave_address_bit_string + register_address_bit_string + parity_bit
        data_frame = data_frame + register_data_bit_string + __parity_calc(register_data_bit_string)
        return (1, __convert_string_to_numeric_array(data_frame))
    if command == __Command.REG_READ or command == __Command.REG_READ_HR:
        # For RegRead<HR> , build 4 bit SA and 5 bit Addr with parity.
        # COMMAND/ADDRESS FRAME
        slave_address_bit_string = "{:04b}".format(register_data.slave_address)
        register_address_bit_string = "{:05b}".format(register_data.register_address)
        # Separate concatenated string w/o command bits due to pattern structure
        command_bits = "011" # Add command bits for parity check
        parity_bit = __parity_calc(slave_address_bit_string + command_bits + register_address_bit_string)
        data_frame = slave_address_bit_string + register_address_bit_string + parity_bit
        return (1, __convert_string_to_numeric_array(data_frame))
    raise RffeException(5000, "The specified command " + command.name + " is not supported.")


def __burst_command(session, pin_name, command, register_data):
    """ Bursts RFFE """
    assert isinstance(session, nidigital.Session)
    assert isinstance(register_data, RegisterData)
    __data_check(command, register_data)
    source_waveform_name = __create_waveforms(session, pin_name, command)
    byte_count, source_waveform_data = __create_source_waveform_data(command, register_data)
    session.write_source_waveform_broadcast(source_waveform_name, source_waveform_data)
    session.write_sequencer_register("reg0", byte_count)
    session.burst_pattern("", source_waveform_name, True, True, 10)
    if command == __Command.REG_0_WRITE or command == __Command.REG_WRITE:
        return
    if command == __Command.REG_READ:
        capture_waveform = session.fetch_capture_waveform("", source_waveform_name, register_data.byte_count, 1)
        return list(capture_waveform[0])
    raise RffeException(5000, "The specified command " + command.name + " is not supported.")


def load_patterns(session, pattern_directory_path):
    """ Loads all *.digipat files in the specified directory onto the instrument. """
    assert isinstance(session, nidigital.Session)
    from glob import glob
    from os import path
    digipat_file_paths = glob(path.join(pattern_directory_path, "*.digipat"))
    for digipat_path in digipat_file_paths:
        session.load_pattern(digipat_path)


def load_pin_map(session, pin_map_file_path):
    """ Calls nidigital.load_pin_map using the specified file path.
        This function is included to keep parity between the LabVIEW reference architecture and Python port."""
    assert isinstance(session, nidigital.Session)
    session.load_pin_map(pin_map_file_path)
    

def load_sheets(session, specifications_file_path, levels_file_path, timing_file_path):
    """ Loads specifications, levels, and timing sheets onto the instrument then applies them. """
    assert isinstance(session, nidigital.Session)
    session.load_specifications(specifications_file_path)
    session.load_levels(levels_file_path)
    session.load_timing(timing_file_path)
    session.apply_levels_and_timing("", levels_file_path, timing_file_path, "", "", "")


def reg0_write(session, pin_name, register_data):
    """ Bursts a Reg0Write command. This function returns None. """
    return __burst_command(session, pin_name, __Command.REG_0_WRITE, register_data)


def reg_write(session, pin_name, register_data):
    """ Bursts a RegWrite command. This function returns None. """
    return __burst_command(session, pin_name, __Command.REG_WRITE, register_data)


def reg_read(session, pin_name, register_data):
    """ Bursts a RegRead command. This function returns one channel of read data. """
    return __burst_command(session, pin_name, __Command.REG_READ, register_data)


def multi_command(session, pin_name, multi_command_write, multi_command_read):
    """ Uses looping to execute multiple register writes and register reads. """
    for write_command in multi_command_write:
        reg_write(session, pin_name, write_command)
    return [reg_read(session, pin_name, read_command) for read_command in multi_command_read]
