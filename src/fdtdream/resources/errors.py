from ..lumapi import lumapi

LumApiError = lumapi.LumApiError


class FDTDreamError(Exception):
    def __init__(self, message: str):
        super().__init__(message)


# region Name Errors

class FDTDreamNameError(FDTDreamError):
    ...


class FDTDreamEmptyNameError(FDTDreamNameError):
    ...


class FDTDreamNotUniqueNameError(FDTDreamNameError):
    ...


# endregion

# region Material Errors
class FDTDreamMaterialError(FDTDreamError):
    ...


class FDTDreamMaterialNotFoundError(FDTDreamMaterialError):
    ...


class FDTDreamNotObjectDefinedDielectric(FDTDreamMaterialError):
    ...


# endregion

# region Misc Errors

class FDTDreamBadKwargError(FDTDreamError):
    ...


class FDTDreamParameterNotFound(FDTDreamError):
    ...


class FDTDreamNotBasedOnAStructureError(FDTDreamError):
    ...


class FDTDreamDuplicateFDTDRegionError(FDTDreamError):
    ...


class FDTDreamBasedOnAStructureError(FDTDreamError):
    ...


# endregion

# region Simulation Errors

class FDTDreamNoSimulationRegionError(FDTDreamError):
    ...

# endregion
