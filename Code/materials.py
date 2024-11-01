from __future__ import annotations

# Standard-library imports
from typing import Literal, Union, TypedDict,  Any

# Third-party library imports
import numpy as np

from Code.base_classes import PARAMETER_TYPES

# Local library imports
from local_resources import DECIMALS, frequency_to_wavelength
from base_classes import SettingTab

########################################################################################################################
#                                             CONSTANTS AND LITERALS
########################################################################################################################

MATERIAL_TYPE = Literal["(n,k) Material", "Analytic material", "Chi2", "Chi3 Raman Kerr", "Chi3/Chi2", "Conductive 2D",
                        "Conductive 3D", "Current Driven Gain (version 1.0.0)", "Debye", "Dielectric",
                        "Four-Level Two-Electron (Version 1.0.0)", "Graphene", "Index perturbation", "Kerr nonlinear",
                        "Lorentz", "Magnetic Electric Lorentz (Version 1.0.0)", "PEC", "Paramagnetic", "Plasma",
                        "Sampled 2D data", "Sampled 3D data", "Sellmeier"]
ANISOTROPY = Literal["None", "Diagonal"]
MATERIAL_LENGTH_UNITS = Literal["m", "cm", "mm", "microns", "nm"]
MATERIAL_FREQUENCY_UNITS = Literal["Hz", "KHz", "MHz", "GHz", "THz", "inverse cm"]

########################################################################################################################
#                        CLASSES FOR FETCHING MATERIAL SETTINGS FROM SPECIFIC MATERIAL TYPES
########################################################################################################################


class MaterialBase:

    @staticmethod
    def get_parameter(simulation, name: str, parameter: str,
                      type_: Literal["str", "bool", "float", "int", "list"]) -> Any:
        value = simulation.getmaterial(name, parameter)

        if type_ == "bool":
            value = value != 0
        elif type_ == "float":
            value = np.round(value, decimals=DECIMALS)
        elif type_ == "int":
            value = int(value)
        if type_ == "list" and isinstance(value, np.ndarray):
            value = np.round(value, decimals=DECIMALS)

        return value


class AnalyticMaterial:
    class _SettingsDict(TypedDict):
        Define_by_index: bool
        Real: np.ndarray
        Imaginary: np.ndarray
        Length_units: MATERIAL_LENGTH_UNITS
        Frequency_units: MATERIAL_FREQUENCY_UNITS
        Number_of_samples: int
        x1: float
        x2: float
        x3: float
        x4: float
        x5: float
        x6: float
        x7: float
        x8: float
        x9: float
        x10: float

    _index_to_length_units = {
        1: "nm", 2: "microns", 3: "mm", 4: "cm", 5: "m"
    }
    _index_to_freq_units = {
        1: "inverse cm", 2: "THz", 3: "GHz", 4: "MHz", 5: "KHz", 6: "Hz"
    }

    @staticmethod
    def get_material(simulation, name) -> _SettingsDict:

        settings = AnalyticMaterial._SettingsDict(**{
            param: None for param in AnalyticMaterial._SettingsDict.__annotations__
        })

        settings["Define_by_index"] = MaterialBase.get_parameter(
            simulation, name, "Define by index", "bool")

        if settings["anisotropy"] == "Diagonal":
            real = MaterialBase.get_parameter(
                simulation, name, "Real", "str").split(";")
            settings["Real"] = np.array([float(real[0]), float(real[1]), float(real[2])])

            img = MaterialBase.get_parameter(
                simulation, name, "Imaginary", "list").split(";")
            settings["Imaginary"] = np.array([float(img[0]), float(img[1]), float(img[2])])

        else:
            settings["Real"] = np.array([
                MaterialBase.get_parameter(simulation, name, "Real", "float"),
                MaterialBase.get_parameter(simulation, name, "Real", "float"),
                MaterialBase.get_parameter(simulation, name, "Real", "float")
            ])
            settings["Imaginary"] = np.array([
                MaterialBase.get_parameter(simulation, name, "Imaginary", "float"),
                MaterialBase.get_parameter(simulation, name, "Imaginary", "float"),
                MaterialBase.get_parameter(simulation, name, "Imaginary", "float")
            ])

        settings["Length_units"] = AnalyticMaterial._index_to_length_units[
            MaterialBase.get_parameter(simulation, name, "Length units", "str")]
        settings["Frequency_units"] = AnalyticMaterial._index_to_freq_units[
            MaterialBase.get_parameter(simulation, name, "Frequency units", "str")]
        settings["Number_of_samples"] = MaterialBase.get_parameter(
            simulation, name, "Number of samples", "int")
        for i in range(10):
            settings[f"x{i + 1}"] = MaterialBase.get_parameter(
                simulation, name, f"x{i + 1}", "float")

        return settings


class Chi2:
    class _SettingsDict(TypedDict):
        base_material: str
        x_1: np.ndarray
        x_2: np.ndarray

    @staticmethod
    def get_material(simulation, name) -> _SettingsDict:

        settings = Chi2._SettingsDict(**{
            param: None for param in Chi2._SettingsDict.__annotations__
        })

        try:
            base_material = MaterialBase.get_parameter(
                simulation, name, "base material", "str")
            base_material_type = MaterialBase.get_parameter(
                simulation, base_material, "type", "str")

        except:
            base_material = None

        settings["base_material"] = base_material

        settings[f"x_1"] = MaterialBase.get_parameter(simulation, name, 'χ 1', "list").flatten()
        settings[f"x_2"] = MaterialBase.get_parameter(simulation, name, 'χ 2', "list").flatten()

        if MaterialBase.get_parameter(simulation, name, "anisotropy", "str") == "None":
            for key in ["x_1", "x_2"]:
                settings[key] = np.full_like(settings[key], settings[key][0])

        return settings


class Chi3:
    class _SettingsDict(TypedDict):
        base_material: str
        chi1: np.ndarray
        chi3: np.ndarray
        alpha: np.ndarray
        wraman: np.ndarray
        delta_raman: np.ndarray

    @staticmethod
    def get_material(simulation, name) -> _SettingsDict:

        settings = Chi3._SettingsDict(**{
            param: None for param in Chi3._SettingsDict.__annotations__
        })

        try:
            base_material = MaterialBase.get_parameter(
                simulation, name, "base material", "str")
            base_material_type = MaterialBase.get_parameter(
                simulation, base_material, "type", "str")
        except:
            base_material = None

        settings["base_material"] = base_material

        settings[f"chi1"] = MaterialBase.get_parameter(simulation, name, 'chi1', "list").flatten()
        settings[f"chi3"] = MaterialBase.get_parameter(simulation, name, 'chi3', "list").flatten()
        settings["alpha"] = MaterialBase.get_parameter(simulation, name, 'alpha', "list").flatten()
        settings["wraman"] = MaterialBase.get_parameter(simulation, name, 'wraman', "list").flatten()
        settings["delta_raman"] = MaterialBase.get_parameter(
            simulation, name, 'delta raman', "list").flatten()

        if MaterialBase.get_parameter(simulation, name, "anisotropy", "str") == "None":
            for key in ["chi1", "chi3", "alpha", "wraman", "delta_raman"]:
                settings[key] = np.full_like(settings[key], settings[key][0])

        return settings


class Chi3Chi2(Chi2):
    class _SettingsDict(Chi2._SettingsDict):
        x_3: np.ndarray

    @staticmethod
    def get_material(simulation, name) -> _SettingsDict:
        settings = Chi3Chi2._SettingsDict(**Chi2.get_material(simulation, name))
        settings["x_3"] = MaterialBase.get_parameter(simulation, name, 'χ 3', "list").flatten()
        if MaterialBase.get_parameter(simulation, name, "anisotropy", "str") == "None":
            for key in ["x_3"]:
                settings[key] = np.full_like(settings[key], settings[key][0])
        return settings


class Conductive2D:
    class _SettingsDict(TypedDict):
        layer_thickness: float
        conductivity: float

    @staticmethod
    def get_material(simulation, name) -> _SettingsDict:
        settings = Conductive2D._SettingsDict(**{
            param: None for param in Conductive2D.__annotations__
        })

        settings["layer_thickness"] = MaterialBase.get_parameter(
            simulation, name, 'layer thickness', "float")
        settings["conductivity"] = MaterialBase.get_parameter(
            simulation, name, 'conductivity', "float")

        return settings


class Conductive3D:
    class _SettingsDict(TypedDict):
        permittivity: np.ndarray
        conductivity: np.ndarray

    @staticmethod
    def get_material(simulation, name) -> _SettingsDict:
        settings = Conductive3D._SettingsDict(**{
            param: None for param in Conductive3D.__annotations__
        })

        permittivity = MaterialBase.get_parameter(simulation, name, "permittivity", "float")
        conductivity = MaterialBase.get_parameter(simulation, name, 'conductivity', "float")

        if MaterialBase.get_parameter(simulation, name, "anisotropy", "str") == "None":
            permittivity = np.array([permittivity, permittivity, permittivity])
            conductivity = np.array([conductivity, conductivity, conductivity])
        else:
            permittivity = permittivity.flatten()
            conductivity = conductivity.flatten()

        settings["permittivity"] = permittivity
        settings["conductivity"] = conductivity

        return settings


class CurrentDrivenGain(MaterialBase):
    class _SettingsDict(TypedDict):
        base_material: str
        lambda0: np.ndarray
        delta_lambda: np.ndarray
        gamma_radiative: np.ndarray
        gamma_non_radiative: np.ndarray
        i_volume: np.ndarray
        density_normalization: np.ndarray
        transparency_density: np.ndarray
        start_density: np.ndarray
        background_relative_permittivity: np.ndarray
        background_fluctuations: np.ndarray
        seed: np.ndarray
        change_current: np.ndarray
        i_volume_2: np.ndarray
        transition_time: np.ndarray
        self_field_correction: np.ndarray

    @staticmethod
    def get_material(simulation, name) -> _SettingsDict:
        settings = CurrentDrivenGain._SettingsDict(
            **{param: None for param in CurrentDrivenGain._SettingsDict.__annotations__})

        try:
            settings["base_material"] = MaterialBase.get_parameter(
                simulation, name, "base material", "str")
            base_material_type = MaterialBase.get_parameter(
                simulation, settings["base_material"], "type", "str"
            )
        except:
            settings["base_material"] = None

        map_ = {param: param for param in settings.keys()}
        map_.pop("base_material"), map_.pop("mesh_order"), map_.pop("anisotropy"), map_.pop("type")
        map_["gamma_non_radiative"] = "gamma non-radiative (1/s)"
        map_["i_volume"] = "I/volume"
        map_["i_volume_2"] = "I/volume 2"

        for key, item in map_.items():
            settings[key] = MaterialBase.get_parameter(
                simulation, name, item.replace("_", " "), "list"
            ).flatten()

        if MaterialBase.get_parameter(simulation, name, "anisotropy", "str") == "None":
            for key in map_.keys():
                settings[key] = np.full_like(settings[key], settings[key][0])

        return settings


class Debye:
    class _SettingsDict(TypedDict):
        permittivity: np.ndarray
        debye_permittivity: np.ndarray
        debye_collision: np.ndarray

    @staticmethod
    def get_material(simulation, name) -> _SettingsDict:

        settings = Debye._SettingsDict(**{param: None for param in Debye._SettingsDict.__annotations__})

        if MaterialBase.get_parameter(simulation, name, "anisotropy", "str") == "Diagonal":
            settings["permittivity"] = MaterialBase.get_parameter(
                simulation, name, "permittivity", "list"
            ).flatten()
            settings["debye_permittivity"] = MaterialBase.get_parameter(
                simulation, name, "debye permittivity", "list"
            ).flatten()
            settings["debye_collision"] = MaterialBase.get_parameter(
                simulation, name, "debye collision", "list"
            ).flatten()
        else:
            permittivity = MaterialBase.get_parameter(
                simulation, name, "permittivity", "float"
            )
            settings["permittivity"] = np.array([permittivity, permittivity, permittivity])

            debye_permittivity = MaterialBase.get_parameter(
                simulation, name, "debye permittivity", "float"
            )
            settings["debye_permittivity"] = np.array([
                debye_permittivity, debye_permittivity, debye_permittivity
            ])

            debye_collision = MaterialBase.get_parameter(
                simulation, name, "debye collision", "float"
            )
            settings["debye_collision"] = np.array([
                debye_collision, debye_collision, debye_collision
            ])

        return settings


class Dielectric:
    class _SettingsDict(TypedDict):
        refractive_index: np.ndarray

    @staticmethod
    def get_material(simulation, name) -> _SettingsDict:
        settings = Dielectric._SettingsDict(**{
            param: None for param in Dielectric._SettingsDict.__annotations__
        })

        if MaterialBase.get_parameter(simulation, name, "anisotropy", "str") == "Diagonal":
            settings["refractive_index"] = MaterialBase.get_parameter(
                simulation, name, "refractive index", "list"
            ).flatten()
        else:
            refractive_index = MaterialBase.get_parameter(
                simulation, name, "refractive index", "float"
            )
            settings["refractive_index"] = np.array([
                refractive_index, refractive_index, refractive_index
            ])

        return settings


class FourLevelTwoElectron:
    class _SettingsDict(TypedDict):
        base_material: str
        w_a: np.ndarray
        gamma_a: np.ndarray
        w_b: np.ndarray
        gamma_b: np.ndarray
        t30: np.ndarray
        t32: np.ndarray
        t21: np.ndarray
        t10: np.ndarray
        N_density: np.ndarray
        set_initial_populations: np.ndarray
        N0: np.ndarray
        N1: np.ndarray
        N2: np.ndarray
        N3: np.ndarray
        do_not_enforce_electron_conservation: np.ndarray

    @staticmethod
    def get_material(simulation, name) -> _SettingsDict:

        settings = FourLevelTwoElectron._SettingsDict(**{
            param: None for param in FourLevelTwoElectron._SettingsDict.__annotations__
        })

        try:
            settings["base_material"] = MaterialBase.get_parameter(
                simulation, name, "base material", "str")
            base_material_type = MaterialBase.get_parameter(
                simulation, settings["base_material"], "type", "str"
            )
        except:
            settings["base_material"] = None

        for key in FourLevelTwoElectron._SettingsDict.__annotations__:
            if key == "base_material":
                continue
            if key in [f"N{i}" for i in range(4)]:
                key_ = key + "(0)"
            else:
                key_ = key.replace("_", " ")
            settings[key] = MaterialBase.get_parameter(
                simulation, name, key_, "list"
            ).flatten()
            if MaterialBase.get_parameter(simulation, name, "anisotropy", "str") == "None":
                settings[key] = np.full_like(settings[key], settings[key][0])

        return settings


class Graphene:
    class _SettingsDict(TypedDict):
        scattering_rate: float
        chemical_potential: float
        temperature: float
        conductivity_scaling: float
        frequency_samples: int
        quadrature_tolerance: float
        max_quadrature_iterations: int

    @staticmethod
    def get_material(simulation, name) -> _SettingsDict:
        settings = Graphene._SettingsDict(**{
            param: None for param in Graphene._SettingsDict.__annotations__
        })

        settings["scattering_rate"] = MaterialBase.get_parameter(
            simulation, name, "scattering rate (eV)", "float"
        )
        settings["chemical_potential"] = MaterialBase.get_parameter(
            simulation, name, "chemical potential (eV)", "float"
        )
        settings["temperature"] = MaterialBase.get_parameter(
            simulation, name, "temperature (K)", "float"
        )
        settings["conductivity_scaling"] = MaterialBase.get_parameter(
            simulation, name, "conductivity scaling", "float"
        )
        settings["frequency_samples"] = MaterialBase.get_parameter(
            simulation, name, "frequency samples", "int"
        )
        settings["quadrature_tolerance"] = MaterialBase.get_parameter(
            simulation, name, "quadrature tolerance", "float"
        )
        settings["max_quadrature_iterations"] = MaterialBase.get_parameter(
            simulation, name, "max quadrature iterations", "int"
        )
        return settings


class KerrNonlinear:
    class _SettingsDict(TypedDict):
        permittivity: np.ndarray
        chi3: float

    @staticmethod
    def get_material(simulation, name) -> _SettingsDict:
        settings = KerrNonlinear._SettingsDict(**{
            param: None for param in KerrNonlinear._SettingsDict.__annotations__
        })
        if MaterialBase.get_parameter(simulation, name, "anisotropy", "str") == "Diagonal":
            settings["permittivity"] = MaterialBase.get_parameter(
                simulation, name, "permittivity", "list"
            ).flatten()
        else:
            permittivity = MaterialBase.get_parameter(
                simulation, name, "permittivity", "float"
            )
            settings["permittivity"] = np.array([
                permittivity, permittivity, permittivity
            ])

        settings["chi3"] = MaterialBase.get_parameter(
            simulation, name, "chi(3)", "float"
        )

        return settings


class Lorentz:
    class _SettingsDict(TypedDict):
        permittivity: np.ndarray
        lorentz_permittivity: np.ndarray
        lorentz_resonance: np.ndarray
        lorentz_linewidth: np.ndarray

    @staticmethod
    def get_material(simulation, name) -> _SettingsDict:
        settings = Lorentz._SettingsDict(**{
            param: None for param in Lorentz._SettingsDict.__annotations__
        })

        anisotropy = MaterialBase.get_parameter(simulation, name, "anisotropy", "str")

        permittivity = MaterialBase.get_parameter(simulation, name, "permittivity", "float")
        lorentz_permittivity = MaterialBase.get_parameter(simulation, name, "lorentz permittivity",
                                                          "float")
        lorentz_resonance = MaterialBase.get_parameter(simulation, name, "lorentz resonance", "float")
        lorentz_linewidth = MaterialBase.get_parameter(simulation, name, "lorentz linewidth", "float")

        if anisotropy == "None":
            permittivity = np.array([permittivity, permittivity, permittivity])
            lorentz_permittivity = np.array([lorentz_permittivity, lorentz_permittivity, lorentz_permittivity])
            lorentz_resonance = np.array([lorentz_resonance, lorentz_resonance, lorentz_resonance])
            lorentz_linewidth = np.array([lorentz_linewidth, lorentz_linewidth, lorentz_linewidth])

        settings["permittivity"] = permittivity.flatten()
        settings["lorentz_permittivity"] = lorentz_permittivity.flatten()
        settings["lorentz_resonance"] = lorentz_resonance.flatten()
        settings["lorentz_linewidth"] = lorentz_linewidth.flatten()

        return settings


class MagneticElectricLorentz:
    class _SettingsDict(TypedDict):
        base_material: str
        x0_electric: np.ndarray
        de_electric: np.ndarray
        w0_electric: np.ndarray
        d_electric: np.ndarray
        x0_magnetic: np.ndarray
        dmu_magnetic: np.ndarray
        w0_magnetic: np.ndarray
        d_magnetic: np.ndarray
        exclude_electric: np.ndarray
        exclude_magnetic: np.ndarray

    @staticmethod
    def get_material(simulation, name) -> _SettingsDict:

        settings = MagneticElectricLorentz._SettingsDict(**{
            param: None for param in MagneticElectricLorentz._SettingsDict.__annotations__
        })

        anisotropy = MaterialBase.get_parameter(simulation, name, "anisotropy", "str")

        try:
            base_material = MaterialBase.get_parameter(simulation, name, "base material", "str")
        except:
            base_material = None

        settings["base_material"] = base_material

        settings["x0_electric"] = MaterialBase.get_parameter(
            simulation, name, 'χ0 electric', "list").flatten()
        settings["de_electric"] = MaterialBase.get_parameter(
            simulation, name, 'Δε electric', "list").flatten()
        settings["w0_electric"] = MaterialBase.get_parameter(
            simulation, name, 'ω0 electric', "list").flatten()
        settings["d_electric"] = MaterialBase.get_parameter(
            simulation, name, 'δ electric', "list").flatten()
        settings["x0_magnetic"] = MaterialBase.get_parameter(
            simulation, name, 'χ0 magnetic', "list").flatten()
        settings["dmu_magnetic"] = MaterialBase.get_parameter(
            simulation, name, 'Δμ magnetic', "list").flatten()
        settings["w0_magnetic"] = MaterialBase.get_parameter(
            simulation, name, 'ω0 magnetic', "list").flatten()
        settings["d_magnetic"] = MaterialBase.get_parameter(
            simulation, name, 'δ magnetic', "list").flatten()
        settings["exclude_electric"] = MaterialBase.get_parameter(
            simulation, name, 'exclude electric', "list").flatten()
        settings["exclude_magnetic"] = MaterialBase.get_parameter(
            simulation, name, 'exclude magnetic', "list").flatten()

        if anisotropy != "Diagonal":
            for key in settings.keys():
                if key != "base_material":
                    settings[key] = np.full_like(settings[key], settings[key][0])

        return settings


class Paramagnetic:
    class _SettingsDict(TypedDict):
        base_material: str
        permittivity: np.ndarray
        permeability: np.ndarray

    @staticmethod
    def get_material(simulation, name) -> _SettingsDict:
        settings = Paramagnetic._SettingsDict(**{
            param: None for param in Paramagnetic._SettingsDict.__annotations__
        })

        try:
            base_material = MaterialBase.get_parameter(simulation, name, "base material", "str")
        except:
            base_material = None

        settings["base_material"] = base_material

        settings["permittivity"] = MaterialBase.get_parameter(
            simulation, name, "Permittivity", "list").flatten()
        settings["permeability"] = MaterialBase.get_parameter(
            simulation, name, "Permeability", "list").flatten()

        anisotropy = MaterialBase.get_parameter(simulation, name, "anisotropy", "str")
        if anisotropy != "Diagonal":
            for key in settings.keys():
                if key != "base_material":
                    settings[key] = np.full_like(settings[key], settings[key][0])

        return settings


class PEC:

    @staticmethod
    def get_material(self, simulation, name) -> None:
        return None


class Plasma:
    class _SettingsDict(TypedDict):
        permittivity: np.ndarray
        plasma_resonance: np.ndarray
        plasma_collision: np.ndarray

    @staticmethod
    def get_material(simulation, name) -> _SettingsDict:

        settings = Plasma._SettingsDict(**{
            param: None for param in Plasma._SettingsDict.__annotations__
        })

        permittivity = MaterialBase.get_parameter(
            simulation, name, "Permittivity", "list")
        plasma_resonance = MaterialBase.get_parameter(
            simulation, name, "Plasma resonance", "list")
        plasma_collision = MaterialBase.get_parameter(
            simulation, name, "Plasma collision", "list")

        anisotropy = MaterialBase.get_parameter(simulation, name, "anisotropy", "str")
        if anisotropy != "Diagonal":
            permittivity = np.array([permittivity, permittivity, permittivity])
            plasma_resonance = np.array([plasma_resonance, plasma_resonance, plasma_resonance])
            plasma_collision = np.array([plasma_collision, plasma_collision, plasma_collision])

        settings["permittivity"] = permittivity.flatten()
        settings["plasma_resonance"] = plasma_resonance.flatten()
        settings["plasma_collision"] = plasma_collision.flatten()

        return settings


class Sampled2Ddata:

    class _SettingsDict(TypedDict):
        frequencies: np.ndarray
        wavelengths: np.ndarray
        conductivity_real: np.ndarray
        conductivity_imaginary: np.ndarray

    @staticmethod
    def get_material(simulation, name) -> _SettingsDict:

        settings = Sampled2Ddata._SettingsDict(**{
            param: None for param in Sampled2Ddata._SettingsDict.__annotations__
        })
        sampled_data = simulation.getmaterial(name, "sampled data")

        settings["frequencies"] = np.real(sampled_data[:, 0])
        settings["wavelengths"] = frequency_to_wavelength(settings["frequencies"])
        settings["conductivity_real"] = np.real(sampled_data[:, 1:])
        settings["conductivity_imaginary"] = np.imag(sampled_data[:, 1:])

        return settings


class Sampled3Ddata:

    class _SettingsDict(TypedDict):
        frequencies: np.ndarray
        wavelengths: np.ndarray
        permittivity_real: np.ndarray
        permittivity_imaginary: np.ndarray

    @staticmethod
    def get_material(simulation, name) -> _SettingsDict:
        settings = Sampled3Ddata._SettingsDict(**{
            param: None for param in Sampled3Ddata._SettingsDict.__annotations__
        })

        sampled_data = simulation.getmaterial(name, "sampled data")

        settings["frequencies"] = np.real(sampled_data[:, 0])
        settings["wavelengths"] = frequency_to_wavelength(settings["frequencies"])
        settings["permittivity_real"] = np.real(sampled_data[:, 1:])
        settings["permittivity_imaginary"] = np.imag(sampled_data[:, 1:])
        return settings


class Sellmeier:

    class _SettingsDict(TypedDict):
        a0: np.ndarray
        b1: np.ndarray
        c1: np.ndarray
        b2: np.ndarray
        c2: np.ndarray
        b3: np.ndarray
        c3: np.ndarray

    @staticmethod
    def get_material(simulation, name) -> _SettingsDict:
        settings = Sellmeier._SettingsDict(**{
            param: None for param in Sellmeier._SettingsDict.__annotations__
        })
        a0 = MaterialBase.get_parameter(simulation, name, "A0", "float")
        b1 = MaterialBase.get_parameter(simulation, name, "B1", "float")
        c1 = MaterialBase.get_parameter(simulation, name, "C1", "float")
        b2 = MaterialBase.get_parameter(simulation, name, "B2", "float")
        c2 = MaterialBase.get_parameter(simulation, name, "C2", "float")
        b3 = MaterialBase.get_parameter(simulation, name, "B3", "float")
        c3 = MaterialBase.get_parameter(simulation, name, "C3", "float")

        anisotropy = MaterialBase.get_parameter(simulation, name, "anisotropy", "str")
        # Handle anisotropy if it is set to "None"
        if anisotropy == "None":
            a0 = np.array([a0, a0, a0])
            b1 = np.array([b1, b1, b1])
            c1 = np.array([c1, c1, c1])
            b2 = np.array([b2, b2, b2])
            c2 = np.array([c2, c2, c2])
            b3 = np.array([b3, b3, b3])
            c3 = np.array([c3, c3, c3])

        # Assign parameters to settings
        settings["a0"] = a0
        settings["b1"] = b1
        settings["c1"] = c1
        settings["b2"] = b2
        settings["c2"] = c2
        settings["b3"] = b3
        settings["c3"] = c3

        return settings


class IndexPerturbation:

    class _Drude(TypedDict):
        electron_effective_mass: float
        hole_effective_mass: float
        electron_mobility: float
        hole_mobility: float

    class _SorefAndBennet(TypedDict):
        coefficients: Literal["Nedeljkovic, Soref & Mashanovich, 2011", "user input"]
        soref_and_bennett_table: np.ndarray

    class _Custom(TypedDict):
        n_sensitivity_table: np.ndarray
        p_sensitivity_table: np.ndarray

    class _NPDensity(_Drude, _SorefAndBennet, _Custom):
        density_model: Literal["Drude", "Soref and Bennett", "Custom"]
        test_value_n: float
        test_value_p: float

    class _Temperature(TypedDict):
        Tref: float
        dn_dt: float
        dk_dt: float
        test_value_T: float
        temperature_sensitivity_table: np.ndarray

    class _SettingsDict(_NPDensity, _Temperature):
        base_material: str

    @staticmethod
    def get_material(simulation, name) -> _SettingsDict:

        settings = IndexPerturbation._SettingsDict(**{
            param: None for param in IndexPerturbation._SettingsDict.__annotations__
        })

        try:
            base_material = MaterialBase.get_parameter(simulation, name, "base material", "str")
        except:
            base_material = None

        settings["base_material"] = base_material

        include_np_density = MaterialBase.get_parameter(simulation, name, "include np density", "bool")
        if include_np_density:

            settings["test_value_n"] = MaterialBase.get_parameter(
                    simulation, name, "test value n", "float")
            settings["test_value_p"] = MaterialBase.get_parameter(
                    simulation, name, "test value p", "float")

            density_model = MaterialBase.get_parameter(simulation, name, "np density model", "str")
            print(density_model)
            settings["density_model"] = density_model
            if density_model == "Drude":
                settings["electron_effective_mass"] = MaterialBase.get_parameter(
                    simulation, name, "electron effective mass", "float")
                settings["hole_effective_mass"] = MaterialBase.get_parameter(
                    simulation, name, "hole effective mass", "float")
                settings["electron_mobility"] = MaterialBase.get_parameter(
                    simulation, name, "electron mobility", "float")
                settings["hole_mobility"] = MaterialBase.get_parameter(
                    simulation, name, "hole mobility", "float")
            elif density_model == "Soref and Bennett":
                settings["coefficients"] = MaterialBase.get_parameter(
                    simulation, name, "coefficients", "str")
                settings["soref_and_bennett_table"] = simulation.getmaterial(name, "soref and bennett table")
            elif density_model == "Custom":
                settings["n_sensitivity_table"] = simulation.getmaterial(name, "n sensitivity table")
                settings["p_sensitivity_table"] = simulation.getmaterial(name, "p sensitivity table")

        include_temperature_effects = MaterialBase.get_parameter(
            simulation, name, "include temperature effects", "bool")
        if include_temperature_effects:

            settings["test_value_T"] = MaterialBase.get_parameter(
                simulation, name, "test value T", "float")

            linear_sensitivity = MaterialBase.get_parameter(
                simulation, name, "linear sensitivity", "bool")
            if linear_sensitivity:
                settings["Tref"] = MaterialBase.get_parameter(
                    simulation, name, "Tref", "float")
                settings["dn_dt"] = MaterialBase.get_parameter(
                    simulation, name, "dn/dt", "float")
                settings["dk_dt"] = MaterialBase.get_parameter(
                    simulation, name, "dk/dt", "float")
            else:
                settings["temperature_sensitivity_table"] = simulation.getmaterial(name,
                                                                                   "temperature sensitivity table")

        return settings


MATERIAL_DICTS = Union[
    AnalyticMaterial._SettingsDict, Chi2._SettingsDict, Chi3._SettingsDict, Chi3Chi2._SettingsDict,
    Conductive2D._SettingsDict, Conductive3D._SettingsDict, CurrentDrivenGain._SettingsDict,
    Debye._SettingsDict, Dielectric._SettingsDict, FourLevelTwoElectron._SettingsDict,
    Graphene._SettingsDict, KerrNonlinear._SettingsDict, Lorentz._SettingsDict,
    MagneticElectricLorentz._SettingsDict, Paramagnetic._SettingsDict, None, Plasma._SettingsDict,
    Sampled2Ddata._SettingsDict, Sampled3Ddata._SettingsDict, Sellmeier._SettingsDict,
    IndexPerturbation._SettingsDict
]


########################################################################################################################
#                                         MATERIAL DATABASE SETTING CLASS
########################################################################################################################


class MaterialDatabase(SettingTab):

    class _AdvancedOptions(TypedDict):
        layer_thickness: float
        tolerance: float
        max_coefficients: int
        make_fit_passive: bool
        improve_numerical_stability: bool
        imaginary_weight: float
        specify_fit_range: bool
        wavelength_min: float
        wavelength_max: float
        frequency_min: float
        frequency_max: float

    class _SettingsDict(SettingTab._SettingsDict):
        name: str
        mesh_order: int
        anisotropy: ANISOTROPY
        type: MATERIAL_TYPE
        advanced_options: MaterialDatabase._AdvancedOptions
        parameters: MATERIAL_DICTS

    _type_to_parameters_map = {
        "Analytic material": AnalyticMaterial.get_material,
        "Chi2": Chi2.get_material,
        "Chi3 Raman Kerr": Chi3.get_material,
        "Chi3/Chi2": Chi3Chi2.get_material,
        "Conductive 2D": Conductive2D.get_material,
        "Conductive 3D": Conductive3D.get_material,
        "Current Driven Gain (version 1.0.0)": CurrentDrivenGain.get_material,
        "Debye": Debye.get_material,
        "Dielectric": Dielectric.get_material,
        "Four-Level Two-Electron (Version 1.0.0)": FourLevelTwoElectron.get_material,
        "Graphene": Graphene.get_material,
        "Kerr nonlinear": KerrNonlinear.get_material,
        "Lorentz": Lorentz.get_material,
        "Magnetic Electric Lorentz (Version 1.0.0)": MagneticElectricLorentz.get_material,
        "Paramagnetic": Paramagnetic.get_material,
        "PEC": PEC.get_material,
        "Plasma": Plasma.get_material,
        "Sampled 2D data": Sampled2Ddata.get_material,
        "Sampled 3D data": Sampled3Ddata.get_material,
        "Sellmeier": Sellmeier.get_material,
        "Index perturbation": IndexPerturbation.get_material
    }

    def _get_parameter(
            self, parameter_name: str, type_: PARAMETER_TYPES, material_name: str = None, getter_function=None) -> Any:

        return super()._get_parameter(parameter_name=parameter_name, type_=type_, object_name=material_name,
                                      getter_function=self._simulation.getmaterial)

    def _set_parameter(
            self, parameter_name: str, value: Any, type_: PARAMETER_TYPES, material_name: str = None,
            getter_function=None, setter_function=None) -> Any:

        return super()._set_parameter(parameter_name=parameter_name, value=value, type_=type_,
                                      object_name=material_name,
                                      getter_function=self._simulation.getmaterial,
                                      setter_function=self._simulation.setmaterial)

    def get_material_parameters(self, material_name: str) -> _SettingsDict:

        settings = self.__class__._SettingsDict(**self._init_empty_settings_dict())

        settings["name"] = material_name

        settings["mesh_order"] = self._get_parameter("mesh order", "int",
                                                     material_name=material_name)
        settings["anisotropy"] = self._get_parameter("anisotropy", "str",
                                                     material_name=material_name)
        settings["type"] = self._get_parameter("type", "str",
                                               material_name=material_name)
        settings["advanced_options"] = self._get_advanced_options(material_name, settings["type"])

        settings["parameters"] = self.__class__._type_to_parameters_map[settings["type"]](self._simulation,
                                                                                          material_name)

        if "base_material" in settings["parameters"]:
            base_material: str = settings["parameters"]["base_material"]
            if base_material is not None:
                base_material_type = self._get_parameter("type", "str",
                                                         material_name=base_material)
                base_material_parameters = self.get_material_parameters(base_material)
                settings["parameters"]["base_material"] = base_material_parameters

        return settings

    def _get_advanced_options(self, material_name: str, material_type: str) -> _AdvancedOptions | None:

        if material_type in ["Analytic material", "Graphene", "Sampled 2D data", "Sampled 3D data"]:
            pass
        else:
            return None

        settings = self.__class__._AdvancedOptions(**{
            param: None for param in self.__class__._AdvancedOptions.__annotations__
        })

        if (material_type == "Sampled 2D data"
                and self._get_parameter("layer thickness enabled",
                                        "bool", material_name=material_name)):
            settings["layer_thickness"] = self._get_parameter("layer thickness", "float",
                                                              material_name=material_name)

        settings["tolerance"] = self._get_parameter("tolerance", "float",
                                                    material_name=material_name)
        settings["max_coefficients"] = self._get_parameter("max coefficients", "int",
                                                           material_name=material_name)
        settings["make_fit_passive"] = self._get_parameter("make fit passive", "bool",
                                                           material_name=material_name)
        settings["improve_numerical_stability"] = self._get_parameter("improve numerical stability",
                                                                      "bool", material_name=material_name)
        settings["imaginary_weight"] = self._get_parameter("imaginary weight", "float",
                                                           material_name=material_name)
        settings["specify_fit_range"] = self._get_parameter("specify fit range", "bool",
                                                            material_name=material_name)
        settings["wavelength_min"] = self._get_parameter("wavelength min", "float",
                                                         material_name=material_name)
        settings["wavelength_max"] = self._get_parameter("wavelength max", "float",
                                                         material_name=material_name)
        settings["frequency_min"] = self._get_parameter("frequency min", "float",
                                                        material_name=material_name)
        settings["frequency_max"] = self._get_parameter("frequency max", "float",
                                                        material_name=material_name)

        return settings

    def _get_specific_material_parameters(self, material_name: str, material_type: str) -> MATERIAL_DICTS:

        return self.__class__._type_to_parameters_map[material_type](self._simulation, material_name)
