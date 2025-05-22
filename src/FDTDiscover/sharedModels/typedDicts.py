import typing


class TextSettingsState(typing.TypedDict):
    enabled: bool
    font: str
    fontSize: int
    fontColor: str


class EditableTextSettingsState(TextSettingsState):
    text: str
    alpha: float


class TicksSettingsState(TextSettingsState):
    rotation: float

