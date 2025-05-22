import PyQt6.QtCore as Qc
import typing
import PyQt6.QtWidgets as Qw
import matplotlib.text
from matplotlib.text import Text
from matplotlib.axis import XAxis, YAxis, Axis
from ..signal_busses import TextSettingsSignalBus, TickSettingsSignalBus
from . import functions
from ..shared import SignalProtocolNone
from ..sharedModels import EditableTextSettingsState, TicksSettingsState


class PlotSettingsCallbackHandler(Qc.QObject):

    _canvasRedrawRequested: SignalProtocolNone

    def __init__(
        self,
        canvasRedrawRequested: SignalProtocolNone,
        title: Text, titleSignalBus: TextSettingsSignalBus,
        xlabel: Text, xlabelSignalBus: TextSettingsSignalBus,
        ylabel: Text, ylabelSignalBus: TextSettingsSignalBus,
        xaxis: XAxis, xticksSignalBus: TickSettingsSignalBus,
        yaxis: YAxis, yticksSignalBus: TickSettingsSignalBus
    ):
        super().__init__()

        self._canvasRedrawRequested = canvasRedrawRequested

        self._connectTextSettings(title, titleSignalBus)
        self._connectTextSettings(xlabel, xlabelSignalBus)
        self._connectTextSettings(ylabel, ylabelSignalBus)

        self._connectTickSettings(xaxis, xticksSignalBus)
        self._connectTickSettings(yaxis, yticksSignalBus)

    def _connectTextSettings(self, textArtist: Text, textSignalBus: TextSettingsSignalBus) -> None:
        textSignalBus.initialStateRequested.connect(
            lambda: self._onInitialTextStateRequested(textArtist, textSignalBus))
        textSignalBus.textChanged.connect(lambda text: self._applyAndRedraw(lambda: textArtist.set_text(text)))
        textSignalBus.fontChanged.connect(lambda font: self._applyAndRedraw(lambda: textArtist.set_fontname(font)))
        textSignalBus.fontsizeChanged.connect(lambda size: self._applyAndRedraw(
            lambda: textArtist.set_fontsize(size)))
        textSignalBus.enabledChanged.connect(
            lambda visible: self._applyAndRedraw(lambda: textArtist.set_visible(visible)))

        # Preview color is throttled
        functions.connectColorPreview(
            previewSignal=textSignalBus.fontColorPreviewRequested,
            applyColor=textArtist.set_color,
            canvasRedrawRequestedSignal=self._canvasRedrawRequested
        )

        # Final color change is immediate
        textSignalBus.fontColorChanged.connect(lambda color: self._applyAndRedraw(lambda: textArtist.set_color(color)))

        textSignalBus.fontAlphaChanged.connect(lambda alpha: self._applyAndRedraw(lambda: textArtist.set_alpha(alpha)))

    def _connectTickSettings(self, axisObject: Axis, tickSignalBus: TickSettingsSignalBus) -> None:
        tickSignalBus.initialStateRequested.connect(
            lambda: self._onInitialTickStateRequested(axisObject, tickSignalBus))

        tickSignalBus.enabledChanged.connect(
            lambda enabled: self._applyAndRedraw(lambda: axisObject.set_tick_params(labelbottom=enabled))
        )
        tickSignalBus.rotationChanged.connect(
            lambda angle: self._applyAndRedraw(lambda: axisObject.set_tick_params(labelrotation=angle))
        )
        tickSignalBus.fontChanged.connect(
            lambda fontsize: self._applyAndRedraw(lambda: axisObject.set_tick_params(labelfontfamily=fontsize))
        )
        tickSignalBus.fontsizeChanged.connect(
            lambda size: self._applyAndRedraw(lambda: axisObject.set_tick_params(labelsize=size))
        )
        tickSignalBus.fontColorChanged.connect(
            lambda color: self._applyAndRedraw(lambda: axisObject.set_tick_params(labelcolor=color))
        )

        # Throttled preview
        functions.connectColorPreview(
            previewSignal=tickSignalBus.fontColorPreviewRequested,
            applyColor=lambda color: axisObject.set_tick_params(labelcolor=color),
            canvasRedrawRequestedSignal=self._canvasRedrawRequested
        )

    @Qc.pyqtSlot()
    def _onInitialTextStateRequested(self, textArtist: Text, signalBus: TextSettingsSignalBus) -> None:
        def compute():
            return EditableTextSettingsState(
                enabled=textArtist.get_visible(),
                font=textArtist.get_fontname(),
                fontSize=int(textArtist.get_fontsize()),
                fontColor=textArtist.get_color(),
                text=textArtist.get_text(),
                alpha=textArtist.get_alpha()
            )

        worker = StateWorker(compute)
        worker.signals.finished.connect(signalBus.initialStateGranted.emit)
        Qc.QThreadPool.globalInstance().start(worker)

    @Qc.pyqtSlot()
    def _onInitialTickStateRequested(self, axisObject: Axis, signalBus: TickSettingsSignalBus) -> None:
        def compute():
            ticklabels = axisObject.get_ticklabels()
            sampleLabel = ticklabels[0] if ticklabels else None
            tickParams = axisObject.get_tick_params()

            return TicksSettingsState(
                enabled=tickParams.get("labelbottom", True) if isinstance(axisObject, XAxis)
                else tickParams.get("labelleft", True),
                font=sampleLabel.get_fontfamily() if sampleLabel else "Arial",
                fontSize=sampleLabel.get_fontsize() if sampleLabel else 10,
                fontColor=sampleLabel.get_color() if sampleLabel else "#000000",
                rotation=tickParams.get("labelrotation", 0.0)
            )

        worker = StateWorker(compute)
        worker.signals.finished.connect(signalBus.initialStateGranted.emit)
        Qc.QThreadPool.globalInstance().start(worker)

    @Qc.pyqtSlot(object)
    def _applyAndRedraw(self, action: typing.Callable[[], None]) -> None:
        action()
        self._canvasRedrawRequested.emit()


class SignalEmitter(Qc.QObject):
    finished = Qc.pyqtSignal(object)


class StateWorker(Qc.QRunnable):
    def __init__(self, computeFunc: typing.Callable[[], typing.Any]):
        super().__init__()
        self.computeFunc = computeFunc
        self.signals = SignalEmitter()

    @Qc.pyqtSlot()
    def run(self):
        result = self.computeFunc()
        self.signals.finished.emit(result)