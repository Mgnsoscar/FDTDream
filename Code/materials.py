from __future__ import annotations

# Standard-library imports
from typing import Optional, get_type_hints
from abc import ABC
from dataclasses import dataclass

# Third-party library imports
import numpy as np

# Local library imports
from Code.Resources.local_resources import frequency_to_wavelength
from Code.Resources.literals import MATERIAL_LENGTH_UNITS, MATERIAL_FREQUENCY_UNITS
from base_classes import TMaterial
from base_classes import Settings
from base_classes import MaterialSettingsBase, MaterialBase, MaterialDatabaseBase


########################################################################################################################
#                        CLASS FOR FETCHING MATERIAL SETTINGS FROM SPECIFIC MATERIAL TYPES
########################################################################################################################


class MaterialSettings(MaterialSettingsBase):
    __slots__ = MaterialSettingsBase.__slots__

    def _get_active_parameters(self) -> TMaterial.Settings:

        material_database = self._simulation.__getattribute__("_material_database")
        material_name = self._get_parameter("material", "str")
        settings = material_database.get_material_parameters(material_name)

        settings.name = material_name

        override_mesh_order = self._get_parameter("override mesh order from material database", "bool")
        if override_mesh_order and settings.specific_parameters.type != "<Object defined dielectric>":
            new_mesh_order = self._get_parameter("mesh order", "int")
            if new_mesh_order != settings.common_parameters.mesh_order:
                settings.common_parameters.mesh_order = new_mesh_order
                settings.common_parameters.hash = None
                settings.common_parametersfill_hash_fields()

        if settings.specific_parameters.type == "<Object defined dielectric>":
            settings.common_parameters.mesh_order = self._get_parameter("mesh order", "int")
            settings.specific_parameters.index = self._get_parameter("index", "str")
            if any(char.isalpha() for char in settings.specific_parameters.index):
                settings.specific_parameters.index_units = self._get_parameter("index units", "str")
                settings.common_parameters.anisotropy = "Diagonal"
            elif ";" in settings.specific_parameters.index:
                settings.common_parameters.anisotropy = "Diagonal"
            else:
                settings.common_parameters.anisotropy = "None"

        settings.fill_hash_fields()
        return settings


########################################################################################################################
#                        MATERIAL CLASSES (USED FOR FETCHING PARAMETERS FROM MATERIAL DATABASE)
########################################################################################################################


class Material(MaterialBase, ABC):
    __slots__ = MaterialBase.__slots__

    def get_base_material(self) -> Optional[TMaterial.Settings]:
        try:
            base_material = self.get_parameter("base material", "str")
            base_material_type = Material(base_material, self.material_database).get_parameter("type", "str")
            base_material_class = getattr(MaterialDatabase, "_type_to_parameters_map")[base_material_type]
            base_material = base_material_class(base_material, self.material_database)
        except:
            base_material = None

        return base_material


class AnalyticMaterial(Material):
    @dataclass
    class SpecificParameters(Material.SpecificParameters):
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

    @dataclass
    class Settings(Material.Settings):
        specific_parameters: AnalyticMaterial.SpecificParameters
        advanced_parameters: None

    __slots__ = Material.__slots__

    def get_material_parameters(self) -> Settings:

        index_to_length_units = {1: "nm", 2: "microns", 3: "mm", 4: "cm", 5: "m"}
        index_to_freq_units = {1: "inverse cm", 2: "THz", 3: "GHz", 4: "MHz", 5: "KHz", 6: "Hz"}

        settings = self.Settings.initialize_empty()
        settings.common_parameters = self.get_common_parameters()
        settings.advanced_parameters = self.get_advanced_parameters()
        parameters = settings.specific_parameters

        parameters.Define_by_index = self.get_parameter("Define by index", "bool")

        if settings.common_parameters.anisotropy == "Diagonal":
            real = self.get_parameter("Real", "str").split(";")
            parameters.Real = np.array([float(real[0]), float(real[1]), float(real[2])])

            img = self.get_parameter("Imaginary", "list").split(";")
            parameters.Imaginary = np.array([float(img[0]), float(img[1]), float(img[2])])

        else:
            parameters.Real = np.array([self.get_parameter("Real", "float"),
                                        self.get_parameter("Real", "float"),
                                        self.get_parameter("Real", "float")])
            parameters.Imaginary = np.array([self.get_parameter("Imaginary", "float"),
                                             self.get_parameter("Imaginary", "float"),
                                             self.get_parameter("Imaginary", "float")])

        parameters.Length_units = index_to_length_units[self.get_parameter("Length units", "str")]
        parameters.Frequency_units = index_to_freq_units[self.get_parameter("Frequency units", "str")]
        parameters.Number_of_samples = self.get_parameter("Number of samples", "int")

        for i in range(10):
            parameters.__setattr__(f"x{i + 1}", self.get_parameter(f"x{i + 1}", "float"))

        parameters.type = self.get_parameter("type", "str")
        settings.fill_hash_fields()
        return settings


class Chi2(Material):
    @dataclass
    class SpecificParameters(Material.SpecificParameters):
        base_material: Optional[TMaterial.SettingsDict]
        x_1: np.ndarray
        x_2: np.ndarray

    class Settings(Material.Settings):
        advanced_parameters: None
        specific_parameters: Chi2.SpecificParameters

    __slots__ = Material.__slots__

    def get_material_parameters(self) -> Settings:

        settings = self.Settings.initialize_empty()
        settings.common_parameters = self.get_common_parameters()
        parameters = settings.specific_parameters
        parameters.base_material = self.get_base_material()

        parameters.x_1 = self.get_parameter('χ 1', "list").flatten()
        parameters.x_2 = self.get_parameter('χ 2', "list").flatten()

        if settings.common_parameters.anisotropy == "None":
            for key in ["x_1", "x_2"]:
                attr = parameters.__getattribute__(key)
                parameters.__setattr__(key, np.full_like(attr, attr[0]))

        parameters.type = self.get_parameter("type", "str")
        settings.fill_hash_fields()
        return settings


class Chi3(Material):
    @dataclass
    class SpecificParameters(Material.SpecificParameters):
        base_material: Optional[TMaterial.Settings]
        chi1: np.ndarray
        chi3: np.ndarray
        alpha: np.ndarray
        wraman: np.ndarray
        delta_raman: np.ndarray

    @dataclass
    class Settings(Material.Settings):
        advanced_parameters: None
        specific_parameters: Chi3.SpecificParameters

    __slots__ = Material.__slots__

    def get_material_parameters(self) -> Settings:

        settings = self.Settings.initialize_empty()
        settings.common_parameters = self.get_common_parameters()
        parameters = settings.specific_parameters
        parameters.base_material = self.get_base_material()

        parameters.chi1 = self.get_parameter('chi1', "list").flatten()
        parameters.chi3 = self.get_parameter('chi3', "list").flatten()
        parameters.alpha = self.get_parameter('alpha', "list").flatten()
        parameters.wraman = self.get_parameter('wraman', "list").flatten()
        parameters.delta_raman = self.get_parameter('delta raman', "list").flatten()

        if settings.common_parameters.anisotropy == "None":
            for key in ["chi1", "chi3", "alpha", "wraman", "delta_raman"]:
                attr = parameters.__getattribute__(key)
                parameters.__setattr__(key, np.full_like(attr, attr[key][0]))

        parameters.type = self.get_parameter("type", "str")
        settings.fill_hash_fields()
        return settings


class Chi3Chi2(Material):
    @dataclass
    class SpecificParameters(Material.SpecificParameters):
        base_material: Optional[TMaterial.SettingsDict]
        x_1: np.ndarray
        x_2: np.ndarray
        x_3: np.ndarray

    @dataclass
    class Settings(Material.Settings):
        advanced_parameters: None
        specific_parameters: Chi3Chi2.SpecificParameters

    __slots__ = Material.__slots__

    def get_material_parameters(self) -> Settings:

        settings = self.Settings.initialize_empty()
        settings.common_parameters = self.get_common_parameters()
        settings.specific_parameters.base_material = self.get_base_material()
        settings.specific_parameters.type = self.get_parameter("type", "str")

        for param in ["x_1", "x_2", "x_3"]:
            settings.specific_parameters.__setattr__(param, self.get_parameter(param.replace("_", " "), "list"))

        if settings.common_parameters.anisotropy == "None":
            for param in ["x_1", "x_2"]:
                attr = settings.specific_parameters.__getattribute__(param)
                settings.specific_parameters.__setattr__(param, np.full_like(attr, attr[0]))

        settings.fill_hash_fields()
        return settings


class Conductive2D(Material):
    @dataclass
    class SpecificParameters(Material.SpecificParameters):
        layer_thickness: float
        conductivity: float

    @dataclass
    class Settings(Material.Settings):
        advanced_parameters: None
        specific_parameters: Conductive2D.SpecificParameters

    __slots__ = Material.__slots__

    def get_material_parameters(self) -> Settings:
        settings = self.Settings.initialize_empty()
        settings.common_parameters = self.get_common_parameters()
        parameters = settings.specific_parameters
        parameters.type = self.get_parameter("type", "str")

        parameters.layer_thickness = self.get_parameter('layer thickness', "float")
        parameters.conductivity = self.get_parameter('conductivity', "float")
        settings.fill_hash_fields()
        return settings


class Conductive3D(Material):
    @dataclass
    class SpecificParameters(Material.SpecificParameters):
        permittivity: np.ndarray
        conductivity: np.ndarray

    @dataclass
    class Settings(Material.Settings):
        advanced_parameters: None
        specific_parameters: Conductive3D.SpecificParameters

    __slots__ = Material.__slots__

    def get_material_parameters(self) -> Settings:

        settings = self.Settings.initialize_empty()
        settings.common_parameters = self.get_common_parameters()
        settings.specific_parameters.type = self.get_parameter("type", "str")

        permittivity = self.get_parameter("permittivity", "float")
        conductivity = self.get_parameter('conductivity', "float")

        if settings.common_parameters.anisotropy == "None":
            permittivity = np.array([permittivity, permittivity, permittivity])
            conductivity = np.array([conductivity, conductivity, conductivity])
        else:
            permittivity = permittivity.flatten()
            conductivity = conductivity.flatten()

        settings.specific_parameters.permittivity = permittivity
        settings.specific_parameters.conductivity = conductivity
        settings.fill_hash_fields()
        return settings


class CurrentDrivenGain(Material):
    @dataclass
    class SpecificParameters(Material.SpecificParameters):
        base_material: Optional[TMaterial.SettingsDict]
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

    @dataclass
    class Settings(Material.Settings):
        advanced_parameters: None
        specific_parameters: CurrentDrivenGain.SpecificParameters

    __slots__ = Material.__slots__

    def get_material_parameters(self) -> Settings:

        settings = self.Settings.initialize_empty()
        settings.common_parameters = self.get_common_parameters()
        parameters = settings.specific_parameters
        parameters.type = self.get_parameter("type", "str")
        parameters.base_material = self.get_base_material()

        map_ = {key: key for key in get_type_hints(self.SpecificParameters).keys()}
        map_.pop("base_material")
        map_.pop("hash")
        map_.pop("type")
        map_["gamma_non_radiative"] = "gamma non-radiative (1/s)"
        map_["i_volume"] = "I/volume"
        map_["i_volume_2"] = "I/volume 2"

        for key, item in map_.items():
            parameters.__setattr__(key, self.get_parameter(item.replace("_", " "), "list").flatten())

        if settings.common_parameters.anisotropy == "None":
            for key in map_.keys():
                attr = parameters.__getattribute__(key)
                parameters.__setattr__(key, np.full_like(attr, attr[0]))

        settings.fill_hash_fields()
        return settings


class Debye(Material):
    @dataclass
    class SpecificParameters(Material.SpecificParameters):
        permittivity: np.ndarray
        debye_permittivity: np.ndarray
        debye_collision: np.ndarray

    @dataclass
    class Settings(Material.Settings):
        advanced_parameters: None
        specific_parameters: Debye.SpecificParameters

    __slots__ = Material.__slots__

    def get_material_parameters(self) -> Settings:

        settings = self.Settings.initialize_empty()
        settings.common_parameters = self.get_common_parameters()
        parameters = settings.specific_parameters
        parameters.type = self.get_parameter("type", "str")

        if settings.common_parameters.anisotropy == "Diagonal":
            parameters.permittivity = self.get_parameter("permittivity", "list").flatten()
            parameters.debye_permittivity = self.get_parameter("debye permittivity", "list").flatten()
            parameters.debye_collision = self.get_parameter("debye collision", "list").flatten()
        else:
            permittivity = self.get_parameter("permittivity", "float")
            parameters.permittivity = np.array([permittivity, permittivity, permittivity])

            debye_permittivity = self.get_parameter("debye permittivity", "float")
            parameters.debye_collision = np.array([debye_permittivity, debye_permittivity, debye_permittivity])

            debye_collision = self.get_parameter("debye collision", "float")
            parameters.debye_collision = np.array([debye_collision, debye_collision, debye_collision])

        settings.fill_hash_fields()
        return settings


class Dielectric(Material):
    @dataclass
    class SpecificParameters(Material.SpecificParameters):
        refractive_index: np.ndarray

    @dataclass
    class Settings(Material.Settings):
        advanced_parameters: None
        specific_parameters: Dielectric.SpecificParameters

    __slots__ = Material.__slots__

    def get_material_parameters(self) -> Settings:

        settings = self.Settings.initialize_empty()
        settings.common_parameters = self.get_common_parameters()
        parameters = settings.specific_parameters
        parameters.type = self.get_parameter("type", "str")

        if settings.common_parameters.anisotropy == "Diagonal":
            parameters.refractive_index = self.get_parameter("refractive index", "list").flatten()
        else:
            refractive_index = self.get_parameter("refractive index", "float")
            parameters.refractive_index = np.array([refractive_index, refractive_index, refractive_index])

        settings.fill_hash_fields()
        return settings


class FourLevelTwoElectron(Material):
    @dataclass
    class SpecificParameters(Material.SpecificParameters):
        base_material: Optional[TMaterial.SettingsDict]
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

    @dataclass
    class Settings(Material.Settings):
        advanced_parameters: None
        specific_parameters: FourLevelTwoElectron.SpecificParameters

    __slots__ = Material.__slots__

    def get_material_parameters(self) -> Settings:

        settings = self.Settings.initialize_empty()
        settings.common_parameters = self.get_common_parameters()
        parameters = settings.specific_parameters
        parameters.type = self.get_parameter("typ", "str")
        parameters.base_material = self.get_base_material()

        for key in [key for key in get_type_hints(self.SpecificParameters).keys() if
                    key not in ["base_material", "type", "hash"]]:
            if key in [f"N{i}" for i in range(4)]:
                key = key + "(0)"
            else:
                key = key.replace("_", " ")
            parameters.__setattr__(key, self.get_parameter(key, "list").flatten())

            if settings.common_parameters.anisotropy == "None":
                attr = parameters.__getattribute__(key)
                parameters.__setattr__(key, np.full_like(attr, attr[0]))

        settings.fill_hash_fields()
        return settings


class Graphene(Material):
    @dataclass
    class SpecificParameters(Material.SpecificParameters):
        scattering_rate: float
        chemical_potential: float
        temperature: float
        conductivity_scaling: float
        frequency_samples: int
        quadrature_tolerance: float
        max_quadrature_iterations: int

    @dataclass
    class Settings(Material.Settings):
        advanced_parameters: Graphene.AdvancedParameters
        specific_parameters: Graphene.SpecificParameters

    __slots__ = Material.__slots__

    def get_material_parameters(self) -> Settings:
        settings = self.Settings.initialize_empty()
        settings.common_parameters = self.get_common_parameters()
        settings.advanced_parameters = self.get_advanced_parameters()
        parameters = settings.specific_parameters
        parameters.type = self.get_parameter("type", "str")

        parameters.scattering_rate = self.get_parameter("scattering rate (eV)", "float")
        parameters.chemical_potential = self.get_parameter("chemical potential (eV)", "float")
        parameters.temperature = self.get_parameter("temperature (K)", "float")
        parameters.conductivity_scaling = self.get_parameter("conductivity scaling", "float")
        parameters.frequency_samples = self.get_parameter("frequency samples", "int")
        parameters.quadrature_tolerance = self.get_parameter("quadrature tolerance", "float")
        parameters.max_quadrature_iterations = self.get_parameter("max quadrature iterations", "int")

        settings.fill_hash_fields()
        return settings


class KerrNonLinear(Material):
    @dataclass
    class SpecificParameters(Material.SpecificParameters):
        permittivity: np.ndarray
        chi3: float

    @dataclass
    class Settings(Material.Settings):
        advanced_parameters: None
        specific_parameters: KerrNonLinear.SpecificParameters

    __slots__ = Material.__slots__

    def get_material_parameters(self) -> Settings:

        settings = self.Settings.initialize_empty()
        settings.common_parameters = self.get_common_parameters()
        parameters = settings.specific_parameters
        parameters.type = self.get_parameter("type", "str")

        if settings.common_parameters.anisotropy == "Diagonal":
            parameters.permittivity = self.get_parameter("permittivity", "list").flatten()
        else:
            permittivity = self.get_parameter("permittivity", "float")
            parameters.permittivity = np.array([permittivity, permittivity, permittivity])

        parameters.chi3 = self.get_parameter("chi(3)", "float")

        settings.fill_hash_fields()
        return settings


class Lorentz(Material):
    @dataclass
    class SpecificParameters(Material.SpecificParameters):
        permittivity: np.ndarray
        lorentz_permittivity: np.ndarray
        lorentz_resonance: np.ndarray
        lorentz_linewidth: np.ndarray

    @dataclass
    class Settings(Material.Settings):
        advanced_parameters: None
        specific_parameters: Lorentz.SpecificParameters

    __slots__ = Material.__slots__

    def get_material_parameters(self) -> Settings:
        settings = self.Settings.initialize_empty()
        settings.common_parameters = self.get_common_parameters()
        parameters = settings.specific_parameters
        parameters.type = self.get_parameter("type", "str")

        permittivity = self.get_parameter("permittivity", "float")
        lorentz_permittivity = self.get_parameter("lorentz permittivity", "float")
        lorentz_resonance = self.get_parameter("lorentz resonance", "float")
        lorentz_linewidth = self.get_parameter("lorentz linewidth", "float")

        if settings.common_parameters.anisotropy == "None":
            permittivity = np.array([permittivity, permittivity, permittivity])
            lorentz_permittivity = np.array([lorentz_permittivity, lorentz_permittivity, lorentz_permittivity])
            lorentz_resonance = np.array([lorentz_resonance, lorentz_resonance, lorentz_resonance])
            lorentz_linewidth = np.array([lorentz_linewidth, lorentz_linewidth, lorentz_linewidth])

        parameters.permittivity = permittivity.flatten()
        parameters.lorentz_permittivity = lorentz_permittivity.flatten()
        parameters.lorentz_resonance = lorentz_resonance.flatten()
        parameters.lorentz_linewidth = lorentz_linewidth.flatten()

        settings.fill_hash_fields()
        return settings


class MagneticElectricLorentz(Material):
    @dataclass
    class SpecificParameters(Material.SpecificParameters):
        base_material: Optional[TMaterial.SettingsDict]
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

    @dataclass
    class Settings(Material.Settings):
        advanced_parameters: None
        specific_parameters: MagneticElectricLorentz.SpecificParameters

    __slots__ = Material.__slots__

    def get_material_parameters(self) -> Settings:

        settings = self.Settings.initialize_empty()
        settings.common_parameters = self.get_common_parameters()
        parameters = settings.specific_parameters
        parameters.type = self.get_parameter("type", "str")

        parameters.base_material = self.get_base_material()

        parameters.x0_electric = self.get_parameter('χ0 electric', "list").flatten()
        parameters.de_electric = self.get_parameter('Δε electric', "list").flatten()
        parameters.w0_electric = self.get_parameter('ω0 electric', "list").flatten()
        parameters.d_electric = self.get_parameter('δ electric', "list").flatten()
        parameters.x0_magnetic = self.get_parameter('χ0 magnetic', "list").flatten()
        parameters.dmu_magnetic = self.get_parameter('Δμ magnetic', "list").flatten()
        parameters.w0_magnetic = self.get_parameter('ω0 magnetic', "list").flatten()
        parameters.d_magnetic = self.get_parameter('δ magnetic', "list").flatten()
        parameters.exclude_electric = self.get_parameter('exclude electric', "list").flatten()
        parameters.exclude_magnetic = self.get_parameter('exclude magnetic', "list").flatten()

        if settings.common_parameters.anisotropy != "Diagonal":
            for param in [key for key in get_type_hints(self.SpecificParameters) if
                          key not in ["base_material", "hash", "type"]]:
                attr = parameters.__getattribute__(param)
                parameters.__setattr__(param, np.full_like(attr, attr[0]))

        settings.fill_hash_fields()
        return settings


class Paramagnetic(Material):
    @dataclass
    class SpecificParameters(Material.SpecificParameters):
        base_material: str
        permittivity: np.ndarray
        permeability: np.ndarray

    @dataclass
    class Settings(Material.Settings):
        advanced_parameters: None
        specific_parameters: Paramagnetic.SpecificParameters

    __slots__ = Material.__slots__

    def get_material_parameters(self) -> Settings:

        settings = self.Settings.initialize_empty()
        settings.common_parameters = self.get_common_parameters()
        parameters = settings.specific_parameters
        parameters.type = self.get_parameter("type", "str")
        parameters.base_material = self.get_base_material()

        parameters.permittivity = self.get_parameter("Permittivity", "list").flatten()
        parameters.permeability = self.get_parameter("Permeability", "list").flatten()

        if settings.common_parameters.anisotropy != "Diagonal":
            for param in [key for key in get_type_hints(self.SpecificParameters) if
                          key not in ["hash", "type", "base_material"]]:
                attr = parameters.__getattribute__(param)
                parameters.__setattr__(param, np.full_like(attr, attr[0]))

        settings.fill_hash_fields()
        return settings


class PEC(Material):
    @dataclass
    class SpecificParameters(Material.SpecificParameters):
        ...

    @dataclass
    class Settings(Material.Settings):
        advanced_parameters: None
        specific_parameters: PEC.SpecificParameters

    __slots__ = Material.__slots__

    def get_material_parameters(self) -> Settings:
        settings = self.Settings.initialize_empty()
        settings.common_parameters = self.get_common_parameters()
        settings.specific_parameters.type = self.get_parameter("type", "str")
        settings.fill_hash_fields()
        return settings


class Plasma(Material):
    @dataclass
    class SpecificParameters(Material.SpecificParameters):
        permittivity: np.ndarray
        plasma_resonance: np.ndarray
        plasma_collision: np.ndarray

    @dataclass
    class Settings(Material.Settings):
        advanced_parameters: None
        specific_parameters: Plasma.SpecificParameters

    __slots__ = Material.__slots__

    def get_material_parameters(self: TMaterial) -> Settings:
        settings = self.Settings.initialize_empty()
        settings.common_parameters = self.get_common_parameters()
        parameters = settings.specific_parameters
        parameters.type = self.get_parameter("type", "str")

        permittivity = self.get_parameter("Permittivity", "list")
        plasma_resonance = self.get_parameter("Plasma resonance", "list")
        plasma_collision = self.get_parameter("Plasma collision", "list")

        if settings.common_parameters.anisotropy != "Diagonal":
            permittivity = np.array([permittivity, permittivity, permittivity])
            plasma_resonance = np.array([plasma_resonance, plasma_resonance, plasma_resonance])
            plasma_collision = np.array([plasma_collision, plasma_collision, plasma_collision])

        parameters.permittivity = permittivity.flatten()
        parameters.plasma_resonance = plasma_resonance.flatten()
        parameters.plasma_collision = plasma_collision.flatten()

        settings.fill_hash_fields()
        return settings


class Sampled2Ddata(Material):
    @dataclass
    class AdvancedParameters(Material.AdvancedParameters):
        layer_thickness_enabled: bool
        layer_thickness: float

    class SpecificParameters(Material.SpecificParameters):
        frequencies: np.ndarray
        wavelengths: np.ndarray
        conductivity_real: np.ndarray
        conductivity_imaginary: np.ndarray

    @dataclass
    class Settings(Material.Settings):
        advanced_parameters: Sampled2Ddata.AdvancedParameters
        specific_parameters: Sampled2Ddata.SpecificParameters

    __slots__ = Material.__slots__

    def get_advanced_parameters(self) -> AdvancedParameters:
        settings = self.AdvancedParameters.initialize_empty()
        settings._update(super().get_advanced_parameters().as_dict())
        settings.hash = None
        settings.layer_thickness_enabled = self.get_parameter("layer thickness enabled", "bool")
        settings.layer_thickness = self.get_parameter("layer thickness", "bool")
        settings.fill_hash_fields()
        return settings

    def get_material_parameters(self) -> Settings:
        settings = self.Settings.initialize_empty()
        settings.advanced_parameters = self.get_advanced_parameters()
        settings.common_parameters = self.get_common_parameters()
        parameters = settings.specific_parameters
        parameters.type = self.get_parameter("type", "str")

        sampled_data = self.get_parameter("sampled data", "list")
        parameters.frequencies = np.real(sampled_data[:, 0])
        parameters.wavelengths = frequency_to_wavelength(parameters.frequencies)
        parameters.conductivity_real = np.real(sampled_data[:, 1:])
        parameters.conductivity_imaginary = np.imag(sampled_data[:, 1:])

        settings.fill_hash_fields()
        return settings


class Sampled3Ddata(Material):
    @dataclass
    class SpecificParameters(Material.SpecificParameters):
        frequencies: np.ndarray
        wavelengths: np.ndarray
        permittivity_real: np.ndarray
        permittivity_imaginary: np.ndarray

    @dataclass
    class Settings(Material.Settings):
        advanced_parameters: Material.AdvancedParameters
        specific_parameters: Sampled3Ddata.SpecificParameters

    __slots__ = Material.__slots__

    def get_material_parameters(self) -> Settings:
        settings = self.Settings.initialize_empty()
        settings.common_parameters = self.get_common_parameters()
        settings.advanced_parameters = self.get_advanced_parameters()
        parameters = settings.specific_parameters
        parameters.type = self.get_parameter("type", "str")

        sampled_data = np.array(self.get_parameter("sampled data", "list"))

        parameters.frequencies = np.real(sampled_data[:, 0])
        parameters.wavelengths = frequency_to_wavelength(parameters.frequencies)
        parameters.permittivity_real = np.real(sampled_data[:, 1:])
        parameters.permittivity_imaginary = np.imag(sampled_data[:, 1:])

        settings.fill_hash_fields()
        return settings


class Sellmeier(Material):
    @dataclass
    class SpecificParameters(Material.SpecificParameters):
        a0: np.ndarray
        b1: np.ndarray
        c1: np.ndarray
        b2: np.ndarray
        c2: np.ndarray
        b3: np.ndarray
        c3: np.ndarray

    @dataclass
    class Settings(Material.Settings):
        advanced_parameters: None
        specific_parameters: Sellmeier.SpecificParameters

    __slots__ = Material.__slots__

    def get_material_parameters(self) -> Settings:
        settings = self.Settings.initialize_empty()
        settings.common_parameters = self.get_common_parameters()
        parameters = settings.specific_parameters
        parameters.type = self.get_parameter("type", "str")

        a0 = self.get_parameter("A0", "float")
        b1 = self.get_parameter("B1", "float")
        c1 = self.get_parameter("C1", "float")
        b2 = self.get_parameter("B2", "float")
        c2 = self.get_parameter("C2", "float")
        b3 = self.get_parameter("B3", "float")
        c3 = self.get_parameter("C3", "float")

        if settings.common_parameters.anisotropy == "None":
            a0 = np.array([a0, a0, a0])
            b1 = np.array([b1, b1, b1])
            c1 = np.array([c1, c1, c1])
            b2 = np.array([b2, b2, b2])
            c2 = np.array([c2, c2, c2])
            b3 = np.array([b3, b3, b3])
            c3 = np.array([c3, c3, c3])

        parameters.a0 = a0
        parameters.b1 = b1
        parameters.c1 = c1
        parameters.b2 = b2
        parameters.c2 = c2
        parameters.b3 = b3
        parameters.c3 = c3

        settings.fill_hash_fields()
        return settings


class IndexPerturbation(Material):
    @dataclass
    class Drude(Settings):
        electron_effective_mass: float
        hole_effective_mass: float
        electron_mobility: float
        hole_mobility: float

    @dataclass
    class SorefAndBennet(Settings):
        coefficients: str
        soref_and_bennett_table: np.ndarray

    @dataclass
    class Custom(Settings):
        n_sensitivity_table: np.ndarray
        p_sensitivity_table: np.ndarray

    @dataclass
    class NPDensity(Settings):
        include_np_density: bool
        np_density_model: str
        drude_parameters: Optional[IndexPerturbation.Drude]
        soref_and_bennet_parameters: Optional[IndexPerturbation.SorefAndBennet]
        custom_parameters: Optional[IndexPerturbation.Custom]
        test_value_n: float
        test_value_p: float

    @dataclass
    class LinearSensitivity(Settings):
        Tref: Optional[float]
        dn_dt: Optional[float]
        dk_dt: Optional[float]

    @dataclass
    class Temperature(Settings):
        hash: str
        include_temperature_effects: bool
        linear_sensitivity: bool
        table_of_values: bool
        linear_sensitivity_parameters: Optional[IndexPerturbation.LinearSensitivity]
        temperature_sensitivity_table: Optional[np.ndarray]
        test_value_T: float

    @dataclass
    class SpecificParameters(Material.SpecificParameters):
        np_density_parameters: IndexPerturbation.NPDensity
        temperature_parameters: IndexPerturbation.Temperature
        base_material: str

    @dataclass
    class Settings(Material.Settings):
        advanced_parameters: None
        specific_parameters: IndexPerturbation.SpecificParameters

    __slots__ = Material.__slots__

    def get_drude_model_parameters(self) -> Drude:
        drude = self.Drude.initialize_empty()
        drude.electron_effective_mass = self.get_parameter("electron effective mass", "float")
        drude.hole_effective_mass = self.get_parameter("hole effective mass", "float")
        drude.electron_mobility = self.get_parameter("electron mobility", "float")
        drude.hole_mobility = self.get_parameter("hole mobility", "float")
        drude.fill_hash_fields()
        return drude

    def get_soref_and_bennet_model_parameters(self) -> SorefAndBennet:
        sb = self.SorefAndBennet.initialize_empty()
        sb.coefficients = self.get_parameter("coefficients", "str")
        sb.soref_and_bennett_table = self.get_parameter("soref and bennett table", "list")
        sb.fill_hash_fields()
        return sb

    def get_custom_model_parameters(self) -> Custom:
        custom = self.Custom.initialize_empty()
        custom.n_sensitivity_table = self.get_parameter("n sensitivity table", "list")
        custom.p_sensitivity_table = self.get_parameter("p sensitivity table", "list")
        custom.fill_hash_fields()
        return custom

    def get_linear_sensitivity_parameters(self) -> LinearSensitivity:
        ls = self.LinearSensitivity.initialize_empty()
        ls.Tref = self.get_parameter("Tref", "float")
        ls.dn_dt = self.get_parameter("dn/dt", "float")
        ls.dk_dt = self.get_parameter("dk/dt", "float")
        ls.fill_hash_fields()
        return ls

    def get_material_parameters(self) -> Settings:

        settings = self.Settings.initialize_empty()
        settings.common_parameters = self.get_common_parameters()
        parameters = settings.specific_parameters
        parameters.type = self.get_parameter("type", "str")
        parameters.base_material = self.get_base_material()

        np_density = settings.specific_parameters.np_density_parameters
        temperature = settings.specific_parameters.temperature_parameters

        # NP Density Parameters
        np_density.include_np_density = self.get_parameter("include np density", "bool")
        if np_density.include_np_density:

            np_density.test_value_n = self.get_parameter("test value n", "float")
            np_density.test_value_p = self.get_parameter("test value p", "float")
            np_density.np_density_model = self.get_parameter("np density model", "str")

            if np_density.np_density_model == "Drude":
                np_density.drude_parameters = self.get_drude_model_parameters()

            elif np_density.np_density_model == "Soref and Bennett":
                np_density.soref_and_bennet_parameters = self.get_soref_and_bennet_model_parameters()

            elif np_density.np_density_model == "Custom":
                np_density.custom_parameters = self.get_custom_model_parameters()

        temperature.include_temperature_effects = self.get_parameter("include temperature effects", "bool")
        if temperature.include_temperature_effects:

            temperature.linear_sensitivity = self.get_parameter("linear sensitivity", "bool")
            temperature.table_of_values = not temperature.linear_sensitivity
            temperature.test_value_T = self.get_parameter("test value T", "float")

            if temperature.linear_sensitivity:
                temperature.linear_sensitivity_parameters = self.get_linear_sensitivity_parameters()

            else:
                temperature.temperature_sensitivity_table = self.get_parameter("temperature sensitivity table", "list")

        settings.fill_hash_fields()
        return settings


class ObjectDefinedDielectric(Material):
    @dataclass
    class SpecificParameters(Material.SpecificParameters):
        index: str
        index_units: str

    @dataclass
    class Settings(Material.Settings):
        advanced_parameters: None
        specific_parameters: ObjectDefinedDielectric.SpecificParameters

    __slots__ = Material.__slots__

    def get_material_parameters(self) -> Settings:
        settings = self.Settings.initialize_empty()
        settings.specific_parameters.type = "<Object defined dielectric>"
        return settings


class NKMaterial(Material):
    @dataclass
    class SpecificParameters(Material.SpecificParameters):
        refractive_index: np.ndarray
        imaginary_refractive_index: np.ndarray

    @dataclass
    class Settings(Material.Settings):
        advanced_options: None
        specific_parameters: NKMaterial.SpecificParameters

    __slots__ = Material.__slots__

    def get_material_parameters(self) -> Settings:

        settings = self.Settings.initialize_empty()
        settings.common_parameters = self.get_common_parameters()
        parameters = settings.specific_parameters
        parameters.type = self.get_parameter("type", "str")

        if settings.common_parameters.anisotropy == "Diagonal":
            parameters.refractive_index = self.get_parameter("refractive index", "list").flatten()
            parameters.imaginary_refractive_index = self.get_parameter("imaginary refractive index", "list").flatten()
        else:
            refractive_index = self.get_parameter("refractive index", "float")
            parameters.refractive_index = np.array([refractive_index, refractive_index, refractive_index])
            imaginary_refractive_index = self.get_parameter("imaginary refractive index", "float")
            parameters.imaginary_refractive_index = np.array([imaginary_refractive_index, imaginary_refractive_index,
                                                              imaginary_refractive_index])

        settings.fill_hash_fields()
        return settings


########################################################################################################################
#                                         MATERIAL DATABASE CLASS
########################################################################################################################

class MaterialDatabase(MaterialDatabaseBase):
    _type_to_parameters_map = {
        "Analytic material": AnalyticMaterial,
        "Chi2": Chi2,
        "Chi3 Raman Kerr": Chi3,
        "Chi3/Chi2": Chi3Chi2,
        "Conductive 2D": Conductive2D,
        "Conductive 3D": Conductive3D,
        "Current Driven Gain (version 1.0.0)": CurrentDrivenGain,
        "Debye": Debye,
        "Dielectric": Dielectric,
        "Four-Level Two-Electron (Version 1.0.0)": FourLevelTwoElectron,
        "Graphene": Graphene,
        "Kerr nonlinear": KerrNonLinear,
        "Lorentz": Lorentz,
        "Magnetic Electric Lorentz (Version 1.0.0)": MagneticElectricLorentz,
        "Paramagnetic": Paramagnetic,
        "PEC": PEC,
        "Plasma": Plasma,
        "Sampled 2D data": Sampled2Ddata,
        "Sampled 3D data": Sampled3Ddata,
        "Sellmeier": Sellmeier,
        "Index perturbation": IndexPerturbation,
        "<Object defined dielectric>": ObjectDefinedDielectric
    }

    def get_material_parameters(self, material_name: str) -> TMaterial.Settings:

        if material_name == "<Object defined dielectric>":
            material_type = "<Object defined dielectric>"
        else:
            material_type = self._get_parameter(material_name, "type", "str")

        material_class = MaterialDatabase._type_to_parameters_map[material_type]
        material = material_class(material_name, self)
        material_parameters = material.get_material_parameters()
        return material_parameters

    def _get_active_parameters(self) -> None:
        return None
