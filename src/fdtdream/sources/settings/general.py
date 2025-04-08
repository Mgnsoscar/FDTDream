
from typing import TypedDict, Unpack

from .literals import (DIRECTION_DEFINITIONS, POLARIZATION_DEFINITIONS, DIRECTIONS, CONVERSIONS,
                       PLANE_WAVE_TYPES, AXES)
from ...base_classes.object_modules import Module
from ...resources import validation
from ...resources.functions import convert_length, convert_frequency
from ...resources.literals import FREQUENCY_UNITS, LENGTH_UNITS


# region Kwargs

class SetUnitVectorKwargs(TypedDict, total=False):
    ux: float
    uy: float
    uz: float


class SetKVectorKwargs(TypedDict, total=False):
    kx: float
    ky: float
    kz: float

# endregion Kwargs


class General(Module):

    def set_amplitude(self, amplitude: float) -> None:
        """
        Sets the amplitude for the source.

        Args:
            amplitude (float): The amplitude value to set.

        Raises:
            ValueError: If amplitude is negative.
        """
        if amplitude < 0:
            raise ValueError("Amplitude must be non-negative.")
        self._set("amplitude", amplitude)

    def set_phase(self, phase: float) -> None:
        """
        Sets the phase for the source.

        The phase of the point source, measured in units of degrees.
        This parameter is only useful for setting relative phase delays
        between multiple radiation sources.

        Args:
            phase (float): The phase value to set. Should be given in degrees.

        Raises:
            ValueError: If the phase is not within the expected range (0 to 360 degrees).
        """
        if not (0 <= phase <= 360):  # Assuming the phase should be in the range [0, 360]
            raise ValueError(f"Phase must be between 0 and 360 degrees, got '{phase}'.")
        self._set("phase", phase)

    def set_direction_definition(self, definition: DIRECTION_DEFINITIONS) -> None:
        """
        Sets the direction definition for the source.

        Args:
            definition (DIRECTION_DEFINITIONS): The direction definition to set.
                Must be one of the predefined direction definitions.

        Raises:
            ValueError: If the definition is not valid.
        """
        validation.in_literal(definition, "definition", DIRECTION_DEFINITIONS)
        self._set("direction definition", definition)

    def set_polarization_definition(self, definition: POLARIZATION_DEFINITIONS) -> None:
        """
        Sets the polarization definition for the source.

        Args:
            definition (POLARIZATION_DEFINITIONS): The polarization definition to set.
                Must be one of the predefined polarization definitions.

        Raises:
            ValueError: If the definition is not valid.
        """
        validation.in_literal(definition, "definition", POLARIZATION_DEFINITIONS)
        self._set("polarization definition", definition)

    def set_injection_axis(self, injection_axis: AXES) -> None:
        """
        Sets the injection axis for the source.

        This parameter sets the axis along which the radiation propagates.

        Args:
            injection_axis (INJECTION_AXES): The injection axis to set.
                Must be one of the predefined injection axes.

        Raises:
            ValueError: If the axis is not valid.
        """
        validation.axis(injection_axis)
        self._set("injection axis", injection_axis + "-axis")

    def set_direction(self, direction: DIRECTIONS) -> None:
        """
        Sets the direction for the source.

        This field specifies the direction in which the radiation propagates.
        Forward corresponds to propagation in the positive direction,
        while Backward corresponds to propagation in the negative direction.

        Args:
            direction (DIRECTIONS): The direction to set.
                Must be one of the predefined directions.

        Raises:
            ValueError: If the direction is not valid.
        """
        validation.in_literal(direction, "direction", DIRECTIONS)
        self._set("direction", direction.capitalize())

    def set_unit_vectors(self, **kwargs: Unpack[SetUnitVectorKwargs]) -> None:
        """
        Sets the unit vectors for the source.

        Args:
            ux (float, optional): The x-component of the unit vector.
                If None, the x-component will not be set.
            uy (float, optional): The y-component of the unit vector.
                If None, the y-component will not be set.
            uz (float, optional): The z-component of the unit vector.
                If None, the z-component will not be set.

        Raises:
            ValueError: If the 'direction definition' is not set to 'unit-vector'.
        """

        if not kwargs:
            raise ValueError("You must provide arguments for this method.")

        if self._get("direction definition", str) != "unit-vector":
            raise ValueError(f"You cannot set the unit vectors when 'direction definition' "
                             f"is not 'unit-vector'.")

        valid_arguments = list(SetUnitVectorKwargs.__annotations__.keys())
        for axis, value in kwargs.items():
            validation.in_list(axis, valid_arguments)
            validation.number(value, axis)
            self._set(axis, value)

    def set_k_vectors(self, **kwargs: Unpack[SetKVectorKwargs]) -> None:
        """
        Sets the wave vector components for the source.

        Args:
            kx (float, optional): The x-component of the wave vector.
                If None, the x-component will not be set.
            ky (float, optional): The y-component of the wave vector.
                If None, the y-component will not be set.
            kz (float, optional): The z-component of the wave vector.
                If None, the z-component will not be set.

        Raises:
            ValueError: If the 'direction definition' is not set to 'k-vector'.
        """

        if not kwargs:
            raise ValueError("You must provide arguments for this method.")

        if self._get("direction definition", str) != "k-vector":
            raise ValueError(f"You cannot set the k-vectors when 'direction definition' "
                             f"is not 'k-vector'.")

        valid_arguments = list(SetKVectorKwargs.__annotations__.keys())
        for axis, value in kwargs.items():
            validation.in_list(axis, valid_arguments)
            validation.number(value, axis)
            self._set(axis, value)

    def set_polarization_angle_theta(self, theta: float) -> None:
        """
        Sets the polarization angle theta for the source.

        In 3D simulations, this is the angle of propagation, in degrees,
        with respect to the injection axis of the source.
        In 2D simulations, it is the angle of propagation, in degrees,
        rotated about the global Z-axis in a right-hand context,
        i.e., the angle of propagation in the XY plane.

        Args:
            theta (float): The angle of polarization in degrees.

        Raises:
            ValueError: If the 'direction definition' is not set to 'axis'.
        """

        if self._get("direction definition", str) == "axis":
            self._set("theta", theta)
        else:
            raise ValueError(f"You cannot set the polarization angle theta when "
                             f"'direction definition' is not 'axis'.")

    def set_polarization_angle_phi(self, phi: float) -> None:
        """
        Sets the polarization angle phi for the source.

        In 3D simulations, this is the angle of propagation, in degrees,
        rotated about the injection axis of the source in a right-hand context.
        In 2D simulations, this value is not used.

        Args:
            phi (float): The angle of polarization in degrees.

        Raises:
            ValueError: If the 'direction definition' is not set to 'axis'.
        """

        if self._get("direction definition", str) == "axis":
            self._set("phi", phi)
        else:
            raise ValueError(f"You cannot set the polarization angle phi when "
                             f"'direction definition' is not 'axis'.")

    def set_polarization_angle(self, angle: float) -> None:
        """
        Sets the polarization angle for the source.

        The polarization angle defines the orientation of the injected electric field
        and is measured with respect to the plane formed by the direction of propagation
        and the normal to the injection plane. A polarization angle of zero degrees defines
        P-polarized radiation, regardless of the direction of propagation, while a
        polarization angle of 90 degrees defines S-polarized radiation.

        Args:
            angle (float): The angle of polarization in degrees.

        Raises:
            ValueError: If the 'polarization definition' is not set to 'angle'.
        """

        if self._get("polarization definition", str) == "angle":
            self._set("polarization angle", angle)
        else:
            raise ValueError(f"You cannot set the polarization angle when "
                             f"'polarization definition' is not 'angle'.")

    def set_angle_to_wavevector_conversion(self, conversion: CONVERSIONS) -> None:
        """
        Sets the method of converting angles to wavevector components for the source.

        This parameter defines how angles are translated into wavevector components, which determine the
        propagation direction and phase velocity of the wave within the simulation space.

        Args:
            conversion (CONVERSIONS): The conversion method to set.
                Must be one of the predefined conversion options.

        Raises:
            ValueError: If the conversion method is not valid.
        """

        validation.in_literal(conversion, "conversion", CONVERSIONS)
        self._set("angle to wavevector conversion", conversion)

    def set_user_defined_angle_to_wavevector_conversion(self, wavelength_point: float = None,
                                                        frequency_point: float = None,
                                                        length_units: LENGTH_UNITS = None,
                                                        frequency_units: FREQUENCY_UNITS = "THz") -> None:
        """
        Sets a user-defined conversion from angle to wavevector using either a wavelength or frequency point.

        This method allows manual specification of the angle-to-wavevector conversion based on either
        a wavelength or frequency. If a wavelength point is provided, it is converted to meters based
        on the specified or global simulation units. If a frequency point is given, it is converted to
        Hz based on the provided frequency units. The user cannot specify both wavelength and frequency
        points simultaneously.

        Args:
            wavelength_point (float, optional): The wavelength for conversion, in the specified or global units.
            frequency_point (float, optional): The frequency for conversion, in the specified frequency units.
            length_units (LENGTH_UNITS, optional): Units for the wavelength, defaults to the global simulation units.
            frequency_units (FREQUENCY_UNITS): Units for the frequency, defaults to "THz".

        Raises:
            ValueError: If both wavelength_point and frequency_point are provided or if neither is provided.
            ValueError: If length_units or frequency_units are invalid.

        """
        if wavelength_point is not None and frequency_point is not None:
            raise ValueError(
                f"You cannot set both wavelength point and frequency point at the same time. Choose one."
            )
        elif wavelength_point is None and frequency_point is None:
            raise ValueError(
                f"You must provide either a wavelength point or a frequency point."
            )

        self._set("angle to wavelength conversion", "user defined")

        if wavelength_point is not None:
            if length_units is None:
                length_units = self._units
            else:
                validation.in_literal(length_units, "length_units", LENGTH_UNITS)
            wavelength_point = convert_length(wavelength_point, from_unit=length_units, to_unit="m")
            self._set("define by", "wavelength")
            self._set("wavelength point", wavelength_point)

        if frequency_point is not None:
            validation.in_literal(frequency_units, "frequency_units", FREQUENCY_UNITS)
            frequency_point = convert_frequency(frequency_point, from_unit=frequency_units, to_unit="Hz")
            self._set("define by", "frequency")
            self._set("frequency point", frequency_point)


class PlaneWave(General):

    def set_plane_wave_type(self, wave_type: PLANE_WAVE_TYPES) -> None:
        """
        Sets the type of the plane wave source.

        This method allows setting the specific type of plane wave for the source.
        This setting applies only to plane wave sources and provides options that
        can be chosen from the predefined plane wave types.

        Args:
            wave_type (PLANE_WAVE_TYPES): The plane wave type to set, chosen from the allowed plane wave types.

        Raises:
            ValueError: If the specified plane wave type is not valid.
        """

        validation.in_literal(wave_type, "type_", PLANE_WAVE_TYPES)
        self._set("plane wave type", wave_type)
