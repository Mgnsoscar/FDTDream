import importlib.util

# Where the lumerical python API is located. Change this to the location on your computer.
lumapi_location = r'C:\\Program Files\\Lumerical\\v241\\api\\python\\lumapi.py'

spec_win = importlib.util.spec_from_file_location(name='lumapi', location=lumapi_location)
lumapi = importlib.util.module_from_spec(spec_win)
spec_win.loader.exec_module(lumapi)
