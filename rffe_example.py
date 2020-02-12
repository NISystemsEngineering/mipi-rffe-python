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
# digital.channels["RFFEVIO"].ppmu_configure_current_limit_range(0.032)
digital.channels["RFFEVIO"].ppmu_source()

rffe.multi_command(digital, "RFFEDATA", Rfmd8090.Band1Apt, [])

input("Press any key to exit.")

digital.close()