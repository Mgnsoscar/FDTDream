from typing import TypedDict, Unpack, Self, List, Union
from scipy.constants import c as light_speed
from numpy.typing import NDArray
import numpy as np
from ..resources.functions import convert_length
from .monitor import Monitor
from .settings import general, data_to_record, spectral_averaging, advanced
from ..base_classes import BaseGeometry
from ..base_classes.object_modules import ModuleCollection
from ..resources.literals import DATA_TO_RECORD, MONITOR_TYPES_ALL, LENGTH_UNITS
from ..results.field_and_power_monitor import FieldAndPower
from ..results.monitors import FieldAndPowerMonitor, Field
from ..resources import errors


class FreqDomainFieldAndPowerKwargs(TypedDict, total=False):
    x: float
    y: float
    z: float
    x_span: float
    y_span: float
    z_span: float
    data_to_record: List[DATA_TO_RECORD]
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

    def _get_results_2(self) -> FieldAndPower:
        monitor_type = self._get("monitor type", str)
        return FieldAndPower._extract_results(self.name, monitor_type, self._lumapi)

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

    def _get_results(self) -> Union[FieldAndPowerMonitor, None]:

        # Fetch lumapi
        lumapi = self._lumapi

        # Get the list of available results
        available_results = lumapi.getresult(self.name).split("\n")

        # Check if any of the data we're interested in is available. Return None if there is no data.
        interesting_data = ["power", "T", "E", "H", "P"]
        if not any([data in available_results for data in interesting_data]):
            return None

        # Ready the set of parameters to be saved.
        parameters = {
            "Monitor type": "Frequency domain field and power",
            "Geometry type": self._get("monitor type", str),
            "x [nm]": convert_length(self._get("x", float), "m", "nm"),
            "y [nm]": convert_length(self._get("y", float), "m", "nm"),
            "z [nm]": convert_length(self._get("z", float), "m", "nm"),
            "x span [nm]": convert_length(self._get("x span", float), "m", "nm"),
            "y span [nm]": convert_length(self._get("y span", float), "m", "nm"),
            "z span [nm]": convert_length(self._get("z span", float), "m", "nm")
        }

        # region Extract wavelengths:
        frequencies: NDArray = lumapi.getresult(self.name, "f")

        # Convert to wavelengths and reverse so the array is from shortest to longest.
        raw_wavelengths = light_speed / frequencies[::-1]

        # Flatten array and convert to nanometers. Set type to 32 bit float.
        wavelengths_converted = convert_length(raw_wavelengths.flatten(), "m", "nm").astype(np.float32)

        wavelengths = np.ascontiguousarray(wavelengths_converted)
        # endregion

        # region Extract coordinates
        fetched_axes = {}
        for axis in ["x", "y", "z"]:

            # Fetch the array of coordinates along the specified axis.
            coordinates = lumapi.getresult(self.name, axis)

            # Convert from meters to nanometers. Allows us to use 32 bit floats in stead of 62 bit floats.
            coordinates = convert_length(coordinates, "m", "nm")

            # If the coordinates is just a single float, convert it to an array.
            if type(coordinates) is float:
                coordinates = np.array([coordinates], dtype=np.float32)

            # If not, flatten the array and convert values to 32 bit floats.
            else:
                coordinates = coordinates.flatten().astype(np.float32)

            # Assign the array to the dictionary. Make sure array is contiuous
            fetched_axes[axis] = np.ascontiguousarray(coordinates)
        # endregion

        # region Extract T and power
        if "T" in available_results:

            # Fetch transmission data
            t_data = lumapi.getresult(self.name, "T")
            t_processed = t_data["T"].flatten()[::-1].astype(np.float32)
            T = np.ascontiguousarray(t_processed)

            power_data = lumapi.getresult(self.name, "power")
            power_processed = power_data.flatten()[::-1]
            power = np.ascontiguousarray(power_processed)

        else:
            T = None
            power = None
        # endregion

        # region Extract fields
        fetched_fields = {}
        fields = ["E", "H", "P"]
        for field in fields:

            # Build components list from expected axes
            axes = ["x", "y", "z"]
            components = [axis for axis in axes if field + axis in available_results]

            # Special handling for P-field
            if field == "P" and "P" in available_results and not components:
                # Get the data
                try:
                    data_dict = lumapi.getresult(self.name, 'P')
                except errors.LumApiError as e:
                    if "Can not find result 'P' in the result provider" in str(e):
                        fetched_fields[field] = None
                        continue
                    else:
                        raise e

                # Infer components from which E and H fields are present
                e_fields = {axis for axis in axes if "E" + axis in available_results}
                h_fields = {axis for axis in axes if "H" + axis in available_results}

                present_axes = sorted(e_fields & h_fields)

                if len(present_axes) == 3:
                    component_str = "xyz"
                    data = data_dict["P"]
                elif len(present_axes) == 2:
                    missing_axis = list(set(axes) - set(present_axes))[0]
                    component_str = missing_axis

                    data = np.stack([data_dict[field + comp] for comp in component_str], axis=-1)

                else:
                    fetched_fields[field] = None
                    continue

            else:
                if field not in available_results:
                    fetched_fields[field] = None
                    continue

                # Turn the components into a string, ie. 'xyz'
                component_str = "".join(components)

                # Extract the result dict for the field.
                data_dict = lumapi.getresult(self.name, field)

                # If all components are in a single array
                if field in data_dict:
                    data = data_dict[field]
                else:
                    data = np.stack(
                        [data_dict[field + axis] for axis in axes if field + axis in data_dict],
                        axis=-1
                    )

            # Reverse all arrays along the wavelength axis
            try:
                data = np.ascontiguousarray(data[:, :, :, ::-1, :])

            except Exception as e:
                print(field + ": " + str(e))
            fetched_fields[field] = Field(field, data, component_str)
        # endregion

        monitor_results = FieldAndPowerMonitor(self.name, parameters, wavelengths,
                                               T=T, power=power,
                                               **fetched_axes, **fetched_fields)
        return monitor_results


