import typing

import PyQt6.QtWidgets as Qw
import PyQt6.QtCore as Qc
import PyQt6.QtGui as Qg
from ..shared import SignalProtocol
from ..sharedModels import TextSettingsState, TicksSettingsState, EditableTextSettingsState
from ..signal_busses import TextSettingsSignalBus, TickSettingsSignalBus


class EnabledCheckbox(Qw.QCheckBox):
    def __init__(self, enabledChangedSignal: SignalProtocol[bool], initialState: bool = None):
        super().__init__()
        self.setChecked(initialState if initialState is not None else True)
        self.clicked.connect(  # type: ignore
            enabledChangedSignal)


class TextInput(Qw.QLineEdit):
    def __init__(self, textChangedSignal: SignalProtocol[str], initialText: str = None):
        super().__init__(initialText)
        self.setText(initialText if initialText is not None else "")
        self.textChanged.connect(  # type: ignore
            textChangedSignal)


class FontSelectorWidget(Qw.QFontComboBox):
    def __init__(self, fontChangedSignal: SignalProtocol[str], initialFont: str = None):
        super().__init__()
        self.setFont(Qg.QFont(initialFont if initialFont is not None else "Arial"))
        self.setWheelEvent = lambda _: None
        self.currentFontChanged.connect(  # type: ignore
            lambda font: fontChangedSignal.emit(font.family()))


class FontSizeSpinBox(Qw.QSpinBox):
    def __init__(self, fontsizeChangedSignal: SignalProtocol[int], initialValue: int = None):
        super().__init__()
        self.setRange(0, 100)  # Set min and max values
        self.setSingleStep(1)  # Step size for arrows and key input
        self.setValue(int(initialValue) if initialValue is not None else 12)
        self.wheelEvent = lambda _: None
        self.valueChanged.connect(  # type: ignore
            fontsizeChangedSignal.emit)


class ColorPickerButton(Qw.QPushButton):

    colorPreviewRequestedSignal: SignalProtocol[str]
    colorChangedSignal: SignalProtocol[str]

    def __init__(self,
                 colorPreviewRequestedSignal: SignalProtocol[str],
                 colorChangedSignal: SignalProtocol[str],
                 initialColor: str = None):
        super().__init__("Choose Color")
        self.colorPreviewRequestedSignal = colorPreviewRequestedSignal
        self.colorChangedSignal = colorChangedSignal
        self._setButtonColor(Qg.QColor(initialColor) if initialColor is not None else Qg.QColor("black"))
        self.clicked.connect(  # type: ignore
            self.choose_color)

    @Qc.pyqtSlot()
    def choose_color(self):

        # Fetch the color prior to opening the color dialog.
        originalColor = self._get_button_color()

        # Open the color dialog
        dialog = Qw.QColorDialog(self)
        dialog.setOption(Qw.QColorDialog.ColorDialogOption.ShowAlphaChannel, False)
        dialog.setOption(Qw.QColorDialog.ColorDialogOption.DontUseNativeDialog, True)

        # Connect the color changed signal to the preview request
        dialog.currentColorChanged.connect(  # type: ignore
            lambda color: self.colorPreviewRequestedSignal.emit(color.name())
        )

        # Define the on-accept function
        def handleAccept():
            selectedColor = dialog.currentColor()
            if selectedColor.isValid():
                self._setButtonColor(selectedColor)
                self.colorChangedSignal.emit(selectedColor.name())

        # Define the on-reject function (reset to original color)
        def handleReject():
            selectedColor = originalColor
            if selectedColor.isValid():
                self._setButtonColor(selectedColor)
                self.colorChangedSignal.emit(selectedColor.name())

        # Link the accepted signal to the handleAccept function-
        dialog.accepted.connect(  # type: ignore
            handleAccept)
        dialog.rejected.connect(  # type: ignore
            handleReject)

        # Open the color dialog.
        dialog.exec()

    def _setButtonColor(self, color: Qg.QColor):
        brightness = color.red() * 0.299 + color.green() * 0.587 + color.blue() * 0.114
        text_color = "#000000" if brightness > 186 else "#ffffff"
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {color.name()};
                color: {text_color};
                border: 1px solid #555;
                padding: 4px;
            }}
        """)
        self.setText(color.name())

    def _get_button_color(self) -> Qg.QColor:
        try:
            return Qg.QColor(self.text())
        except Exception as e:
            Qw.QMessageBox.critical(
                self,
                "Color Error",
                f"Could not apply selected color, defaulting to black. Error message: {e}."
            )
            return Qg.QColor("#000000")


class LinkedSliderSpinbox(Qw.QWidget):
    """Reusable base class for float based slider widgets that connects to a valueChanged signal."""

    def __init__(
        self,
        *,
        signal: SignalProtocol[float],
        min_val: float,
        max_val: float,
        step: float,
        decimals: int,
        scale: float = 1.0,
        initial: typing.Optional[float] = None,
    ):
        super().__init__()
        layout = Qw.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Scale controls integer <-> float conversion
        self._scale = scale
        self._signal = signal

        # Slider
        self.slider = Qw.QSlider(Qc.Qt.Orientation.Horizontal)
        int_min = int(min_val / scale)
        int_max = int(max_val / scale)
        self.slider.setRange(int_min, int_max)
        self.slider.setSingleStep(max(1, int(step / scale)))
        self.slider.setFocusPolicy(Qc.Qt.FocusPolicy.NoFocus)
        self.slider.wheelEvent = lambda _: None

        # Spinbox
        self.spinbox = Qw.QDoubleSpinBox()
        self.spinbox.setRange(min_val, max_val)
        self.spinbox.setSingleStep(step)
        self.spinbox.setDecimals(decimals)
        self.spinbox.wheelEvent = lambda _: None

        # Add to layout
        layout.addWidget(self.slider)
        layout.addWidget(self.spinbox)

        layout.setStretch(0, 1)  # Slider expands
        layout.setStretch(1, 1)  # Spinbox keeps its minimum size

        # Initial value
        value = initial if initial is not None else min_val
        self.setValue(value)

        # Sync both ways
        self.slider.valueChanged.connect(  # type: ignore
            self._update_spinbox)
        self.spinbox.valueChanged.connect(  # type: ignore
            self._update_slider)
        self.spinbox.valueChanged.connect(  # type: ignore
            self._signal.emit)

    @Qc.pyqtSlot(int)
    def _update_spinbox(self, slider_value: int):
        self.spinbox.setValue(slider_value * self._scale)

    @Qc.pyqtSlot(float)
    def _update_slider(self, float_value: float):
        self.slider.setValue(int(round(float_value / self._scale)))

    def setValue(self, value: float):
        self._update_slider(value)
        self.spinbox.setValue(value)

    def value(self) -> float:
        return self.spinbox.value()


class AlphaControlWidget(LinkedSliderSpinbox):
    def __init__(self, alphaChangedSignal: SignalProtocol[float], initialValue: float = None):
        super().__init__(
            signal=alphaChangedSignal,
            min_val=0.0,
            max_val=1.0,
            step=0.01,
            decimals=2,
            scale=0.01,
            initial= initialValue if initialValue is not None else 1.
        )


class RotationControlWidget(LinkedSliderSpinbox):
    def __init__(self, rotationChangedSignal: SignalProtocol[float], initialValue: float = None):
        super().__init__(
            signal=rotationChangedSignal,
            min_val=-180.0,
            max_val=180.0,
            step=1.0,
            decimals=1,
            scale=1.0,
            initial=initialValue if initialValue is not None else 0.
        )


class TextSettings(Qw.QWidget):

    _signalBus: TextSettingsSignalBus
    _enabledCheckbox: EnabledCheckbox
    _fontSelector: FontSelectorWidget
    _fontsizeSpinbox: FontSizeSpinBox
    _colorButton: ColorPickerButton

    def __init__(self, signalBus: TextSettingsSignalBus):
        super().__init__()

        self.setSizePolicy(Qw.QSizePolicy.Policy.Preferred, Qw.QSizePolicy.Policy.Maximum)

        # Store the signal bus
        self._signalBus = signalBus

        # Connect the state granted method and emit the state request
        signalBus.initialStateGranted.connect(self._onInitialStateGranted)
        signalBus.initialStateRequested.emit()

    @Qc.pyqtSlot(object)
    def _onInitialStateGranted(self, state: TextSettingsState) -> None:
        # Create layout
        layout = Qw.QFormLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self._enabledCheckbox = EnabledCheckbox(self._signalBus.enabledChanged, initialState=state["enabled"])
        layout.addRow("Enabled:", self._enabledCheckbox)

        self._fontSelector = FontSelectorWidget(self._signalBus.fontChanged, initialFont=state["font"])
        layout.addRow("Font:", self._fontSelector)

        self._fontsizeSpinbox = FontSizeSpinBox(self._signalBus.fontsizeChanged, initialValue=state["fontSize"])
        layout.addRow("Font Size:", self._fontsizeSpinbox)

        self._colorButton = ColorPickerButton(
            self._signalBus.fontColorPreviewRequested, self._signalBus.fontColorChanged, initialColor=state["fontColor"]
        )
        layout.addRow("Color:", self._colorButton)


class EditableTextSettings(TextSettings):

    _textInput: TextInput
    _alphaControl: AlphaControlWidget

    @Qc.pyqtSlot(object)
    def _onInitialStateGranted(self, state: EditableTextSettingsState) -> None:
        super()._onInitialStateGranted(state)
        layout = typing.cast(Qw.QFormLayout, self.layout())
        self._textInput = TextInput(self._signalBus.textChanged, initialText=state["text"])
        layout.insertRow(0, "Text:", self._textInput)
        self._alphaControl = AlphaControlWidget(self._signalBus.fontAlphaChanged, initialValue=state["alpha"])
        layout.addRow("Alpha:", self._alphaControl)


class TickSettings(TextSettings):

    _signalBus: TickSettingsSignalBus

    def __init__(self, signalBus: TickSettingsSignalBus):
        super().__init__(signalBus)

    @Qc.pyqtSlot(object)
    def _onInitialStateGranted(self, state: TicksSettingsState) -> None:
        super()._onInitialStateGranted(state)
        layout = typing.cast(Qw.QFormLayout, self.layout())
        layout.addRow("Rotation:",
                      RotationControlWidget(self._signalBus.rotationChanged, initialValue=state["rotation"])
                      )


class PlotSettings(Qw.QToolBox):

    def __init__(self,
                 *,
                 titleSignalBus: TextSettingsSignalBus,
                 xlabelSignalBus: TextSettingsSignalBus,
                 ylabelSignalBus: TextSettingsSignalBus,
                 xticksSignalBus: TickSettingsSignalBus,
                 yticksSignalBus: TickSettingsSignalBus
                 ):
        super().__init__()

        self.addItem(EditableTextSettings(titleSignalBus), "Title")
        self.addItem(EditableTextSettings(xlabelSignalBus), "X Label")
        self.addItem(EditableTextSettings(ylabelSignalBus), "Y Label")
        self.addItem(TickSettings(xticksSignalBus), "X Ticks")
        self.addItem(TickSettings(yticksSignalBus), "Y Ticks")
