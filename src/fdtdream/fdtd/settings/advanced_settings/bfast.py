from ....base_classes import Module
from ....resources import validation


class FDTDBFASTSubsettings(Module):

    def set_BFAST_alpha(self, bfast_alpha: float) -> None:
        """
        Set the BFAST alpha parameter for the simulation.

        The BFAST alpha parameter represents the smallest dielectric
        refractive index in the simulation region. It is generally
        recommended to set this value to 1; however, if a different
        background index is used (for example, 1.33 for water), this
        value should reflect that instead of the default of 1.

        This parameter is crucial for accurately modeling the
        electromagnetic behavior in the simulation, particularly
        in regions where the dielectric properties significantly
        affect the results.

        Parameters:
        - bfast_alpha: A float representing the smallest dielectric
          refractive index in the simulation region.

        Usage:
        - This method should be called to configure the BFAST alpha
          value based on the dielectric properties of the medium
          being simulated.

        Raises:
        - ValueError: If bfast_alpha is less than or equal to 0,
          which would be an invalid refractive index.

        """
        validation.positive_number(bfast_alpha, "bfast_alpha")
        self._set("bfast alpha", bfast_alpha)

    def set_BFAST_dt_multiplier(self, dt_multiplier: float) -> None:
        """
        Set the BFAST time step multiplier for the simulation.

        The BFAST time step multiplier is used to further reduce the
        time step ("dt") in the mesh settings, complementing the
        existing "dt factor." The maximum value for this multiplier
        is 1, indicating no change to the time step. When the
        multiplier is set to a value smaller than 1, it effectively
        reduces the actual time step "dt." This can be particularly
        useful for mitigating diverging problems that cannot be
        resolved by modifying other simulation settings.

        Parameters:
        - dt_multiplier: A float representing the BFAST time step
          multiplier. Must be in the range (0, 1] to effectively
          reduce the time step.

        Raises:
        - ValueError: If dt_multiplier is not greater or equal to zero.

        """
        validation.positive_number(dt_multiplier, "dt_multiplier")
        self._set("bfast dt multiplier", dt_multiplier)
