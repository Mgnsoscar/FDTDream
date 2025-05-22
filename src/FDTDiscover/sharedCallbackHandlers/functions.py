import typing

import PyQt6.QtCore as Qc

from ..shared import SignalProtocol, SignalProtocolNone


def connectColorPreview(
    previewSignal: SignalProtocol[str],
    applyColor: typing.Callable[[str], None],
    canvasRedrawRequestedSignal: SignalProtocolNone,
    fpsLimit: int = 30
) -> None:
    """
    Connects a preview signal to a throttled update using QTimer.
    Applies color and emits redraw at most `fpsLimit` times per second.
    """
    timer = Qc.QTimer()
    timer.setSingleShot(True)
    timer.setInterval(int(1000 / fpsLimit))

    latestColor: dict[str, str] = {"value": ""}

    def handlePreview(previewColor: str):
        latestColor["value"] = previewColor
        if not timer.isActive():
            timer.start()

    def onTimeout():
        applyColor(latestColor["value"])
        canvasRedrawRequestedSignal.emit()

    timer.timeout.connect(onTimeout)
    previewSignal.connect(handlePreview)
