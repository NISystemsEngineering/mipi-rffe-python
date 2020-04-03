import nidigital
from nimipi import rffe

session = nidigital.Session("PXIe-6570", True, False, {"simulate": True, "driver_setup": {"Model": "6571"}})

rffe.load_digital_project(session)
rffe.enable_vio(session)

session.close()
