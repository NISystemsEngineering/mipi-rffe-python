from os import path
import nidigital
from nimipi import rffe
from rfmd8090 import Rfmd8090

digital_project_path = path.abspath(r"nimipi\digiproj")
pin_map_file_path = path.join(digital_project_path, "PinMap.pinmap")
specifications_file_path = path.join(digital_project_path, "Specifications.specs")
levels_file_path = path.join(digital_project_path, "PinLevels.digilevels")
timing_file_path = path.join(digital_project_path, "Timing.digitiming")
pattern_directory_path = path.join(digital_project_path, "RFFE Command Patterns")

digital = nidigital.Session("PXIe-6570", True, False)

rffe.load_pin_map(digital, pin_map_file_path)
rffe.load_sheets(digital, specifications_file_path, levels_file_path, timing_file_path)
rffe.load_patterns(digital, pattern_directory_path)

digital.channels["RFFEVIO"].ppmu_configure_output_function(nidigital.PPMUOutputFunction.VOLTAGE.value)
digital.channels["RFFEVIO"].ppmu_configure_voltage_level(1.8)
digital.channels["RFFEVIO"].ppmu_configure_current_limit_range(0.032)
digital.channels["RFFEVIO"].ppmu_source()

multi_command_write = Rfmd8090.Band1Apt
multi_command_read = Rfmd8090.Band1Apt
multi_read_data = rffe.multi_command(digital, "RFFEDATA", multi_command_write, multi_command_read)

for register_data in multi_command_write:
    print("Slave: 0x{:02X}".format(register_data.slave_address) + \
        " | Register: 0x{:02X}".format(register_data.register_address) + \
        " | WriteData: " + ", ".join(map("0x{:02X}".format, register_data.write_data)))
print('-' * 50)
for register_data, read_data in zip(multi_command_read, multi_read_data):
    print("Slave: 0x{:02X}".format(register_data.slave_address) + \
        " | Register: 0x{:02X}".format(register_data.register_address) + \
        " | ReadData: " + ", ".join(map("0x{:02X}".format, read_data)))
print('-' * 50)

digital.close()