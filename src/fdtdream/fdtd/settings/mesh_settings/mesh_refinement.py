from ....base_classes import Module


class FDTDMeshRefinementSubsettings(Module):

    def set_staircase(self) -> None:
        """
        Set the mesh refinement method to Staircasing.

        This method configures the mesh refinement approach to use the Staircasing
        technique. In this method, the material properties at each position of the
        Yee cell are evaluated, using only the properties of the material at that
        location for the E-field calculation.

        Limitations:
        - This approach does not account for variations within a Yee cell, resulting
          in a "staircase" permittivity mesh that aligns with the Cartesian mesh.
        - Layer thickness cannot be resolved more finely than the mesh step size,
          limiting the resolution of structure details.

        Usage:
        - Ideal for simulations where high resolution and material variation
          within the Yee cell are not critical.
        """

        self._set("mesh refinement", "staircase")

    def set_conformal_variant_0(self) -> None:
        """
        Set the mesh refinement method to Conformal Variant 0.

        This method configures the mesh refinement approach to use Conformal
        Variant 0. In this variant, Lumerical's Conformal Mesh Technology (CMT)
        is not applied to interfaces involving metals or Perfect Electrical
        Conductors (PEC). This approach leverages a rigorous physical description
        of Maxwell's equations to handle material interfaces, but does not enhance
        accuracy for metallic interfaces.

        Benefits:
        - Suitable for simulations involving dielectric materials where metal
          interfaces do not require special handling.
        - Can improve accuracy for dielectric interfaces compared to the
          Staircasing method.

        Usage:
        - Ideal when modeling materials that do not involve PEC or metal
          interfaces, allowing for improved simulation performance.
        """

        self._set("mesh refinement", "conformal variant 0")

    def set_conformal_variant_1(self) -> None:
        """
        Set the mesh refinement method to Conformal Variant 1.

        This method configures the mesh refinement approach to use Conformal
        Variant 1, where Lumerical's Conformal Mesh Technology (CMT) is applied
        to all materials, including Perfect Electrical Conductors (PEC) and metals.
        This variant provides enhanced accuracy for a given mesh size, allowing for
        faster simulations without sacrificing accuracy.

        Benefits:
        - Provides greater accuracy in simulations involving a wider variety of
          materials, including metals and PEC.
        - Can significantly reduce computation time while maintaining accuracy.

        Usage:
        - Suitable for general simulations requiring robust handling of material
          interfaces, particularly when both dielectric and metallic materials are present.
        """

        self._set("mesh refinement", "conformal variant 1")

    def set_conformal_variant_2(self) -> None:
        """
        Set the mesh refinement method to Conformal Variant 2.

        This method configures the mesh refinement approach to use Conformal
        Variant 2, which applies Lumerical's Conformal Mesh Technology (CMT)
        to all materials except for interfaces involving Perfect Electrical
        Conductors (PEC) and metals, where the Yu-Mittra method 1 is employed.
        This variant allows for greater accuracy in modeling interfaces while
        still improving performance compared to traditional methods.

        Benefits:
        - Combines the benefits of CMT for general material interfaces with
          improved handling of PEC and metallic interfaces via the Yu-Mittra method 1.
        - Provides a balanced approach for accuracy and simulation speed.

        Usage:
        - Ideal for simulations that involve complex material interfaces, especially
          those containing both dielectric and PEC materials.
        """

        self._set("mesh refinement", "conformal variant 2")

    def set_dielectric_volume_average(self, meshing_refinement: float = None) -> None:
        """
        Set the mesh refinement method to Dielectric Volume Average.

        This method configures the mesh refinement approach to utilize the
        dielectric volume average method. This method averages the permittivity
        of dielectric materials within each Yee cell by dividing the cell into
        subcells. The average permittivity is calculated based on the volume
        fraction of dielectric materials present. The method is particularly useful
        for low index contrast dielectric structures.

        Parameters:
        - meshing_refinement: A float value representing the refinement level for
          the meshing process. This parameter determines how finely the cell is
          subdivided to achieve the volume average. Higher values will yield more
          precise results but may increase computational costs.

        Benefits:
        - Provides a simple yet effective way to handle dielectric interfaces
          within Yee cells.
        - Suitable for cases where low index contrast spatial variations are present,
          allowing for effective averaging of permittivity.

        Usage:
        - Ideal for simulations where dielectric materials dominate and non-dielectric
          materials are either absent or present only in minimal amounts.

        Raises:
        - Any exceptions related to parameter setting in the simulation,
          including invalid values for meshing_refinement.
        """

        self._set("mesh refinement", "dielectric volume average")
        if meshing_refinement is not None:
            self._set("meshing refinement", meshing_refinement)

    def set_volume_average(self) -> None:
        """
        Set the mesh refinement method to Volume Average.

        This method configures the mesh refinement approach to utilize the
        volume average method. In this approach, the permittivity of each Yee cell
        is calculated as the simple volume average of the permittivities of the
        materials present in that cell. This method allows for the inclusion of
        multiple dispersive materials and provides a straightforward way to model
        their interactions.

        Benefits:
        - Suitable for simulating scenarios where the interaction of two materials
          within a Yee cell is important.
        - Provides a reasonable balance between accuracy and computational efficiency
          compared to more complex methods.

        Usage:
        - Ideal for simulations that require a basic yet effective treatment of
          permittivity averaging in regions with two materials.
        """

        self._set("mesh refinement", "volume average")

    def set_Yu_Mittra_method_1(self) -> None:
        """
        Set the mesh refinement method to Yu-Mittra Method 1.

        This method configures the simulation to use Yu-Mittra Method 1 for mesh refinement.
        This approach enhances the accuracy when modeling interfaces between perfect electric
        conductors (PEC) and dielectric materials. It evaluates the electric field by
        considering only the region outside the PEC where the electric field is non-zero.

        Benefits:
        - Provides improved accuracy for simulations involving PEC/dielectric interfaces.
        - Extends the original Yu-Mittra formulation to accommodate arbitrary dispersive media.

        Usage:
        - Recommended for cases where precision at PEC interfaces is critical for the simulation
          results.
        """

        self._set("mesh refinement", "Yu-Mittra method 1")

    def set_Yu_Mittra_method_2(self) -> None:
        """
        Set the mesh refinement method to Yu-Mittra Method 2.

        This method configures the simulation to use Yu-Mittra Method 2 for mesh refinement.
        This approach improves accuracy when modeling dielectric interfaces by assigning an
        effective permittivity to each material component in the Yee cell, weighted by the
        fraction of the mesh step that is inside each material.

        Benefits:
        - Enhances simulation fidelity when dealing with dielectric interfaces with spatial
          variations in permittivity.
        - Suitable for scenarios where precise modeling of permittivity distribution is necessary.

        Usage:
        - Ideal for simulations that involve complex dielectric interactions and require
          higher accuracy in permittivity averaging.
        """

        self._set("mesh refinement", "Yu-Mittra method 2")

    def set_precise_volume_average(self, meshing_refinement: float = None) -> None:
        """
        Set the mesh refinement method to Precise Volume Average.

        This method configures the simulation to use the Precise Volume Average approach for
        mesh refinement. It provides a highly sensitive meshing technique that accurately
        calculates the average permittivity in the mesh cells, especially important for
        photonic inverse design.

        Parameters:
        - meshing_refinement: A float value that specifies the level of refinement for the
          meshing process. This parameter enhances the accuracy of permittivity averaging,
          with a default value of 5 (can be increased up to 12 for maximum precision).

        Benefits:
        - Allows for fine-tuned accuracy in simulations that require sensitive adjustments
          to small geometric variations, such as those needed for accurate gradient
          calculations in inverse design processes.
        - It is memory intensive but essential for applications demanding high precision.

        Usage:
        - Recommended for scenarios where small variations in geometry or permittivity can
          significantly affect simulation outcomes, particularly in advanced photonic design.
        """

        self._set("mesh refinement", "precise volume average")
        if meshing_refinement is not None:
            self._set("meshing refinement", meshing_refinement)

