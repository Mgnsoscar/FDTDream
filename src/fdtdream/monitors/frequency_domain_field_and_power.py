from typing import TypedDict, Unpack, Iterable, Self

from .monitor import Monitor
from .settings import general, data_to_record, spectral_averaging, advanced
from ..base_classes import BaseGeometry
from ..base_classes.object_modules import ModuleCollection
from ..resources.literals import DATA_TO_RECORD, MONITOR_TYPES_ALL
from ..results.field_and_power_monitor import FieldAndPower


class FreqDomainFieldAndPowerKwargs(TypedDict, total=False):
    x: float
    y: float
    z: float
    x_span: float
    y_span: float
    z_span: float
    data_to_record: Iterable[DATA_TO_RECORD]
    monitor_type: MONITOR_TYPES_ALL


class Geometry(BaseGeometry):
    class _Dimensions(TypedDict, total=False):
        x_span: float
        y_span: float
        z_span: float

    def set_dimensions(self, **kwargs: Unpack[_Dimensions]) -> None:
        monitor_type = self._get("monitor type", str)
        for k, v in kwargs.items():
            if monitor_type == "point":
                raise ValueError(f"Parameter '{k}' cannot be assigned to monitor with monitor type 'point'.")
            elif "linear" in monitor_type and k[0] not in monitor_type:
                raise ValueError(f"Parameter '{k}' cannot be assigned to monitor which is linear "
                                 f"along axis '{monitor_type}'")
            elif "2d" in monitor_type and k[0] in monitor_type:
                raise ValueError(f"Parameter '{k}' cannot be assigned to monitor with monitor type '{monitor_type}', "
                                 f"as the monitor has no span along this axis.")
        super().set_dimensions(**kwargs)

    def set_monitor_type(self, monitor_type: MONITOR_TYPES_ALL) -> None:
        """
        Sets the type and orientation of the monitor for the simulation.

        The monitor type determines the available spatial settings for the simulation region.
        Depending on the monitor type selected, different spatial parameters will be enabled,
        including the center position, min/max positions, and span for the X, Y, and Z axes.

        Args:
            monitor_type (MONITOR_TYPES_ALL): The type of monitor to set, which controls the available
                                               spatial settings for the simulation region.

        Raises:
            ValueError: If the provided monitor_type is not a valid type.
        """

        self._set("monitor type", monitor_type)

    def set_down_sampling(self, x: int = None, y: int = None, z: int = None) -> None:
        """
        Sets the spatial downsampling value for the specified monitor axes.

        The downsampling parameter controls how frequently data is recorded along the specified axis.
        A downsample value of N means that data will be sampled every Nth grid point.
        Setting the downsample value to 1 will provide the most detailed spatial information,
        recording data at every grid point.

        Args:
            x/y/z (int): The downsample value along the specified axis. Must be greater than or equal to 1.
        """
        kwargs = {"x": x, "y": y, "z": z}
        for axis, down_sampling in kwargs.items():
            self._set(f"down sample {axis.capitalize()}", down_sampling)


class Settings(ModuleCollection):
    general: general.General
    geometry: Geometry
    data_to_record: data_to_record.DataToRecord
    spectral_averaging: spectral_averaging.SpectralAveraging
    advanced: advanced.FreqAndTimeDomainMonitor

    __slots__ = ["general", "geometry", "data_to_record", "spectral_averaging", "advanced"]

    def __init__(self, parent_object) -> None:
        super().__init__(parent_object)
        self.general = general.General(parent_object)
        self.geometry = Geometry(parent_object)
        self.data_to_record = data_to_record.DataToRecord(parent_object)
        self.spectral_averaging = spectral_averaging.SpectralAveraging(parent_object)
        self.advanced = advanced.FreqAndTimeDomainMonitor(parent_object)


class FreqDomainFieldAndPowerMonitor(Monitor):
    settings: Settings

    def __init__(self, name: str, simulation, **kwargs: Unpack[FreqDomainFieldAndPowerKwargs]):
        super().__init__(name, simulation, **kwargs)

        # Assign the settings module
        self.settings = Settings(self)

        # Filter and apply kwargs
        self._process_kwargs(**kwargs)

    def _process_kwargs(self, copied: bool = False, **kwargs) -> None:
        """Filters and applies the kwargs specific to the Rectangle structure type."""

        # Abort if the kwargs are empty
        if not kwargs:
            return

        # Initialize dicts
        position = {}
        dimensions = {}
        data = None
        monitor_type = None

        # Filter kwargs
        for k, v in kwargs.items():
            if k == "data_to_record":
                data = v
            elif k == "monitor_type":
                monitor_type = v
            elif k in ["x", "y", "z"]:
                position[k] = v
            elif k in ["x_span", "y_span", "z_span"]:
                dimensions[k] = v

        # Apply kwargs
        if monitor_type:
            self.settings.geometry.set_monitor_type(monitor_type)
        if position:
            self.settings.geometry.set_position(**position)
        if dimensions:
            self.settings.geometry.set_dimensions(**dimensions)
        if data:
            self.settings.data_to_record.set_data_to_record(disable_all_first=True, **{k: True for k in data})

    def _get_results(self) -> FieldAndPower:
        return FieldAndPower._extract_results(self.name, self._lumapi)

    def make_profile_monitor(self, profile: bool = True) -> None:
        """
        Turns the monitor into a profile monitor if 'profile' argument is True.

        If True, sets the method for spatial interpolation of electromagnetic fields recorded by the monitor to
        'specified position'. This means fields are recorded exactly where the monitor is located. This is the
        default for 'profile' monitors in lumerical FDTD.

        If False, sets the method for spatial interpolation to 'nearest mesh cell'.

        The interpolation method determines how the electric and magnetic field components are
        aligned spatially for calculations of the Poynting vector and electromagnetic energy density.
        """
        if profile:
            self.settings.advanced.set_spatial_interpolation("specified position")
        else:
            self.settings.advanced.set_spatial_interpolation("nearest mesh cell")


    def copy(self, name, **kwargs: Unpack[FreqDomainFieldAndPowerKwargs]) -> Self:
        return super().copy(name, **kwargs)