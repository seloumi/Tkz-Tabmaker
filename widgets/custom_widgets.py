"""Custom PyQt6 widgets for Tkz-Tabmaker table interface."""

import logging
from typing import Optional
from PyQt6.QtCore import Qt, QLocale, QTimer, QSize
from PyQt6.QtGui import QColor, QBrush, QFont, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QGridLayout,
    QLabel, QComboBox, QLineEdit, QSpacerItem, QSizePolicy,
    QDoubleSpinBox, QTableWidget, QTableWidgetItem, QStyledItemDelegate,
)

from constants import (
    DEFAULT_FONT_FAMILY, COMBO_TYPE_WIDTH, ROW_HEIGHT_SPIN_WIDTH,
    TKZ_VAR_ITEMS, SPLIT_SCENARIOS, GRID_LAYOUT_SPACING, GRID_LAYOUT_MARGINS,
    HATCH_OFFSET, HATCH_PEN_WIDTH, HATCH_COLOR, BORDER_PEN_WIDTH, BORDER_COLOR,
)
from utils import format_float, get_alignment_from_prefix
from .event_filters import SafeEventFilter, LineEditTooltipFilter

logger = logging.getLogger(__name__)


class CustomDoubleSpinBox(QDoubleSpinBox):
    """Custom double spin box with English locale and formatted display.
    
    Handles decimal input with English locale and removes trailing zeros.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize the spin box.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
        self.setStyleSheet("""
            QDoubleSpinBox {
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 2px;
                background-color: #ffffff;
                font-weight: bold;
            }
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
                width: 16px;
                border-left: 1px solid #cbd5e1;
            }
            QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {
                background-color: #e2e8f0;
            }
        """)
        logger.debug("CustomDoubleSpinBox initialized")

    def validate(self, text: str, pos: int) -> tuple:
        """Validate input text.
        
        Args:
            text: Text to validate
            pos: Cursor position
            
        Returns:
            Validation result tuple
        """
        text = text.replace(',', '.')
        return super().validate(text, pos)

    def textFromValue(self, value: float) -> str:
        """Convert value to display text with formatting.
        
        Args:
            value: Numeric value
            
        Returns:
            Formatted text
        """
        return format_float(value)


class RowHeightWidget(QWidget):
    """Widget for selecting row type and height in the table.
    
    Combines a type selector (TabLine/TabVar) with a height spin box.
    """

    def __init__(self, initial_value: float = 2.0, show_type_selector: bool = True,
                 default_type: str = "Line") -> None:
        """Initialize the row height widget.
        
        Args:
            initial_value: Initial height value
            show_type_selector: Whether to show type selector combo
            default_type: Default type ('Line' or 'Var')
        """
        super().__init__()
        layout = QGridLayout(self)
        layout.setContentsMargins(GRID_LAYOUT_MARGINS, 2, GRID_LAYOUT_MARGINS, 2)
        layout.setSpacing(GRID_LAYOUT_SPACING)

        self.type_combo: Optional[QComboBox] = None
        if show_type_selector:
            self.type_combo = QComboBox()
            self.type_combo.addItem("TabLine", "tkzTabLine")
            self.type_combo.addItem("TabVar", "tkzTabVar")
            self.type_combo.setFixedWidth(COMBO_TYPE_WIDTH)
            self.type_combo.setStyleSheet("""
                QComboBox {
                    border: 1px solid #e2e8f0;
                    border-radius: 6px;
                    padding: 2px 4px;
                    background-color: #f8fafc;
                    font-size: 11px;
                }
                QComboBox::drop-down { border: none; }
            """)
            if default_type == "Var":
                self.type_combo.setCurrentIndex(1)
            layout.addWidget(self.type_combo, 0, 0, Qt.AlignmentFlag.AlignCenter)
            self.type_combo.setAccessibleName("Row type selector")
            self.type_combo.setAccessibleDescription("Choose between TabLine and TabVar row types")
        else:
            spacer = QSpacerItem(COMBO_TYPE_WIDTH, 20, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)
            layout.addItem(spacer, 0, 0)

        self.spin = CustomDoubleSpinBox()
        self.spin.setRange(0.5, 10.0)
        self.spin.setSingleStep(0.5)
        self.spin.setDecimals(2)
        self.spin.setValue(float(initial_value))
        self.spin.setFixedWidth(ROW_HEIGHT_SPIN_WIDTH)
        self.spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.spin, 0, 1, Qt.AlignmentFlag.AlignCenter)
        self.spin.setAccessibleName("Row height")
        self.spin.setAccessibleDescription(f"Set row height ({initial_value})")

        self.arrow_label = QLabel("⇳")
        self.arrow_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.arrow_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #6366f1;")
        layout.addWidget(self.arrow_label, 0, 2, Qt.AlignmentFlag.AlignCenter)

        self.setStyleSheet("background-color: transparent; border: none;")
        logger.debug(f"RowHeightWidget initialized: value={initial_value}, show_selector={show_type_selector}")

    def value(self) -> float:
        """Get the selected height value.
        
        Returns:
            Height value
        """
        return self.spin.value()

    def row_type(self) -> str:
        """Get the selected row type.
        
        Returns:
            Row type identifier ('tkzTabLine', 'tkzTabVar', or 'tkzTabInit')
        """
        if self.type_combo:
            return self.type_combo.currentData()
        return "tkzTabInit"


class TkzVarCellWidget(QWidget):
    """Widget for entering TkzVar cell values with prefix selector.
    
    Handles single or dual-value entries depending on the selected prefix.
    """

    def __init__(self, default_prefix: str = "", default_text: str = "") -> None:
        """Initialize the TkzVar cell widget.
        
        Args:
            default_prefix: Default prefix selector
            default_text: Default cell value(s)
        """
        super().__init__()
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(GRID_LAYOUT_MARGINS, GRID_LAYOUT_MARGINS, GRID_LAYOUT_MARGINS, GRID_LAYOUT_MARGINS)
        self.main_layout.setSpacing(0)

        self.container_widget = QWidget()
        self.container_layout = QHBoxLayout(self.container_widget)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(GRID_LAYOUT_SPACING)

        self.container_widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.container_widget.setMinimumHeight(28)

        self.combo = QComboBox(self)
        self.combo.setFixedWidth(55)
        self.combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                padding: 2px;
                background-color: #f1f5f9;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                border: 1px solid #cbd5e1;
            }
        """)
        self.combo.setAccessibleName("TkzVar prefix selector")
        self.combo.setAccessibleDescription("Select the expression type and placement")

        for text in TKZ_VAR_ITEMS.keys():
            self.combo.addItem(text)

        self._filter = SafeEventFilter(self.combo, TKZ_VAR_ITEMS)
        self.combo.installEventFilter(self._filter)
        if self.combo.view():
            self.combo.view().installEventFilter(self._filter)
            self.combo.view().setMouseTracking(True)

        # Line edit styles
        line_edit_style = """
            QLineEdit { border: 1px solid #e2e8f0; border-radius: 6px; padding: 2px; background-color: #ffffff; }
            QLineEdit:focus { border: 1px solid #6366f1; }
        """

        self.line_edit = QLineEdit()
        self.line_edit.setPlaceholderText("Val 1")
        self.line_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.line_edit.setStyleSheet(line_edit_style)
        self.line_edit.setAccessibleName("Primary value input")

        self.line_edit_2 = QLineEdit()
        self.line_edit_2.setPlaceholderText("Val 2")
        self.line_edit_2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.line_edit_2.setStyleSheet(line_edit_style)
        self.line_edit_2.setVisible(False)
        self.line_edit_2.setAccessibleName("Secondary value input")

        self.container_layout.addWidget(self.combo)
        self.container_layout.addWidget(self.line_edit)
        self.container_layout.addWidget(self.line_edit_2)

        self.main_layout.addWidget(self.container_widget)
        self.setStyleSheet("background-color: transparent;")

        self.combo.currentTextChanged.connect(self.update_elements_alignment)

        # Populate initial data if provided
        if default_text:
            if " / " in default_text:
                parts = default_text.split(" / ")
                self.line_edit.setText(parts[0])
                if len(parts) > 1:
                    self.line_edit_2.setText(parts[1])
            else:
                self.line_edit.setText(default_text)

        if default_prefix:
            for i in range(self.combo.count()):
                if self.combo.itemText(i) == default_prefix:
                    self.combo.setCurrentIndex(i)
                    break
            else:
                for i in range(self.combo.count()):
                    if self.combo.itemText(i).startswith(default_prefix):
                        self.combo.setCurrentIndex(i)
                        break

        QTimer.singleShot(0, lambda: self.update_elements_alignment(self.combo.currentText()))
        logger.debug(f"TkzVarCellWidget initialized: prefix={default_prefix}, text={default_text}")

    def update_elements_alignment(self, text: str) -> None:
        """Update visibility and alignment based on selected prefix.
        
        Args:
            text: Currently selected prefix text
        """
        self.main_layout.removeWidget(self.container_widget)

        is_split = text in SPLIT_SCENARIOS

        if is_split:
            self.line_edit_2.setVisible(True)
            self.line_edit.setPlaceholderText("Left")
        else:
            self.line_edit_2.setVisible(False)
            self.line_edit.setPlaceholderText("Value")

        align_name = get_alignment_from_prefix(text)
        if align_name == 'top':
            align = Qt.AlignmentFlag.AlignTop
        elif align_name == 'bottom':
            align = Qt.AlignmentFlag.AlignBottom
        else:
            align = Qt.AlignmentFlag.AlignCenter

        self.main_layout.addWidget(self.container_widget, alignment=align)
        self.container_widget.update()

    def get_tkz_value(self) -> str:
        """Get the formatted LaTeX value for this cell.
        
        Returns:
            Formatted value string for LaTeX
        """
        current_str = self.combo.currentText().strip()
        text1 = self.line_edit.text().strip()
        text2 = self.line_edit_2.text().strip() if self.line_edit_2.isVisible() else ""

        if current_str:
            if text2:
                return f"{current_str}/ {text1} / {text2}"
            elif text1:
                return f"{current_str}/ {text1}"
            else:
                return f"{current_str}/"
        return text1


class BorderAndHatchDelegate(QStyledItemDelegate):
    """Custom delegate for rendering table cells with borders and hatching.
    
    Handles drawing borders around cells and diagonal hatch patterns.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize the delegate.
        
        Args:
            parent: Parent widget (usually the table)
        """
        super().__init__(parent)
        self.nocadre_checkbox = None
        logger.debug("BorderAndHatchDelegate initialized")

    def paint(self, painter: QPainter, option, index) -> None:
        """Paint cell with borders and hatching.
        
        Args:
            painter: QPainter instance
            option: Style option
            index: Model index
        """
        super().paint(painter, option, index)
        rect = option.rect
        row = index.row()
        col = index.column()

        if col == 0:
            return

        table_widget = index.model()
        total_rows = table_widget.rowCount()
        total_cols = table_widget.columnCount()
        nocadre = self.nocadre_checkbox.isChecked() if self.nocadre_checkbox else False

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw hatch pattern if enabled
        is_hatched = index.data(Qt.ItemDataRole.UserRole)
        if is_hatched:
            hatch_pen = QPen(QColor(*HATCH_COLOR), HATCH_PEN_WIDTH, Qt.PenStyle.SolidLine)
            painter.setPen(hatch_pen)
            offset = HATCH_OFFSET
            for i in range(-rect.height(), rect.width() + rect.height(), offset):
                x1 = rect.left() + i
                y1 = rect.top()
                x2 = rect.left() + i + rect.height()
                y2 = rect.bottom()
                if x1 < rect.left():
                    y1 = rect.top() + (rect.left() - x1)
                    x1 = rect.left()
                if x2 > rect.right():
                    y2 = rect.bottom() - (x2 - rect.right())
                    x2 = rect.right()
                if y1 <= rect.bottom() and y2 >= rect.top() and x1 <= rect.right() and x2 >= rect.left():
                    painter.drawLine(int(x1), int(y1), int(x2), int(y2))

        # Draw borders
        border_pen = QPen(QColor(*BORDER_COLOR), BORDER_PEN_WIDTH, Qt.PenStyle.SolidLine)
        painter.setPen(border_pen)

        if row == 0:
            if not nocadre:
                painter.drawLine(rect.left(), rect.top(), rect.right(), rect.top())
        else:
            painter.drawLine(rect.left(), rect.top(), rect.right(), rect.top())

        if row == total_rows - 1:
            if not nocadre:
                painter.drawLine(rect.left(), rect.bottom(), rect.right(), rect.bottom())
        else:
            painter.drawLine(rect.left(), rect.bottom(), rect.right(), rect.bottom())

        if col == 1:
            if not nocadre:
                painter.drawLine(rect.left(), rect.top(), rect.left(), rect.bottom())

        if col == 1:
            painter.drawLine(rect.right(), rect.top(), rect.right(), rect.bottom())

        if col == total_cols - 1:
            if not nocadre:
                painter.drawLine(rect.right(), rect.top(), rect.right(), rect.bottom())

        painter.restore()
