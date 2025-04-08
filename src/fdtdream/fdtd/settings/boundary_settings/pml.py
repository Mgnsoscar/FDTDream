import warnings
from typing import TypedDict, Unpack, Any, Union, get_args, cast

import numpy as np

from ....base_classes import Module
from ....resources import validation
from ....resources.literals import PML_PROFILES


class BoundariesKwargs(TypedDict, total=False):
    x_min: Any
    x_max: Any
    y_min: Any
    y_max: Any
    z_min: Any
    z_max: Any


class ProfileKwargs(TypedDict, total=False):
    x_min: PML_PROFILES
    x_max: PML_PROFILES
    y_min: PML_PROFILES
    y_max: PML_PROFILES
    z_min: PML_PROFILES
    z_max: PML_PROFILES


class IntKwargs(TypedDict, total=False):
    x_min: int
    x_max: int
    y_min: int
    y_max: int
    z_min: int
    z_max: int


class FloatKwargs(TypedDict, total=False):
    x_min: Union[float, int]
    x_max: Union[float, int]
    y_min: Union[float, int]
    y_max: Union[float, int]
    z_min: Union[float, int]
    z_max: Union[float, int]


class FDTDPMLSubsettings(Module):

    def set_stretched_coordinate_PML(self) -> None:
        """
        Set the PML type to stretched coordinate PML.

        This is the default and recommended option for PML settings
        in simulations. The stretched coordinate PML is based on
        the formulation proposed by Gedney and Zhao and provides
        effective absorption characteristics.

        """
        self._set("pml type", "stretched coordinate PML")

    def set_uniaxial_anisotropic_PML(self) -> None:
        """
        Set the PML type to legacy uniaxial anisotropic PML.

        This option provides a legacy formulation of PML that is
        rarely used in practice. It may be suitable for specific
        scenarios but is not the default choice.

        """
        self._set("type", "uniaxial anisotropic PML (legacy)")

    def set_same_settings_on_all_boundaries(self, true_or_false: bool) -> None:
        """
        Set whether to apply the same PML settings to all boundaries.

        When enabled, all PML boundaries will share the same settings.
        Disabling this option allows for individual customization of
        PML profiles for each boundary, which can significantly reduce
        simulation times by allowing adjustments only where necessary.

        Parameters:
        - true_or_false: A boolean indicating whether to use the same
          PML settings for all boundaries.

        """
        validation.boolean(true_or_false, "true_or_false")
        extend = self._get("extend structure through pml", bool)
        auto_scale = self._get("auto scale pml parameters", bool)
        self._set("same settings on all boundaries", true_or_false)
        self.auto_scale_pml_parameters(auto_scale)
        self.extend_structure_through_pml(extend)

    def _set_value(self, parameter_name: str, **kwargs: Unpack[BoundariesKwargs]) -> None:
        """Helper function to set pml boundary settings."""

        self._set("same settings on all boundaries", False)

        valid_boundaries = BoundariesKwargs.__annotations__
        boundary_types = {boundary: self._get(f"{boundary.replace("_", " ")} bc", str)
                          for boundary in valid_boundaries}
        boundary_to_index_map = {boundary: i for i, boundary in enumerate(valid_boundaries)}
        prev_values = np.array(self._get(parameter_name, np.ndarray)).flatten().tolist()
        profiles = np.array(self._get("pml profile", np.ndarray)).flatten().tolist()
        idx_to_p = {(i + 1): profile for i, profile in enumerate(get_args(PML_PROFILES))}

        for b, value in kwargs.items():
            if b not in valid_boundaries:
                raise ValueError(f"'{b}' is not a valid boundary. Choose from {valid_boundaries}.")
            elif (parameter_name in ["pml kappa", "pml sigma", "pml polynomial", "pml alpha",
                                     "pml alpha polynomial", "pml min layers", "pml max layers"]
                  and idx_to_p[profiles[boundary_to_index_map[b]]] != "custom"):

                raise ValueError(f"You are trying to set the '{parameter_name}' parameter of boundary '{b}', which "
                                 f"'pml profile' is currently set to '{idx_to_p[profiles[boundary_to_index_map[b]]]}'. "
                                 f"To set this parameter you must first set the pml profile to custom.")

            if boundary_types[b] != "PML":
                warnings.warn(f"Setting '{parameter_name}' on boundary '{b}' will not have any effect, as it is "
                              f"of type '{boundary_types[b]}', not 'PML'.")

            prev_values[boundary_to_index_map[b]] = value

        # Convert to numpy array and transpose to match the format we fetch from the simulation
        new_values = np.array([np.array([value]) for value in prev_values])

        # Supress the warnings that comes if the set value differs from the one accepted by the simulation
        with warnings.catch_warnings(record=True) as caught_warnings:
            warnings.simplefilter("always")

            accepted_values = cast(np.ndarray, self._set(parameter_name, new_values))

            if not caught_warnings:
                return

            warning = (f"\nMethod: set_{parameter_name.split("pml ")[1].replace(" ", "_")}\n"
                       "The following values accepted by the simulation enviroment differs from the input values:\n")
            for b, new_value, accepted_value in zip(valid_boundaries, new_values, accepted_values):
                if parameter_name in ["pml layers", "pml min layers", "pml max layers", "pml polynomial"]:
                    new_value = int(new_value[0])
                    accepted_value = int(accepted_value[0])
                else:
                    new_value = new_value[0]
                    accepted_value = accepted_value[0]

                if new_value != accepted_value:
                    warning += f"\t{b}: input value={new_value}, accepted value={accepted_value}\n"

        warnings.warn(warning)

    def set_profile(self, **kwargs: Unpack[ProfileKwargs]) -> None:
        """
        Sets the PML (Perfectly Matched Layer) profile for the simulation boundaries.

        This method allows the user to specify a PML profile, which determines the absorption properties
        of the PML boundaries in the simulation region. The choice of profile can affect the numerical behavior
        and performance of the simulation.

        Available profiles:
            - **Standard**: Provides good overall absorption with a relatively small number of layers.
              It is recommended when structures extend completely through the PML region and there are no material
              boundaries cutting through PML regions.

            - **Stabilized**: Designed to enhance stability when material boundaries cut through PML regions.
              It may require a higher number of layers compared to the standard profile to achieve similar absorption performance,
              but it effectively mitigates numerical instabilities.

            - **Steep Angle**: Similar to the standard profile but optimized for use with periodic boundary conditions.
              It provides enhanced absorption when light travels nearly parallel to the PML boundaries,
              though it may be less absorptive at coarse discretizations.

            - **Custom**: Allows users to define all PML parameter values manually.
              This profile starts with the parameters of the standard profile and is suitable for advanced users who wish to experiment.

        Raises:
            ValueError:
                - If the specified profile is not valid.
                - If the specified boundary is not valid.

        """
        profile_to_index_map = {profile: i + 1 for i, profile in enumerate(get_args(PML_PROFILES))}
        kwargs = dict(**kwargs)
        for b, value in kwargs.items():
            validation.in_literal(value, "pml_profile", PML_PROFILES)
            kwargs[b] = profile_to_index_map[value]
        self._set_value("pml profile", **kwargs)

    def set_layers(self, **kwargs: Unpack[IntKwargs]) -> None:
        """
        Sets the number of PML layers for the specified boundaries.

        PML boundaries occupy a finite volume surrounding the simulation region and are divided into layers
        for discretization. The number of layers can significantly affect the absorption properties of the PML.
        Generally, increasing the number of layers leads to lower reflections but may also increase simulation time.

        Raises:
            ValueError:
                - If the provided boundary is invalid.
                - If the provided value is not a positive integer.

        """
        self._set("same settings on all boundaries", False)
        min_layers = self._get("pml min layers", np.ndarray)
        min_layers = {b: v for b, v in zip(BoundariesKwargs.__annotations__, min_layers)}
        max_layers = self._get("pml max layers", np.ndarray)
        max_layers = {b: v for b, v in zip(BoundariesKwargs.__annotations__, max_layers)}
        for b, value in kwargs.items():
            validation.positive_integer(value, "pml_layers")
            if value < min_layers[b]:
                raise ValueError(f"You are trying to set the 'layers' parameter for boundary '{b}' to '{value}', "
                                 f"but the 'min layers' parameter is currently '{int(min_layers[b][0])}'. Change the "
                                 f"'min layers' parameter if you want to set the nr of layers to this value.")
            elif value > max_layers[b]:
                raise ValueError(f"You are trying to set the 'layers' parameter for boundary '{b}' to '{value}', "
                                 f"but the 'max layers' parameter is currently '{int(max_layers[b][0])}'. Change the "
                                 f"'max layers' parameter if you want to set the nr of layers to this value.")

        self._set_value("pml layers", **kwargs)

    def set_kappa(self, **kwargs: Unpack[FloatKwargs]) -> None:
        """
        Sets the kappa parameter for PML boundaries.

        Kappa is a unitless parameter that controls the absorption properties of the PML regions.
        It is graded inside the PML using polynomial functions. The effective range of kappa should
        be carefully chosen to ensure optimal absorption without compromising numerical stability.

        Raises:
            ValueError:
                - If the specified boundary is invalid
                - If the specified value is a positive number.

        """
        for b, value in kwargs.items():
            validation.positive_number(value, "pml_kappa")
        self._set_value("pml kappa", **kwargs)

    def set_sigma(self, **kwargs: Unpack[FloatKwargs]) -> None:
        """
        Sets the sigma parameter for PML boundaries.

        Sigma is another unitless parameter that contributes to the absorption properties of PML regions.
        It must be entered as a normalized unitless value. Increasing sigma can enhance absorption but
        may also impact stability, particularly when combined with the alpha parameter.

        Raises:
            ValueError:
                - If the specified boundary is invalid.
                - If the specified value is not a positive number.

        """
        for b, value in kwargs.items():
            validation.positive_number(value, "pml_sigma")
        self._set_value("pml sigma", **kwargs)

    def set_polynomial(self, **kwargs: Unpack[IntKwargs]) -> None:
        """
        Sets the polynomial order for grading kappa and sigma in PML boundaries.

        The polynomial order specifies how kappa and sigma are graded inside the PML regions.
        Higher-order polynomials can improve the absorption characteristics of the PML but may
        also complicate the numerical stability.

        Raises:
            ValueError:
                - If the specified boundary is invalid.
                - If the specified value is not a positive integer.

        """
        for b, value in kwargs.items():
            validation.positive_number(value, "pml_polynomial")
        self._set_value("pml polynomial", **kwargs)

    def set_alpha(self, **kwargs: Unpack[FloatKwargs]) -> None:
        """
        Sets the alpha parameter for PML boundaries.

        Alpha is a unitless parameter that influences the absorption properties of the PML regions.
        This parameter can only be set if the PML type is "stretched coordinate PML."

        Raises:
            ValueError:
                - If the specified boundary is invalid.
                - If the specified value is not a positive number

        """
        if self._get("pml type", str) != "stretched coordinate PML":
            raise ValueError("'alpha' can only be set when PML type is 'stretched coordinate PML'.")
        for b, value in kwargs.items():
            validation.positive_number(value, "pml_alpha")
        self._set_value("pml alpha", **kwargs)

    def set_alpha_polynomial(self, **kwargs: Unpack[FloatKwargs]) -> None:
        """
        Sets the alpha polynomial order for PML boundaries.

        The alpha polynomial order specifies how alpha is graded inside the PML regions.
        This parameter can only be set if the PML type is "stretched coordinate PML."

        Raises:
            ValueError:
                - If the specified boundary is invalid.
                - If the specified value is not a positive number.

        """
        if self._get("pml type", str) != "stretched coordinate PML":
            raise ValueError("'alpha polynomial' can only be set when PML type is 'stretched coordinate PML'.")
        for b, value in kwargs.items():
            validation.positive_number(value, 'pml_alpha_polynomial')
        self._set_value("pml alpha polynomial", **kwargs)

    def set_min_layers(self, **kwargs: Unpack[IntKwargs]) -> None:
        """
        Sets the minimum number of PML layers for the specified boundaries.

        The minimum number of layers enforces a lower limit on how many layers
        are used in the PML region, which can influence the absorption performance.
        Setting a sensible minimum is important to ensure that the PML can effectively
        absorb outgoing waves without significant reflections.

        Raises:
            ValueError:
                - If the provided boundary is invalid.
                - If the provided value is not a positive integer.

        """
        for b, value in kwargs.items():
            validation.positive_integer(value, "pml_min_layers")
        self._set_value("pml min layers", **kwargs)

    def set_max_layers(self, **kwargs: Unpack[IntKwargs]) -> None:
        """
        Sets the maximum number of PML layers for the specified boundaries.

        The maximum number of layers enforces an upper limit on how many layers
        can be used in the PML region. This can help manage simulation performance,
        as excessively high layer counts may lead to longer simulation times without
        significant improvements in absorption.

        Raises:
            ValueError:
                - If the provided boundary is invalid.
                - If the provided value is not a positive integer.

        """
        for b, value in kwargs.items():
            validation.positive_integer(value, "pml_min_layers")
        self._set_value("pml max layers", **kwargs)

    def extend_structure_through_pml(self, true_or_false: bool) -> None:
        """
        Sets whether structures that touch the inner PML boundary should be extended
        in the direction normal to the boundary.

        If enabled, this option will automatically extend any structures
        that are in contact with the inner PML boundary. This is useful for
        ensuring that the structures are adequately represented in the PML region,
        as illustrated in the accompanying images. However, this behavior may not be
        suitable for all types of structures, particularly those that should not
        extend into the PML.

        If the extension is not desired, this option can be disabled, allowing
        the user to manually draw the structure through the PML.

        Parameters:
            true_or_false (bool):
                True to enable the extension of structures through PML,
                False to disable it and allow manual drawing of the structures.

        Raises:
            ValueError: If the input is not a boolean value.

        """
        validation.boolean(true_or_false, "true_or_false")
        self._set("extend structure through pml", true_or_false)

    def auto_scale_pml_parameters(self, true_or_false: bool) -> None:
        """
        Sets whether the PML parameters should be automatically scaled
        based on variations in the time step (dt) during the simulation.

        Enabling this option allows the PML to adjust its parameters
        to maintain optimal absorption performance when the time step
        becomes significantly smaller than expected. This can occur
        due to regions with a very fine mesh or the use of a reduced
        "dt stability factor." Automatic scaling helps ensure that
        the PML remains effective, preserving the accuracy and stability
        of the simulation.

        Parameters:
            true_or_false (bool):
                True to enable automatic scaling of PML parameters,
                False to disable it.

        Raises:
            ValueError: If the input is not a boolean value.

        """
        validation.boolean(true_or_false, "true_or_false")
        self._set("auto scale pml parameters", true_or_false)
