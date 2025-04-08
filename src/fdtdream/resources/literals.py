from typing import Literal


# region Standard Literals
EXTREMITIES = Literal["x_min", "x_max", "y_min", "y_max", "z_min", "z_max"]
AXES = Literal["x", "y", "z"]
LENGTH_UNITS = Literal["m", "cm", "mm", "um", "nm", "pm", "angstrom", "fm"]
TIME_UNITS = Literal["s", "ms", "us", "ns", "ps", "fs"]
FREQUENCY_UNITS = Literal["Hz", "KHz", "MHz", "GHz", "THz", "PHz"]
# endregion

INDEX_UNITS = Literal["m", "microns", "nm"]
DIMENSION = Literal["2D", "3D"]
BOUNDARY_TYPES = Literal["PML", "Metal", "Periodic", "Symmetric", "Anti-Symmetric", "Bloch", "PMC"]
BOUNDARY_TYPES_LOWER = Literal["pml", "metal", "periodic", "symmetric", "anti-symmetric", "bloch", "pmc"]
BOUNDARIES = Literal["x min bc", "x max bc", "y min bc", "y max bc", "z min bc", "z max bc"]
BOUNDARIES_INC_ALL = Literal["x min bc", "x max bc", "y min bc", "y max bc", "z min bc", "z max bc"]
PML_PARAMETERS = Literal["profile", "layers", "kappa", "sigma", "polynomial", "alpha",
                         "alpha_polynomial", "min_layers", "max_layers"]
PML_PROFILES = Literal["standard", "stabilized", "steep angle", "custom"]
PML_TYPES = Literal["stretched coordinate PML", "uniaxial anisotropic PML (legacy)"]
BLOCH_UNITS = Literal["bandstructure", "SI"]
DEFINE_MESH_BY = Literal["mesh cells per wavelength", "maximum mesh step",
                         "max mesh step and mesh cells per wavelength", "number of mesh cells"]
MESH_REFINEMENT = Literal["staircase", "conformal variant 0", "conformal variant 1", "conformal variant 2",
                          "dielectric volume average", "volume average", "Yu-Mittra method 1", "Yu-Mittra method 2",
                          "precise volume average"]
MESH_TYPE = Literal["auto non-uniform", "custom non-uniform", "uniform"]
MATERIAL_TYPE = Literal["(n,k) Material", "Analytic material", "Chi2", "Chi3 Raman Kerr", "Chi3/Chi2", "Conductive 2D",
                        "Conductive 3D", "Current Driven Gain (version 1.0.0)", "Debye", "Dielectric",
                        "Four-Level Two-Electron (Version 1.0.0)", "Graphene", "Index perturbation", "Kerr nonlinear",
                        "Lorentz", "Magnetic Electric Lorentz (Version 1.0.0)", "PEC", "Paramagnetic", "Plasma",
                        "Sampled 2D data", "Sampled 3D data", "Sellmeier", "<Object defined dielectric>"]
ANISOTROPY = Literal["None", "Diagonal"]
MATERIAL_LENGTH_UNITS = Literal["m", "cm", "mm", "microns", "nm"]
MATERIAL_FREQUENCY_UNITS = Literal["Hz", "KHz", "MHz", "GHz", "THz", "inverse cm"]
SAMPLE_SPACINGS = Literal["uniform", "chebyshev", "custom"]

PULSE_TYPES = Literal["standard", "broadband"]
BEAM_PARAMETERS = Literal["Waist size and position", "Beam size and divergence angle"]


PLANE_WAVE_TYPES = Literal["Bloch/periodic", "BFAST", "Diffracting"]
WAVE_SHAPES = Literal["Plane wave", "Gaussian", "Cauchy-Lorentzian"]
DEFINE_BY = Literal["wavelength", "frequency"]
EXTRACTION_TYPES = Literal["3d geometry model", "2d geometry model", "full index model"]


# region Monitors

DATA_TO_RECORD = Literal["ex", "ey", "ez", "hx", "hy", "hz", "px", "py", "pz", "power"]
MONITOR_TYPES_ALL = Literal["point", "linear x", "linear y", "linear z",
                            "2d x-normal", "2d y-normal", "2d z-normal", "3d"]
MONITOR_TYPES_3D = Literal["2d x-normal", "2d y-normal", "2d z-normal", "3d"]
MONITOR_TYPES_2D = Literal["2D x-normal", "2d y-normal", "2d z-normal"]

# endregion Monitors
