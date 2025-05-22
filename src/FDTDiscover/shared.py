from typing import Callable, TypeVar, Tuple
from typing import cast, Any, Optional, Union

from PyQt6.QtCore import QObject, pyqtSignal, QSettings
from typing_extensions import Protocol, TypeVarTuple, Unpack

# region QSettings definitions
# Company and app name for QSettings
COMPANY = "FDTDream"
APP = "FDTDiscover"

# Create a shared QSettings instance
SETTINGS = QSettings(COMPANY, APP)
# endregion

# region Protocol classes for pyqtSignals
Args = TypeVarTuple("Args")
T = TypeVar("T")


class SignalProtocol(Protocol[Unpack[Args]]):
    """
    Protocol that emulates a pyqtSignal object that emits one or multiple variables of specific types.
    NB! This is not the actual signal, just a type wrapper for type hinting.
    """
    def __call__(self) -> Tuple[Unpack[Args]]: ...
    def connect(self, slot: Callable) -> None: ...
    def disconnect(self, slot: Callable) -> None: ...
    def emit(self, *args: Unpack[Args]) -> None: ...


class SignalProtocolNone(Protocol):
    """
    Protocol that emulates a pyqtSignal object that emits nothing.
    NB! This is not the actual signal, just a type wrapper for type hinting.
    """
    def __call__(self) -> None: ...
    def connect(self, slot: Callable) -> None: ...
    def disconnect(self, slot: Callable) -> None: ...
    def emit(self) -> None: ...
# endregion


# region Metaclass for signal busses
class AutoSignalBusMeta(type(QObject)):
    def __new__(mcs, name, bases, namespace):
        cls = super().__new__(mcs, name, bases, namespace)

        # Gather annotations from the class and all bases
        annotations = {}
        for base in reversed(bases):
            annotations.update(getattr(base, '__annotations__', {}))
        annotations.update(namespace.get('__annotations__', {}))

        for key, signal in namespace.items():
            if key.startswith("_") and isinstance(signal, pyqtSignal):
                public_name = key[1:]
                expected_type = annotations.get(public_name)
                if expected_type is None:
                    continue

                def make_property(attr_name: str, typ: Any):
                    return property(lambda self: cast(typ, getattr(self, attr_name)))

                setattr(cls, public_name, make_property(key, expected_type))

        return cls
# endregion
