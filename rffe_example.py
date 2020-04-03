import nidigital
from nimipi import rffe
import rfmd8090

session = nidigital.Session("PXIe-6570", True, False, {"simulate": True, "driver_setup": {"Model": "6571"}})

rffe.load_digital_project(session)
rffe.enable_vio(session)

print("Slave | Register | Write | Read")
for slave_address, register_address, write_data in rfmd8090.band1_apt:
    rffe.extended_register_write(session, slave_address, register_address, write_data)
    read_data = rffe.extended_register_read(session, slave_address, register_address, len(write_data))
    formatted_write_data = '[' + ','.join(map("0x{:02X}".format, write_data)) + ']'
    formatted_read_data = '[' + ','.join(map("0x{:02X}".format, read_data)) + ']'
    print("0x{:02X} | 0x{:02X} | {:s} | {:s}".format(slave_address, register_address,
                                                           formatted_write_data, formatted_read_data))

session.close()
