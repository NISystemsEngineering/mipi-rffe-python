import nidigital
import enum
import os.path
import glob


class _BitOrder(enum.Enum):  # created because beta version of nidigital does not define this enum
    MSB_FIRST = 2500
    LSB_FIRST = 2501


class _DataMapping(enum.Enum):  # created because beta version of nidigital does not define this enum
    BROADCAST = 2600
    SITE_UNIQUE = 2601


class RffeException(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message


def _format_site_list(bus_number: int) -> str:
    if bus_number < 0:
        return ""
    return "site" + str(bus_number)


def _int_to_bits(integer: int, width: int) -> list:
    return [(integer >> (width - 1 - i)) & 1 for i in range(width)]


def _calculate_odd_parity_bit(integers):
    if isinstance(integers, int):
        bits = _int_to_bits(integers, integers.bit_length())
    else:
        bits = [_calculate_odd_parity_bit(integer) for integer in integers]
    return 1 - sum(bits) % 2


def _get_digital_project_directory() -> str:
    return os.path.abspath(__file__ + r"\..\digiproj")


def _format_into_vector_statement() -> str:
    pass


def _raise_out_of_range_error(parameter_name: str, lower_limit: str, upper_limit: str, as_found: str) -> RffeException:
    raise RffeException(5000, f"{parameter_name} out of range. "
                              f"Expected [{lower_limit}, {upper_limit}] but found {as_found}.")


class _RffeCommand:
    @property
    def name(self) -> str:
        return self._raise_required_override_error(self.name)

    @property
    def alias(self) -> str:
        return self.__alias

    @property
    def _pin(self) -> str:
        return self.__pin

    @property
    def slave_address(self) -> int:
        return self.__slave_address

    @property
    def slave_address_field_width(self) -> int:
        return 4

    @property
    def register_address(self) -> int:
        return self.__register_address

    @property
    def register_address_field_width(self) -> int:
        return self._raise_required_override_error(self.register_address_field_width)

    @property
    def register_address_limit(self) -> int:
        return (1 << self.register_address_field_width) - 1

    @property
    def command(self) -> int:
        return self._raise_required_override_error(self.command)

    @property
    def command_field_width(self) -> int:
        return self._raise_required_override_error(self.command_field_width)

    @property
    def _command_bits(self) -> list:
        return _int_to_bits(self.command, self.command_field_width)

    def __init__(self, slave_address: int, register_address: int, alias=""):
        self.__alias = alias
        self.__pin = "RFFEDATA"
        self.__slave_address = slave_address
        self.__register_address = register_address

    def burst(self, session: nidigital.Session, bus_number=0) -> None:
        self._data_check()
        self._create_waveforms(session)
        source_waveform = self._build_source_waveform()
        self._write_source_waveform(session, source_waveform)
        site_list = _format_site_list(bus_number)
        session.burst_pattern(site_list, self.name, True, True, 10.0)

    def generate_vector_statements(self) -> list:
        self._data_check()
        header_vectors = self._generate_header_vectors()
        command_frame_vectors = self._generate_command_frame_vectors()
        address_frame_vectors = self._generate_address_frame_vectors()
        data_frame_vectors = self._generate_data_frame_vectors()
        return header_vectors + command_frame_vectors + address_frame_vectors + data_frame_vectors

    def _data_check(self) -> None:
        if self.slave_address > 0xF:
            _raise_out_of_range_error("Slave address", "0x0", "0xF", "0x{:02X}".format(self.slave_address))
        if self.register_address > self.register_address_limit:
            _raise_out_of_range_error("Register address", "0x00", "0x{:02X}".format(self.register_address_limit),
                                      "0x{:02X}".format(self.register_address))

    def _create_waveforms(self, session: nidigital.Session) -> None:
        session.pins[self._pin].create_source_waveform_serial(self.name, _DataMapping.BROADCAST.value, 1,
                                                              _BitOrder.MSB_FIRST.value)

    def _build_source_waveform(self) -> list:
        command_frame = self._build_command_frame()
        address_frame = self._build_address_frame()
        data_frame = self._build_data_frame()
        return command_frame + address_frame + data_frame

    def _write_source_waveform(self, session: nidigital.Session, waveform_data: list) -> None:
        session.write_source_waveform_broadcast(self.name, waveform_data)

    def _build_command_frame(self) -> list:
        return []

    def _build_address_frame(self) -> list:
        return []

    def _build_data_frame(self) -> list:
        return []

    def _generate_header_vectors(self) -> list:
        return []

    def _generate_command_frame_vectors(self) -> list:
        return []

    def _generate_address_frame_vectors(self) -> list:
        return []

    def _generate_data_frame_vectors(self) -> list:
        return []

    def _raise_required_override_error(self, func: object):
                raise RffeException(5000, f"Developer error. Override required for {func} by {self}.")


class _RffeReg0WriteCommand(_RffeCommand):
    pass


class _RffeStandardCommand(_RffeCommand):
    pass


class _RffeRegWriteCommand(_RffeStandardCommand):
    pass


class _RffeRegReadCommand(_RffeStandardCommand):
    pass


class _RffeExtendedCommand(_RffeCommand):
    @property
    def register_address_field_width(self) -> int:
        return 8

    @property
    def command_field_width(self) -> int:
        return 4

    @property
    def register_data(self) -> list:
        return self._register_data

    @property
    def byte_count(self) -> int:
        return self._raise_required_override_error(self.byte_count)

    @property
    def byte_count_field_width(self) -> int:
        return 8 - self.command_field_width

    @property
    def byte_count_limit(self) -> int:
        return 1 << self.byte_count_field_width

    def __init__(self, slave_address: int, register_address: int, register_data: list, alias=""):
        super().__init__(slave_address, register_address, alias)
        self._register_data = register_data

    def _data_check(self) -> None:
        super()._data_check()
        if self.byte_count not in range(1, self.byte_count_limit + 1):
            _raise_out_of_range_error("Byte count", '1', str(self.byte_count_limit), str(self.byte_count))

    def _build_command_frame(self) -> list:
        slave_address_bits = _int_to_bits(self.slave_address, 4)
        byte_count_bits = _int_to_bits(self.byte_count - 1, self.byte_count_field_width)
        parity_bit = _calculate_odd_parity_bit(slave_address_bits + self._command_bits + byte_count_bits)
        return slave_address_bits + byte_count_bits + [parity_bit]

    def _build_address_frame(self) -> list:
        num_bytes = self.register_address_field_width >> 3
        address_frame = [0] * (self.register_address_field_width + num_bytes)
        for i in range(num_bytes):
            shift_amount = (num_bytes - 1 - i) << 3
            shifted_register_address = self.register_address >> shift_amount
            shifted_register_address_bits = _int_to_bits(shifted_register_address, 8)
            offset = i << 3 + i
            address_frame[offset:offset + 8] = shifted_register_address_bits
            address_frame[offset + 8] = _calculate_odd_parity_bit(shifted_register_address_bits)
        return address_frame

    def _write_source_waveform(self, session: nidigital.Session, waveform_data: list) -> None:
        super()._write_source_waveform(session, waveform_data)
        session.write_sequencer_register("reg0", self.byte_count)


class _RffeRegWriteExtCommand(_RffeExtendedCommand):
    @property
    def name(self) -> str:
        return "RegWriteExt"

    @property
    def command(self) -> int:
        return 0b0000

    @property
    def byte_count(self) -> int:
        return len(self.register_data)

    def _build_data_frame(self) -> list:
        data_frame = [0] * (self.byte_count * 9)
        for i in range(len(self.register_data)):
            data_bits = _int_to_bits(self.register_data[i], 8)
            offset = i << 3 + i
            data_frame[offset:offset + 8] = data_bits
            data_frame[offset + 8] = _calculate_odd_parity_bit(data_bits)
        return data_frame


class _RffeRegWriteExtLongCommand(_RffeRegWriteExtCommand):
    pass


class _RffeRegReadExtCommand(_RffeExtendedCommand):
    @property
    def name(self) -> str:
        return "RegReadExt"

    @property
    def command(self) -> int:
        return 0b0010

    @property
    def byte_count(self) -> int:
        return self.__byte_count

    def __init__(self, slave_address: int, register_address: int, byte_count: int, alias=""):
        super().__init__(slave_address, register_address, [], alias)
        self.__byte_count = byte_count

    def _create_waveforms(self, session: nidigital.Session) -> None:
        super()._create_waveforms(session)
        session.pins[self._pin].create_capture_waveform_serial(self.name, 8, _BitOrder.MSB_FIRST.value)

    def burst(self, session: nidigital.Session, bus_number=0) -> None:
        super().burst(session, bus_number)
        capture_data = session.fetch_capture_waveform(_format_site_list(bus_number), self.name, self.byte_count, 10)
        self._register_data = list(capture_data[bus_number])


class _RffeRegReadExtLongCommand(_RffeRegReadExtCommand):
    pass


def load_digital_project(session: nidigital.Session) -> None:
    digital_project_directory = _get_digital_project_directory()
    pin_map_path = os.path.join(digital_project_directory, "PinMap.pinmap")
    session.load_pin_map(pin_map_path)
    session.load_specifications(os.path.join(digital_project_directory, "Specifications.specs"))
    levels_path = os.path.join(digital_project_directory, "PinLevels.digilevels")
    session.load_levels(levels_path)
    timing_path = os.path.join(digital_project_directory, "Timing.digitiming")
    session.load_timing(timing_path)
    session.apply_levels_and_timing("", levels_path, timing_path, "", "", "")
    digital_pattern_paths = glob.glob(os.path.join(digital_project_directory, "*.digipat"))
    for pattern_path in digital_pattern_paths:
        session.load_pattern(pattern_path)


def enable_vio(session: nidigital.Session, bus_number=0):
    if bus_number < 0:
        channel_list = "RFFEVIO"
    else:
        channel_list = f"site{bus_number}/RFFEVIO"
    session.channels[channel_list].ppmu_output_function = nidigital.PPMUOutputFunction.VOLTAGE
    session.channels[channel_list].ppmu_voltage_level = 1.8
    session.channels[channel_list].ppmu_current_limit_range = 0.032
    session.channels[channel_list].ppmu_source()


def disable_vio(session: nidigital.Session, bus_number=0):
    if bus_number < 0:
        channel_list = "RFFEVIO"
    else:
        channel_list = f"site{bus_number}/RFFEVIO"
    session.channels[channel_list].selected_function = nidigital.SelectedFunction.OFF


def extended_register_write(session: nidigital.Session, slave_address: int, register_address: int,
                            register_data: list, bus_number=0):
    command = _RffeRegWriteExtCommand(slave_address, register_address, register_data)
    command.burst(session, bus_number)


def extended_register_read(session: nidigital.Session, slave_address: int, register_address: int,
                           byte_count: int, bus_number=0):
    command = _RffeRegReadExtCommand(slave_address, register_address, byte_count)
    command.burst(session, bus_number)
    return command.register_data
