from typing import Literal

# region General Settings
DIRECTION_DEFINITIONS = Literal["axis", "unit-vector", "k-vector"]
POLARIZATION_DEFINITIONS = Literal["angle", "S", "P"]
INJECTION_AXES = Literal["x-axis", "y-axis", "z-axis"]
DIRECTIONS = Literal["forward", "backward"]
CONVERSIONS = Literal["center frequency", "maximum frequency", "minimum frequency",
                      "center wavelength", "maximum wavelength", "minimum wavelength"]
PLANE_WAVE_TYPES = Literal["Bloch/periodic", "BFAST", "Diffracting"]
AXES = Literal["x", "y", "z"]
# endregion General Settings

# region Frequency Wavelength Settings
PULSE_TYPES = Literal["standard", "broadband"]
# endregion Frequency Wavelength Settings
