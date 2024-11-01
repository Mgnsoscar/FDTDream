import importlib.util

spec_win = importlib.util.spec_from_file_location(
    name='lumapi',  # Name of the .py file we want to import
    location=r'C:\\Program Files\\Lumerical\\v241\\api\\python\\lumapi.py'  # The directory of the lumapi file
)
lumapi = importlib.util.module_from_spec(spec_win)
spec_win.loader.exec_module(lumapi)