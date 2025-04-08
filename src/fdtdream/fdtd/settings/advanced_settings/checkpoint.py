from ....base_classes import Module
from ....resources import validation


class FDTDCheckpointSubsettings(Module):

    def set_checkpoint_during_simulation(self, true_or_false: bool, checkpoint_period: int = None) -> None:
        """
        Configure the creation of checkpoints during the simulation.

        This method allows users to enable or disable the creation of
        checkpoints at specified intervals during the simulation run.
        Checkpoints are useful for saving the state of the simulation
        at regular intervals, which can help in recovering from
        unexpected interruptions or failures. The frequency of these
        checkpoints is determined by the checkpoint_period parameter.

        Parameters:
        - true_or_false: A boolean indicating whether to enable
          (True) or disable (False) checkpointing during the simulation.
        - checkpoint_period: An optional integer specifying the
          interval (in time steps) at which checkpoints should be
          created. This parameter is only relevant if
          true_or_false is set to True.

        Usage:
        - This method should be called to configure checkpointing for
          the simulation, ensuring that critical progress is saved
          at regular intervals.

        Raises:
        - ValueError: If checkpoint_period is provided as a negative
          integer.

        """
        self._set("set checkpoint during simulation", true_or_false)

        if true_or_false and checkpoint_period is not None:
            validation.positive_integer(checkpoint_period, "checkpoint_period")
            self._set("checkpoint period", checkpoint_period)

    def set_checkpoint_at_shutoff(self, true_or_false: bool) -> None:
        """
        Configure the creation of checkpoints at simulation shutoff.

        This method allows users to enable or disable the creation of
        checkpoints whenever the simulation ends, except in cases
        where the "Quit and Don't Save" option is selected.
        This feature is useful for preserving the state of the
        simulation for future analysis or review, ensuring that data
        is not lost when the simulation concludes.

        Parameters:
        - true_or_false: A boolean indicating whether to enable
          (True) or disable (False) checkpoint creation at the
          simulation shutoff.

        Usage:
        - This method should be called to configure whether a
          checkpoint should be created automatically upon
          simulation completion.

        Note:
        - The checkpoint will only be created if the simulation ends
          normally and does not include the "Quit and Don't Save"
          option.

        """
        validation.boolean(true_or_false, "true_or_false")
        self._set("set checkpoint at shutoff", true_or_false)
