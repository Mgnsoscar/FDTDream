from __future__ import annotations

from functools import partial
from typing import Unpack, TypedDict, Tuple, Self

import numpy as np
from numpy.typing import NDArray

from .literals import DIRECTIONS, AXES
from .settings import frequency_wavelength, general, beam_options
from .source import Source, SourceGeometry
from ..base_classes.object_modules import ModuleCollection


class CauchyLorentzianBeamKwargs(TypedDict, total=False):
    x: float
    y: float
    z: float
    x_span: float
    y_span: float
    z_span: float
    injection_axis: AXES
    direction: DIRECTIONS


class Settings(ModuleCollection):
    general: general.General
    geometry: SourceGeometry
    freq_and_wavelength: frequency_wavelength.FrequencyWavelength
    beam_options: beam_options.CauchyLorentzian

    def __init__(self, parent_object) -> None:
        super().__init__(parent_object)
        self.general = general.PlaneWave(parent_object)
        self.geometry = SourceGeometry(parent_object)
        self.freq_and_wavelength = frequency_wavelength.FrequencyWavelength(parent_object)
        self.beam_options = beam_options.Gaussian(parent_object)


class CauchyLorentzianBeam(Source):
    settings: Settings

    # region Dev Methods

    def __init__(self, name: str, sim, **kwargs: Unpack[CauchyLorentzianBeamKwargs]) -> None:
        super().__init__(name, sim, **kwargs)

        # Assign the settings module
        self.settings = Settings(self)

        # Set source shape to Cauchy-Lorentzian
        self._set("source shape", "Cauchy-Lorentzian")

        # Filter and apply kwargs
        self._process_kwargs(**kwargs)


    # endregion Dev Methods

    def copy(self, name, **kwargs: Unpack[CauchyLorentzianBeamKwargs]) -> Self:
        return super().copy(name, **kwargs)