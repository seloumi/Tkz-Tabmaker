import sys
import os
import subprocess
import uuid
import tempfile
import math
from PyQt6.QtCore import Qt,QLocale, QTimer, QObject, QEvent, QPoint, QRect
from PyQt6.QtGui import QColor,QIcon , QFont, QPainter, QPen, QPixmap, QCursor, QKeySequence, QShortcut

from PyQt6.QtWidgets import (QApplication,QSizePolicy ,QSpacerItem,QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,QGraphicsDropShadowEffect,
                             QLabel,QSlider,QTableWidget, QTableWidgetItem, QHeaderView, 
                             QDoubleSpinBox, QCheckBox, QTextEdit, QPushButton, QMessageBox, 
                             QGroupBox, QColorDialog, QComboBox, QLineEdit,
                             QStyledItemDelegate, QToolTip)


def resource_path(relative_path):
    """ Get the absolute path to a resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

try:
    import fitz  # PyMuPDF
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

FONT_FAMILY = "Segoe UI" if sys.platform == "win32" else "Arial"


class MathLineEdit(QLineEdit):
    def focusInEvent(self, event):
        # When user clicks, ensure $ are there if not present
        text = self.text().strip()
        if text and not (text.startswith('$') and text.endswith('$')):
            self.setText(f"${text}$")
        elif not text:
            # Optional: Add them when field is empty to show math mode
            self.setText("$$")
            # Move cursor between the two $
            self.setCursorPosition(1)
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        # When user clicks away, clean up if empty
        text = self.text().strip()
        if text == "$$":
            self.setText("")
        super().focusOutEvent(event)



class AutoSizingLineEdit(MathLineEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.textChanged.connect(self.adjust_width_to_text)
        self.setPlaceholderText("")

    def adjust_width_to_text(self):
        fm = self.fontMetrics()
        text_width = fm.horizontalAdvance(self.text())
        padding = 16 
        min_width = 40
        calculated_width = max(text_width + padding, min_width)
        self.setFixedWidth(calculated_width)



# Use your existing AutoSizingLineEdit (which inherits from MathLineEdit) 
# for Math-mode rows, and a plain version for other rows.

class PlainAutoSizingLineEdit(AutoSizingLineEdit):
    # Override the focus events to do NOTHING (no $ wrapping)
    def focusInEvent(self, event):
        super(QLineEdit, self).focusInEvent(event)
    def focusOutEvent(self, event):
        super(QLineEdit, self).focusOutEvent(event)

# الفلتر الذكي لإظهار التلميحات بجانب الماوس مباشرة وبدون مشاكل
class SafeEventFilter(QObject):
    def __init__(self, combo_widget, tooltips_dict):
        super().__init__(combo_widget)
        self.combo = combo_widget
        self.tooltips = tooltips_dict

    def eventFilter(self, obj, event):
        if event.type() in [QEvent.Type.MouseMove, QEvent.Type.HoverMove, QEvent.Type.ToolTip]:
            view = self.combo.view()
            if view and view.isVisible():
                global_pos = QCursor.pos()
                local_pos = view.mapFromGlobal(global_pos)
                index = view.indexAt(local_pos)
                
                if index.isValid():
                    item_text = self.combo.itemText(index.row())
                    desc = self.tooltips.get(item_text, "")
                    if desc:
                        styled_tip = f"""
                        <div style='background-color: #1e293b; color: #f8fafc; border: 1px solid #475569; 
                                    padding: 6px 10px; border-radius: 6px; font-family: "{FONT_FAMILY}"; font-size: 12px;'>
                            <b style='color: #38bdf8;'>[{item_text}]:</b> {desc}
                        </div>
                        """
                        QToolTip.showText(global_pos + QPoint(15, 15), styled_tip, view)
            
            if event.type() == QEvent.Type.ToolTip:
                return True
            return False
        
        elif event.type() in [QEvent.Type.Leave, QEvent.Type.Hide, QEvent.Type.MouseButtonPress]:
            QToolTip.hideText()
            
        return super().eventFilter(obj, event)

class LineEditTooltipFilter(QObject):
    def __init__(self, line_edit, tooltips_dict):
        super().__init__(line_edit)
        self.line_edit = line_edit
        self.tooltips = tooltips_dict

    def eventFilter(self, obj, event):
        if event.type() in [QEvent.Type.MouseMove, QEvent.Type.ToolTip]:
            global_pos = QCursor.pos()
            local_pos = self.line_edit.mapFromGlobal(global_pos)
            
            fm = self.line_edit.fontMetrics()
            text = self.line_edit.text()
            
            content_x = local_pos.x() - self.line_edit.contentsMargins().left() - 2 
            
            char_idx = -1
            for i in range(len(text)):
                prefix_width = fm.horizontalAdvance(text[:i+1])
                if prefix_width >= content_x:
                    char_idx = i
                    break
            if char_idx == -1 and len(text) > 0:
                char_idx = len(text) - 1

            if char_idx >= 0 and char_idx < len(text):
                matched_key = None
                for key in self.tooltips.keys():
                    start = 0
                    while True:
                        idx = text.find(key, start)
                        if idx == -1:
                            break
                        if idx <= char_idx < (idx + len(key)):
                            matched_key = key
                            break
                        start = idx + 1
                    if matched_key:
                        break

                if matched_key:
                    desc = self.tooltips[matched_key]
                    styled_tip = f"""
                    <div style='background-color: #1e293b; color: #f8fafc; border: 1px solid #475569; 
                                padding: 6px 10px; border-radius: 6px; font-family: "{FONT_FAMILY}"; font-size: 12px;'>
                        <b style='color: #38bdf8;'>[{matched_key}]:</b> {desc}
                    </div>
                    """
                    QToolTip.showText(global_pos + QPoint(15, 15), styled_tip, self.line_edit)
                    return True
            
            QToolTip.hideText()
            return False
            
        elif event.type() in [QEvent.Type.Leave, QEvent.Type.FocusOut]:
            QToolTip.hideText()
            
        return super().eventFilter(obj, event)

class CustomDoubleSpinBox(QDoubleSpinBox):
    def __init__(self, parent=None):
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

    def validate(self, text, pos):
        text = text.replace(',', '.')
        return super().validate(text, pos)

    def textFromValue(self, value):
        if value == int(value):
            return str(int(value))
        return f"{value:.2f}".rstrip('0').rstrip('.')


class RowHeightWidget(QWidget):
    def __init__(self, initial_value=1.0, show_type_selector=True, default_type="Line"):
        super().__init__()
        # Use QVBoxLayout for easier vertical centering
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter) # Center vertically
        
    

        self.type_combo = None

        # Spinbox
        self.spin = CustomDoubleSpinBox()
        self.spin.setRange(0.5, 10.0)
        self.spin.setSingleStep(0.5) 
        self.spin.setDecimals(2)      
        self.spin.setValue(float(initial_value))
        self.spin.setFixedSize(45, 13)
        self.spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spin.setSuffix("cm")
        self.spin.setStyleSheet("""
            QDoubleSpinBox {
                border: 1px solid #cbd5e1;
                border-radius: 4px;
                padding: 0px;
                background-color: #ffffff;
                font-weight: bold;
                font-size: 10px;
            }
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
                width: 10px;
                border-left: 1px solid #cbd5e1;
            }
            QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {
                background-color: #e2e8f0;
            }
        """)
        layout.addWidget(self.spin, alignment=Qt.AlignmentFlag.AlignHCenter)
        
        # Spacer
        spacer = QWidget()
        spacer.setFixedSize(1, 5)
        layout.addWidget(spacer)
        
        # Combobox
        if show_type_selector:
            self.type_combo = QComboBox(self)
            self.type_combo.addItem("TabLine", "tkzTabLine")
            self.type_combo.addItem("TabVar", "tkzTabVar")
            self.type_combo.setFixedSize(45, 13)
            self.type_combo.setStyleSheet("""
                QComboBox {
                    border: 1px solid #e2e8f0;
                    border-radius: 4px;
                    padding: 1px 2px;
                    background-color: #f8fafc;
                    font-size: 9px;
                }
                QComboBox::drop-down { border: none; width: 10px; }
            """)
            if default_type == "Var":
                self.type_combo.setCurrentIndex(1)
            self.type_combo.currentIndexChanged.connect(self._on_type_changed)
            layout.addWidget(self.type_combo, alignment=Qt.AlignmentFlag.AlignHCenter)

         # Spacer
        spacer = QWidget()
        spacer.setFixedSize(1, 8)
        layout.addWidget(spacer) 
       
        self.setStyleSheet("background-color: transparent; border: none;")

    def _on_type_changed(self, index):
        if index == 1:
            self.spin.setValue(2.0)
        else:
            self.spin.setValue(1.0)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        pen = QPen(QColor("#F00707"), 2, Qt.PenStyle.SolidLine)
        #pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        
        h = self.height()
        margin = 1
        arrow_top = margin
        arrow_bottom = h - margin
        
        # Position X to the right of the spinbox (45px width)
        # Using a fixed X value relative to the widget width
        center_x = 66 
        
        # Draw central line
        painter.drawLine(center_x, arrow_top, center_x, arrow_bottom)
        
        # Draw arrow heads
        painter.drawLine(center_x, arrow_top, center_x - 4, arrow_top)
        painter.drawLine(center_x, arrow_top, center_x + 4, arrow_top)
        painter.drawLine(center_x, arrow_bottom, center_x - 4, arrow_bottom)
        painter.drawLine(center_x, arrow_bottom, center_x + 4, arrow_bottom)
          
        painter.end()

    def value(self):
        return self.spin.value()
        
    def row_type(self):
        if self.type_combo:
            return self.type_combo.currentData()
        return "tkzTabInit"

class CenteredComboBox(QComboBox):
    def showPopup(self):
        super().showPopup()
        popup = self.findChild(QWidget)
        if popup and popup.isVisible():
            rect = popup.geometry()
            global_center_x = self.mapToGlobal(QPoint(self.width() // 2, 0)).x()
            new_x = global_center_x - (rect.width() // 2)
            popup.move(new_x, rect.y())


class TkzVarCellWidget(QWidget):
    def __init__(self, is_math=True, default_prefix="", default_text=""):
        super().__init__()
            
        self.combo = CenteredComboBox(self)
        self.combo.setFixedSize(24, 10)       
        self.combo.setStyleSheet("""
            QComboBox { 
                border: 1px solid #ffffff; 
                border-radius: 6px; 
                background-color: #ef4444; 
            }
            QComboBox:hover { background-color: #dc2626; }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                border: 1px solid #cbd5e1;
                color: #334155;
                min-width: 100px;
            }
            QComboBox::item { padding: 4px 8px; min-height: 20px; }
            QComboBox::item:selected { background-color: #6366f1; color: #ffffff; }
        """)
        self.combo.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.items_tooltips = {
            "-": "Unique expression centered at the bottom",
            "+": "Unique expression centered at the top",
            "R": "Centered single expression",
            "-C": "Extension by continuity downwards, centered",
            "+C": "Extension by continuity at the top, centered",
            "-H": "Expression at the bottom and centered, then forbidden zone",
            "+H": "Expression at the top and centered, then forbidden zone",
            "-D": "Discontinuity, expression at the bottom left",
            "+D": "Discontinuity, expression at the top left",
            "D-": "Discontinuity, expression at the bottom right",
            "D+": "Discontinuity, expression at the upper right",
            "-DH": "Discontinuity on the left and at the bottom, then forbidden zone",
            "+DH": "Discontinuity on the left and at the top, then forbidden zone",
            "-CH": "Expression at the bottom left, extension by continuity then forbidden zone",
            "+CH": "Expression at the top left, extension by continuity then forbidden zone",
            "-D-": "Discontinuity, two expressions bottom left + bottom right",
            "-D+": "Discontinuity, two expressions bottom left + top right",
            "+D-": "Discontinuity, two expressions top left + bottom right",
            "+D+": "Discontinuity, two expressions top left + top right",
            "-CD-": "Extension by continuity to the bottom left plus value at the bottom right",
            "-CD+": "Extension by continuity to the bottom left plus value at the top right",
            "+CD-": "Extension by continuity to the top left plus value at the bottom right",
            "+CD+": "Extension by continuity to the top left plus value at the top right",
            "-DC-": "Value at bottom left plus Extension by continuity to the bottom right",
            "-DC+": "Value at bottom left plus Extension by continuity to the top right",
            "+DC-": "Value at top left plus Extension by continuity to the bottom right",
            "+DC+": "Value at top left plus Extension by continuity to the top right",
            "-V-":  "Like -D- but without a double bar",
            "-V+":  "Like -D+ but without a double bar",
            "+V-":  "Like +D- but without a double bar",
            "+V+":  "Like +D+ but without a double bar",
            "Text": "Custom text (No slash added)",
        }

        # Setup standard items filter/view
        for text in self.items_tooltips.keys():
            self.combo.addItem(text)
        self._filter = SafeEventFilter(self.combo, self.items_tooltips)
        self.combo.installEventFilter(self._filter)
        if self.combo.view():
            self.combo.view().installEventFilter(self._filter)
            self.combo.view().setMouseTracking(True)

        # Populate initially
        self.update_allowed_items(is_last_col=False)

        line_edit_style = """
            QLineEdit { border: 1px solid #e2e8f0; border-radius: 6px; padding: 2px; background-color: #ffffff; }
            QLineEdit:focus { border: 1px solid #6366f1; }
        """

        # Decide which class to use based on the row type
        LineEditClass = AutoSizingLineEdit if is_math else PlainAutoSizingLineEdit
        
        self.line_edit = LineEditClass(self)
        self.line_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.line_edit.setStyleSheet(line_edit_style)
        
        self.line_edit_2 = LineEditClass(self)
        self.line_edit_2.setVisible(False) 
        
        self.setStyleSheet("background-color: transparent;")
        
        self.line_edit.textChanged.connect(self.reposition_elements)
        self.line_edit_2.textChanged.connect(self.reposition_elements)
        self.combo.currentTextChanged.connect(self.update_elements_alignment)
        
        if default_text:
            if " / " in default_text:  
                parts = default_text.split(" / ")
                self.line_edit.setText(parts[0])
                if len(parts) > 1:
                    self.line_edit_2.setText(parts[1])
            else:
                self.line_edit.setText(default_text)

        if default_prefix:
            self.set_prefix_safely(default_prefix)

        # Inside TkzVarCellWidget.__init__
        self.line_edit.returnPressed.connect(self.clear_focus_on_enter)

        # Only if you have a second line edit
        if hasattr(self, 'line_edit_2'):
            self.line_edit_2.returnPressed.connect(self.clear_focus_on_enter)


        QTimer.singleShot(0, lambda: self.update_elements_alignment(self.combo.currentText()))
        # Add a method to lock inputs
        self.set_editable(True)

    def clear_focus_on_enter(self):
        """Clears focus from the widget to 'commit' the edit."""
        focused = self.focusWidget()
        if focused is not None:
            focused.clearFocus()
        # Optionally, give focus to the main window or the table itself
        parent = self.parent()
        if parent is not None:
            parent.setFocus()

    def set_editable(self, state):
        self.line_edit.setReadOnly(not state)
        if hasattr(self, 'line_edit_2'):
            self.line_edit_2.setReadOnly(not state)    

    def update_allowed_items(self, is_last_col):
        """Forces the combo box to rebuild its items list."""
        self.combo.blockSignals(True)
        current_selection = self.combo.currentText()
        
        self.combo.clear()
        
        for text in self.items_tooltips.keys():
            self.combo.addItem(text)
            
        # Restore selection if possible, otherwise reset
        index = self.combo.findText(current_selection)
        if index != -1:
            self.combo.setCurrentIndex(index)
        else:
            self.combo.setCurrentIndex(0)
            
        self.combo.blockSignals(False)

    def set_prefix_safely(self, prefix):
        found = False
        for i in range(self.combo.count()):
            if self.combo.itemText(i) == prefix:
                self.combo.setCurrentIndex(i)
                found = True
                break
        if not found:
            for i in range(self.combo.count()):
                if self.combo.itemText(i).startswith(prefix):
                    self.combo.setCurrentIndex(i)
                    break

    def update_dot_position(self):
        self.reposition_elements()
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_dot_position()

    def showEvent(self, event):
        super().showEvent(event)
        
        # Check parent dynamically on visibility show to see if we are sitting in the last column
        parent = self.parent()
        while parent and not isinstance(parent, QTableWidget):
            parent = parent.parent()
        if parent:
            for r in range(parent.rowCount()):
                for c in range(parent.columnCount()):
                    if parent.cellWidget(r, c) is self:
                        self.update_allowed_items(is_last_col=(c == parent.columnCount() - 1))
                        break

        QTimer.singleShot(0, self.update_dot_position)
        QTimer.singleShot(0, self.reposition_elements)

    def paintEvent(self, event):
        super().paintEvent(event)
        current_text = self.combo.currentText()
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if 'D' in current_text or 'C' in current_text:
            pen = QPen(QColor("#1f2224"), 1, Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            center_x = self.width() // 2
            painter.drawLine(center_x - 2, 0, center_x - 2, self.height())
            painter.drawLine(center_x + 2, 0, center_x + 2, self.height())

    def update_elements_alignment(self, text):
        # "Text" mode requires the input field to be visible
        self.line_edit.setVisible(True)
        is_split = text in [
            "-D-", "-D+", "+D-", "+D+",
            "-CD-", "-CD+", "+CD-", "+CD+",
            "-DC-", "-DC+", "+DC-", "+DC+",
            "-V-", "-V+", "+V-", "+V+"
        ]
        
        self.line_edit_2.setVisible(is_split)
        
        self.reposition_elements()
        QTimer.singleShot(0, self.update_dot_position)

        parent = self.parent()
        while parent and not isinstance(parent, QTableWidget):
            parent = parent.parent()
            
        if parent:
            target_row, target_col = -1, -1
            for r in range(parent.rowCount()):
                for c in range(parent.columnCount()):
                    if parent.cellWidget(r, c) is self:
                        target_row, target_col = r, c
                        break
                if target_row != -1:
                    break
            
            if target_row != -1 and target_col + 1 < parent.columnCount():
                next_col = target_col + 1
                parent.blockSignals(True)
                for r in range(1, parent.rowCount()):
                    item = parent.item(r, next_col)
                    if not item:
                        item = QTableWidgetItem("")
                        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        parent.setItem(r, next_col, item)
                    
                    widget = parent.cellWidget(r, next_col)
                    if 'H' in text:
                        item.setData(Qt.ItemDataRole.UserRole, True)
                        item.setText("")
                        if widget:
                            widget.setVisible(False)
                    else:
                        if item.data(Qt.ItemDataRole.UserRole) is True:
                            item.setData(Qt.ItemDataRole.UserRole, False)
                            item.setText("")
                            if widget:
                                widget.setVisible(True)
                                
                parent.blockSignals(False)
                parent.viewport().update()
            
    

            parent.viewport().update()

        if text == "R":
            self.line_edit.setVisible(False)
        else:
            self.line_edit.setVisible(True)       

    def reposition_elements(self):
        """Adjusts the layout based on whether the left neighbor is hatched."""
        # Get parent table and current coordinates
        parent_table = self.parent()
        # Find the actual QTableWidget
        while parent_table and not isinstance(parent_table, QTableWidget):
            parent_table = parent_table.parent()
            
        index = parent_table.indexAt(self.pos()) if parent_table else None
        
        # Check if the cell to the left is hatched
        is_left_hatched = False
        if index and index.column() > 0:
            left_item = parent_table.item(index.row(), index.column() - 1)
            if left_item and left_item.data(Qt.ItemDataRole.UserRole) is True:
                is_left_hatched = True
        
        # Define base offset
        offset = 30 if is_left_hatched else 0
        
        # Apply offset to line edits
        # Assuming you use a layout, you might need to adjust margins or fixed positions
        self.line_edit.setGeometry(10 + offset, 5, self.width() - 20 - offset, 20)
        if self.line_edit_2.isVisible():
            self.line_edit_2.setGeometry(10 + offset, 30, self.width() - 20 - offset, 20)

        w = self.width()
        h = self.height()
        dot_w, dot_h = 24, 8
        self.combo.setGeometry((w - dot_w) // 2, -2, dot_w, dot_h)
        text = self.combo.currentText()
        mid = w // 2
        
        box_w = min(50, mid - 10)
        box_h = 24

        if self.line_edit_2.isVisible():
            left_y = (h - box_h) // 2
            right_y = (h - box_h) // 2
            
            if text in ["-D-", "-V-"]:
                left_y, right_y = h - box_h - 2, h - box_h - 2
            elif text in ["-D+", "-V+"]:
                left_y, right_y = h - box_h - 2, 10
            elif text in ["+D-", "+V-"]:
                left_y, right_y = 10, h - box_h - 2
            elif text in ["+D+", "+V+"]:
                left_y, right_y = 10, 10
            elif text in ["-CD-", "-DC-"]:
                left_y, right_y = h - box_h - 2, h - box_h - 2
            elif text in ["-CD+", "-DC+"]:
                left_y, right_y = h - box_h - 2, 10
            elif text in ["+CD-", "+DC-"]:
                left_y, right_y = 10, h - box_h - 2
            elif text in ["+CD+", "+DC+"]:
                left_y, right_y = 10, 10
                
            self.line_edit.setGeometry(15, left_y, mid - 10, box_h)
            self.line_edit_2.setGeometry(mid + 15, right_y, mid - 10, box_h)
            
        else:
            if text in ["-", "-C", "-H"]:
                self.line_edit.setGeometry((w - 50) // 2, h - box_h - 2, 50, box_h)
            elif text in ["+", "+C", "+H"]:
                self.line_edit.setGeometry((w - 50) // 2, 10, 50, box_h)
            elif text == "R":
                self.line_edit.setGeometry((w - 50) // 2, (h - box_h) // 2, 50, box_h)
            elif text in ["-CH"]:
                self.line_edit.setGeometry(mid - (box_w // 2), h - box_h - 2, box_w, box_h)
            elif text in ["+CH"]:
                self.line_edit.setGeometry(mid - (box_w // 2), 10, box_w, box_h)
            elif text in ["-D", "-DH"]:
                self.line_edit.setGeometry(15, h - box_h - 2, mid - 15, box_h)
            elif text in ["+D", "+DH"]:
                self.line_edit.setGeometry(15, 10, mid - 15, box_h)
            elif text == "D-":
                self.line_edit.setGeometry(mid + 15, h - box_h - 2, mid - 15, box_h)
            elif text == "D+":
                self.line_edit.setGeometry(mid + 15, 10, mid - 15, box_h)
            else:
                self.line_edit.setGeometry((w - 50) // 2, (h - box_h) // 2, 50, box_h)
        
        parent = self.parent()
        while parent and not isinstance(parent, QTableWidget):
            parent = parent.parent()
        if parent:
            parent.viewport().update()
            
    def get_tkz_value(self):
        """Constructs the LaTeX string segment."""
        current_str = self.combo.currentText().strip()
        text1 = self.line_edit.text().strip()
        text2 = self.line_edit_2.text().strip() if self.line_edit_2.isVisible() else ""
        
        # 1. Custom "Text" choice: Return only the user input, no slash
        if current_str == "Text":
            return text1 
            
        # 2. Standard choices (with slash logic)
        if not text1 and not text2:
            return current_str
            
        if text2:
            return f"{current_str}/ {text1} / {text2}"
        else:
            return f"{current_str}/ {text1}"
        
class BorderAndHatchDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.nocadre_checkbox = None

    def paint(self, painter, option, index):
        
        rect = option.rect
        row = index.row()
        col = index.column()
        
        #1. Custom drawing for Column 0
        if index.column() == 0:
            painter.save()
            # Draw only background or custom content here, but NO border lines
            painter.fillRect(rect, QColor("#e8edf5"))
            painter.restore()
            
            # Now draw your dashed line at the bottom of column 0
            painter.save()
            painter.setPen(QPen(QColor("#252629"), 1, Qt.PenStyle.DashLine))
            painter.drawLine(rect.left(), rect.bottom(), rect.right(), rect.bottom())
            painter.restore()
            return # Skip the default border drawing for this column

        # 2. Default drawing for other columns
        super().paint(painter, option, index)

      
        table_widget = index.model()
        total_rows = table_widget.rowCount()
        total_cols = table_widget.columnCount()
        nocadre = self.nocadre_checkbox.isChecked() if self.nocadre_checkbox else False

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        is_interval_hatched = index.data(Qt.ItemDataRole.UserRole) is True
        
        is_current_value_col = (col > 1 and col % 2 == 0)
        is_left_neighbor_hatched = False
        is_right_neighbor_hatched = False

        if is_current_value_col:
            left_index = table_widget.index(row, col - 1)
            if left_index.isValid() and left_index.data(Qt.ItemDataRole.UserRole) is True:
                is_left_neighbor_hatched = True
            
            if col + 1 < total_cols:
                right_index = table_widget.index(row, col + 1)
                if right_index.isValid() and right_index.data(Qt.ItemDataRole.UserRole) is True:
                    is_right_neighbor_hatched = True

        if is_interval_hatched or is_left_neighbor_hatched or is_right_neighbor_hatched:
            hatch_pen = QPen(QColor(164, 174, 188), 1.5, Qt.PenStyle.SolidLine)
            painter.setPen(hatch_pen)
            offset = 8  
            
            if is_interval_hatched:
                target_rect = rect
            elif is_left_neighbor_hatched:
                target_rect = QRect(rect.left(), rect.top(), rect.width() // 2, rect.height())
            elif is_right_neighbor_hatched:
                target_rect = QRect(rect.left() + rect.width() // 2, rect.top(), rect.width() // 2, rect.height())
            else:
                target_rect = rect  # Fallback (should not normally happen)

            for i in range(-target_rect.height(), target_rect.width() + target_rect.height(), offset):
                x1 = target_rect.left() + i
                y1 = target_rect.top()
                x2 = target_rect.left() + i + target_rect.height()
                y2 = target_rect.bottom()
                
                if x1 < target_rect.left():
                    y1 = target_rect.top() + (target_rect.left() - x1)
                    x1 = target_rect.left()
                if x2 > target_rect.right():
                    y2 = target_rect.bottom() - (x2 - target_rect.right())
                    x2 = target_rect.right()
                    
                if y1 <= target_rect.bottom() and y2 >= target_rect.top() and x1 <= target_rect.right() and x2 >= target_rect.left():
                    painter.drawLine(int(x1), int(y1), int(x2), int(y2))

        border_pen = QPen(QColor(0, 0, 0), 2, Qt.PenStyle.SolidLine)
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


class PreviewWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Live Table Preview")
        self.setStyleSheet(f"QWidget {{ background-color: #ffffff; color: #334155; font-family: '{FONT_FAMILY}'; }}")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        self.btn_save = QPushButton("Save as PNG")
        self.btn_save.clicked.connect(self.save_as_png)
        self.btn_save.setStyleSheet("""
            QPushButton { font-weight: bold; 
                font-size: 13px; 
                padding: 10px 16px; 
                background-color: #4f46e5;
                color: white; 
                border: none; 
                border-radius: 8px; 
                min-width: 175px;
            }
                QPushButton:hover { background-color: #4338ca; }
        """)
        layout.addWidget(self.btn_save)

        self.preview_label = QLabel("Compiling LaTeX...")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setWordWrap(True)
        self.preview_label.setStyleSheet("color: #94a3b8; font-style: italic; background-color: #ffffff; padding: 10px;")
        
        layout.addWidget(self.preview_label)

    def save_as_png(self):
        # Trigger file dialog to pick where to save
        from PyQt6.QtWidgets import QFileDialog
        
        pixmap = self.preview_label.pixmap()
        if pixmap and not pixmap.isNull():
            file_path, _ = QFileDialog.getSaveFileName(self, "Save Table as PNG", "", "PNG Files (*.png)")
            if file_path:
                pixmap.save(file_path, "PNG")
                QMessageBox.information(self, "Success", "Image saved successfully!")


    def set_status_text(self, text):
        self.preview_label.setPixmap(QPixmap())
        self.preview_label.setText(text)
        self.preview_label.setStyleSheet("color: #94a3b8; font-style: italic; background-color: #ffffff;")
        self.resize(350, 150)

    def show_pixmap(self, pixmap):
        self.preview_label.setPixmap(pixmap)
        self.preview_label.setStyleSheet("background-color: #ffffff; border: none;")
        self.preview_label.adjustSize()
        self.adjustSize()


class ArrowDrawingTableWidget(QTableWidget):
    """Custom Table Widget subclass responsible for rendering procedural variation arrows between cells."""
    def paintEvent(self, event):
        super().paintEvent(event)
        
        painter = QPainter(self.viewport())
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        arrow_pen = QPen(QColor("#6366f1"), 2.5, Qt.PenStyle.SolidLine)
        arrow_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(arrow_pen)
        
        for row in range(1, self.rowCount()):
            header_widget = self.cellWidget(row, 0)
            if not header_widget or header_widget.row_type() != "tkzTabVar":
                continue
                
            points_list = []
            
            for col in range(2, self.columnCount()):
                cell_widget = self.cellWidget(row, col)
                if not cell_widget or not isinstance(cell_widget, TkzVarCellWidget) or not cell_widget.isVisible():
                    continue
                    
                if cell_widget.line_edit_2.isVisible():
                    if cell_widget.line_edit.isVisible():
                        local_center = cell_widget.line_edit.geometry().center()
                        global_p = cell_widget.mapTo(self.viewport(), local_center)
                        points_list.append((global_p, col, 0)) # 0 = Left Edit
                    local_center = cell_widget.line_edit_2.geometry().center()
                    global_p = cell_widget.mapTo(self.viewport(), local_center)
                    points_list.append((global_p, col, 1)) # 1 = Right Edit
                else:
                    if cell_widget.line_edit.isVisible():
                        local_center = cell_widget.line_edit.geometry().center()
                        global_p = cell_widget.mapTo(self.viewport(), local_center)
                        points_list.append((global_p, col, 0))
            
            if len(points_list) >= 2:
                for i in range(len(points_list) - 1):
                    p_start, col_start, sub_start = points_list[i]
                    p_end, col_end, sub_end = points_list[i + 1]
                    
                    should_skip_segment = False
                    
                    # 1. FIXED HACHED ZONE CHECK: Only block if the STARTING column or strictly intermediate columns are hatched.
                    # We check up to col_end (exclusive) because col_end itself is the target landing value box.
                    for check_col in range(col_start, col_end):
                        item = self.item(row, check_col)
                        if item and item.data(Qt.ItemDataRole.UserRole) is True:
                            should_skip_segment = True
                            break
                    
                    # 2. Comprehensive Double Line 'D' Intersection Check
                    if not should_skip_segment:
                        # Case A: Left box to Right box inside the SAME column cell
                        if col_start == col_end and sub_start == 0 and sub_end == 1:
                            widget = self.cellWidget(row, col_start)
                            if widget and "D" in widget.combo.currentText():
                                should_skip_segment = True
                        
                        # Case B: Across different columns
                        elif col_start != col_end:
                            start_widget = self.cellWidget(row, col_start)
                            end_widget = self.cellWidget(row, col_end)
                            
                            start_text = start_widget.combo.currentText() if start_widget else ""
                            end_text = end_widget.combo.currentText() if end_widget else ""

                            # 1. منع الرسم إذا كانت البداية "D-" أو "+D"
                            # (لاحظ: السهم ينطلق من يمين الخط المزدوج في D+ و D-، لذا نحظر الخروج من حالات أخرى)
                            if start_text in ["-D", "+D"]:
                                should_skip_segment = True
                            
                            # 2. منع الرسم إذا كانت النهاية "D-" أو "D+"
                            # (القاعدة: السهم ينتهي يسار الخط المزدوج، لذا نحظر الدخول لهذه الحالات)
                            if not should_skip_segment:
                                if end_text in ["D-", "D+"]:
                                    should_skip_segment = True

                            # 3. التأكد من عدم المرور فوق أعمدة وسطية تحتوي على "D" 
                            # (وهو ما سيمنع السهم من العبور فوق خطوط مزدوجة في أعمدة بين البداية والنهاية)
                            if not should_skip_segment:
                                for check_col in range(col_start + 1, col_end):
                                    widget_between = self.cellWidget(row, check_col)
                                    if widget_between and "D" in widget_between.combo.currentText():
                                        should_skip_segment = True
                                        break
                                            
                    if should_skip_segment:
                        continue
                    
                    dx = p_end.x() - p_start.x()
                    dy = p_end.y() - p_start.y()
                    distance = math.hypot(dx, dy)
                    
                    trim_offset = 38 
                    
                    if distance > (trim_offset * 2):
                        start_x = p_start.x() + (dx / distance) * trim_offset
                        start_y = p_start.y() + (dy / distance) * trim_offset
                        end_x = p_end.x() - (dx / distance) * trim_offset
                        end_y = p_end.y() - (dy / distance) * trim_offset
                        
                        pt1 = QPoint(int(start_x), int(start_y))
                        pt2 = QPoint(int(end_x), int(end_y))
                        
                        painter.drawLine(pt1, pt2)
                        self.draw_arrow_head(painter, pt1, pt2)

    def draw_arrow_head(self, painter, start, end):
        painter.save()
        painter.setPen(QPen(QColor("#6366f1"), 2.5, Qt.PenStyle.SolidLine))
        angle = math.atan2(end.y() - start.y(), end.x() - start.x())
        arrow_len = 8
        
        x1 = end.x() - arrow_len * math.cos(angle - math.pi / 6)
        y1 = end.y() - arrow_len * math.sin(angle - math.pi / 6)
        x2 = end.x() - arrow_len * math.cos(angle + math.pi / 6)
        y2 = end.y() - arrow_len * math.sin(angle + math.pi / 6)
        
        painter.drawLine(end, QPoint(int(x1), int(y1)))
        painter.drawLine(end, QPoint(int(x2), int(y2)))
        painter.restore()


class TkzTabGridGenerator(QWidget):
    def __init__(self):
        super().__init__()
        self.colors = {
            "colorV": QColor("white"),  
            "colorL": QColor("white"),  
            "colorC": QColor("white"),  
            "colorT": QColor("white")   
        }
        
        self.undo_stack = []
        self.redo_stack = []
        self.is_undoing_redoing = False

        self.preview_window = PreviewWindow() 
        self.initUI()
        
        QTimer.singleShot(100, self.save_state)
        
    def initUI(self):
        self.setWindowTitle('Tkz-Tabmaker Table Generator Assistant')
        self.setFont(QFont(FONT_FAMILY, 10))
        
        self.setStyleSheet(f"""
            QWidget {{ background-color: #f8fafc; color: #334155; font-family: "{FONT_FAMILY}"; }}
            QLabel {{ color: #475569; font-weight: 500; }}
            QGroupBox {{ font-weight: bold; border: 1px solid #e2e8f0; border-radius: 12px; background-color: #ffffff; padding: 10px; }}
            QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 4px; color: #1e293b; }}
            QToolTip {{ background: transparent; border: none; padding: 0px;  }}
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        tikzset_group = QGroupBox("Custom Tikzset Styles (\\tikzset)")
        tikzset_layout = QHBoxLayout()  
        tikzset_layout.setSpacing(8)
        
        # Create the shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)           # Set blur radius for softness
        shadow.setOffset(0, 5)             # Set horizontal and vertical offset
        shadow.setColor(QColor(0, 0, 0, 150))  # Set shadow color and transparency

        tikzset_group.setGraphicsEffect(shadow)


        self.style_presets = {
            "Custom": "",
            "t style": "t style/.style = {style  = dotted, draw = \\tkzTabDefaultWritingColor}",
            "h style": "h style/.style = {pattern = north west lines, pattern color = \\tkzTabDefaultWritingColor}",
            "node style": "node style/.style = {inner sep = \\tkzTabDefaultSep, outer sep = \\tkzTabDefaultSep, fill = \\tkzTabDefaultBackgroundColor}",
            "arrow style": "arrow style/.style={\\tkzTabDefaultWritingColor, -> ,> = \\tkzTabDefaultArrowStyle, shorten > = \\tkzTabDefaultSep, shorten < = \\tkzTabDefaultSep}",
            "double style ": "double style/.append style = { draw = \\tkzTabDefaultWritingColor,double =  \\tkzTabDefaultBackgroundColor}"
        }
        
        self.styles_tooltips = {
            "\\tkzTabDefaultWritingColor":"black",
            "\\tkzTabDefaultBackgroundColor":"white",
            "\\tkzTabDefaultArrowStyle":"latex'",
            "\\tkzTabDefaultSep":"2pt",
        } 

        self.combo_presets = QComboBox()
        self.combo_presets.addItems(list(self.style_presets.keys()))
        self.combo_presets.setFixedWidth(110)
        self.combo_presets.setStyleSheet("""
            QComboBox {
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 5px;
                background-color: #f1f5f9;
            }
            QComboBox::drop-down { border: none; }
        """)
        
        self.txt_tikzset_content = QLineEdit("")
        self.txt_tikzset_content.setPlaceholderText("e.g., t style/.style = {style = densely dashed}, arrow style/.style={>=latex}")
        self.txt_tikzset_content.setStyleSheet("""
            QLineEdit {
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 6px;
                font-family: 'Consolas', monospace;
                font-size: 12px;
                background-color: #f8fafc;
            }
            QLineEdit:focus { border: 1px solid #6366f1; background-color: #ffffff; }
        """)
        
        self.txt_tikzset_content.setMouseTracking(True)
        self._line_edit_filter = LineEditTooltipFilter(self.txt_tikzset_content, self.styles_tooltips)
        self.txt_tikzset_content.installEventFilter(self._line_edit_filter)

        self.combo_presets.currentTextChanged.connect(self.on_preset_changed)
        
        tikzset_layout.addWidget(self.combo_presets)
        tikzset_layout.addWidget(self.txt_tikzset_content)
        tikzset_group.setLayout(tikzset_layout)
        main_layout.addWidget(tikzset_group)
        
        settings_group = QGroupBox("Table Options")
        settings_group.setStyleSheet("""
            QCheckBox { spacing: 6px; font-weight: 500; }
            QCheckBox::indicator { width: 16px; height: 16px; border-radius: 4px; border: 1px solid #cbd5e1; }
            QCheckBox::indicator:checked { background-color: #6366f1; border-color: #6366f1; }
        """)

        settings_group.setFixedHeight(60)

        settings_group.setGraphicsEffect(shadow)

        settings_layout = QHBoxLayout()
        settings_layout.setSpacing(10)

        settings_layout.addWidget(QLabel('lgt:'))
        self.spin_lgt = QDoubleSpinBox()
        self.spin_lgt.setRange(0.5, 5.0)
        self.spin_lgt.setSingleStep(0.5)
        self.spin_lgt.setValue(2.0)
        self.spin_lgt.setFixedWidth(75)
        settings_layout.addWidget(self.spin_lgt)
        
        settings_layout.addWidget(QLabel('deltacl:'))
        self.spin_deltacl = QDoubleSpinBox()
        self.spin_deltacl.setRange(0.4, 3.0)
        self.spin_deltacl.setSingleStep(0.1)
        self.spin_deltacl.setValue(0.5)  
        self.spin_deltacl.setFixedWidth(75)
        settings_layout.addWidget(self.spin_deltacl)
        
        settings_layout.addWidget(QLabel('espcl:'))
        self.spin_espcl = QDoubleSpinBox()
        self.spin_espcl.setRange(0.5, 5.0)
        self.spin_espcl.setSingleStep(0.5)
        self.spin_espcl.setValue(2.0)
        self.spin_espcl.setFixedWidth(75)
        settings_layout.addWidget(self.spin_espcl)
        
        self.chk_nocadre = QCheckBox("nocadre")
        settings_layout.addWidget(self.chk_nocadre)
        
        self.chk_help = QCheckBox("help")
        settings_layout.addWidget(self.chk_help)

        self.chk_color = QCheckBox("color")
        self.chk_color.stateChanged.connect(self.toggle_colors_visibility)
        settings_layout.addWidget(self.chk_color)
        
        settings_layout.addStretch(1)
        
        self.color_buttons = {}
        color_labels = {"colorV": "colorV:", "colorL": "colorL:", "colorC": "colorC:", "colorT": "colorT:"}
        for key, label_text in color_labels.items():
            lbl = QLabel(label_text)
            lbl.setVisible(False)
            settings_layout.addWidget(lbl)
            btn = QPushButton()
            btn.setFixedWidth(45)
            btn.setVisible(False)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, k=key: self.pick_color(k))
            settings_layout.addWidget(btn)
            self.color_buttons[key] = btn
        
        settings_layout.addStretch(2)


        self.btn_reset = QPushButton("Reset")
        self.btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reset.setStyleSheet("""
            QPushButton { font-weight: bold; font-size: 11px; padding: 4px 10px; background-color: #ef4444; color: white; border: none; border-radius: 6px; }
            QPushButton:hover { background-color: #dc2626; }
        """)
        self.btn_reset.clicked.connect(self.reset_to_default)
        settings_layout.addWidget(self.btn_reset)
        
        settings_layout.addStretch()
        settings_group.setLayout(settings_layout)
        main_layout.addWidget(settings_group)
        
        
        self.table = ArrowDrawingTableWidget()
       
        self.table.setRowCount(3)
        self.table.setColumnCount(7)
        self.table.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        
        self.table.setStyleSheet("""
            QTableWidget { background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 4px; }
            QTableWidget::item { padding: 4px; }
            QTableWidget::item:selected { background-color: #e0e7ff; color: #4338ca; }
        """)

              
        self.grid_delegate = BorderAndHatchDelegate(self.table)
        self.grid_delegate.nocadre_checkbox = self.chk_nocadre
        self.table.setItemDelegate(self.grid_delegate)
        
        self.chk_nocadre.stateChanged.connect(self.table.viewport().update)
        
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(0, 80) 
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.setShowGrid(False) 
        
        self.table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked | QTableWidget.EditTrigger.AnyKeyPressed)
        self.table.editTriggered = lambda index: False if (index.column() % 2 != 0 and index.column() > 1 and (index.row() == 0 or (self.table.cellWidget(index.row(), 0) and self.table.cellWidget(index.row(), 0).row_type() == "tkzTabVar"))) else True
        
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
                
        self.table.horizontalHeader().sectionResized.connect(lambda: self.table.viewport().update())
        self.table.verticalHeader().sectionResized.connect(lambda: self.table.viewport().update())
        self.table.horizontalScrollBar().valueChanged.connect(lambda: self.table.viewport().update())
        self.table.verticalScrollBar().valueChanged.connect(lambda: self.table.viewport().update())

        self.setup_initial_table()
        
        self.table.itemChanged.connect(self.safe_handle_item_changed)
        
        table_group = QGroupBox("Table")
        table_group.setStyleSheet("""
            QGroupBox { font-weight: bold; border: 1px solid #e2e8f0; border-radius: 12px; background-color: #ffffff; padding: 10px; }
            QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 4px; color: #1e293b; }
        """)
        
        # Create the shadow effect for the table group
        table_shadow = QGraphicsDropShadowEffect()
        table_shadow.setBlurRadius(15)
        table_shadow.setOffset(0, 5)
        table_shadow.setColor(QColor(0, 0, 0, 150))
        table_group.setGraphicsEffect(table_shadow)
        
        table_layout = QVBoxLayout(table_group)
        table_layout.setContentsMargins(5, 15, 5, 5)

        # Column slider above the table
        col_header_layout = QHBoxLayout()
        col_header_layout.addWidget(QLabel('Columns:'))
        self.col_slider = QSlider(Qt.Orientation.Horizontal)
        self.col_slider.setRange(4, 12)
        self.col_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.col_slider.setTickInterval(2)
        self.col_slider.setValue(6)
        self.col_slider.setFixedHeight(30)
        self.col_slider.valueChanged.connect(self.update_table_dimensions)
        self.col_value_label = QLabel(str(self.col_slider.value()))
        self.col_value_label.setFixedWidth(30)
        self.col_value_label.setStyleSheet("color: white;background-color: red;" \
         "font-weight: bold; font-size: 11px;")
        self.col_value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.col_slider.valueChanged.connect(lambda v: self.col_value_label.setText(str(v)))
        col_header_layout.addWidget(self.col_slider)
        col_header_layout.addWidget(self.col_value_label)
        table_layout.addLayout(col_header_layout)

        # Table with row slider to the left
        table_and_row_layout = QHBoxLayout()
        
        # Vertical row slider on the left
        row_slider_layout = QVBoxLayout()
        row_slider_layout.addWidget(QLabel('Rows:'))
        self.row_slider_vert = QSlider(Qt.Orientation.Vertical)
        self.row_slider_vert.setRange(1, 7)
        self.row_slider_vert.setTickPosition(QSlider.TickPosition.TicksRight)
        self.row_slider_vert.setTickInterval(1)
        self.row_slider_vert.setValue(3)
        self.row_slider_vert.valueChanged.connect(self.update_table_dimensions)
        self.row_slider_vert.setFixedWidth(40)
        self.row_slider_vert.setMinimumHeight(120)
        self.row_slider_vert.setInvertedAppearance(True)
        row_slider_layout.addWidget(self.row_slider_vert, alignment=Qt.AlignmentFlag.AlignCenter)
        self.row_vert_value_label = QLabel(str(self.row_slider_vert.value()))
        self.row_vert_value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.row_vert_value_label.setFixedWidth(40)
        self.row_vert_value_label.setStyleSheet("color: white;background-color: red;" \
           "font-weight: bold; font-size: 11px;")
        self.row_slider_vert.valueChanged.connect(lambda v: self.row_vert_value_label.setText(str(v)))
        row_slider_layout.addWidget(self.row_vert_value_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        table_and_row_layout.addLayout(row_slider_layout)
        table_and_row_layout.addWidget(self.table, stretch=1)
        table_layout.addLayout(table_and_row_layout)
        
        main_layout.addWidget(table_group)

        # --- PREVIEW & LATEX GENERATION REGION ---
        output_group = QGroupBox("Generated LaTeX Code")
        output_group.setStyleSheet(f"""
            QGroupBox {{ font-family: '{FONT_FAMILY}'; font-size: 14px; font-weight: bold; color: #1e293b; margin-top: 12px; shadow: 0 2px 4px rgba(0, 0, 0, 0.1); }}
            QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top left; padding: 0 5px; }}
        """)

        output_shadow = QGraphicsDropShadowEffect()
        output_shadow.setBlurRadius(15)
        output_shadow.setOffset(0, 5)
        output_shadow.setColor(QColor(0, 0, 0, 150))
        output_group.setGraphicsEffect(output_shadow)
        
        # main layout inside the group box is changed to Horizontal
        output_layout = QHBoxLayout()
        output_layout.setContentsMargins(10, 15, 10, 10)
        output_layout.setSpacing(15)

        # Left Column: The Code Block Box
        self.output_code = QTextEdit()
        self.output_code.setReadOnly(False)
        self.output_code.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.output_code.setPlaceholderText("\\begin{tikzpicture} code will appear here...")
        self.output_code.setFont(QFont("Consolas" if sys.platform == "win32" else "Courier", 11))
        self.output_code.setStyleSheet("""
            QTextEdit { 
                background-color: #1e1e2e; 
                color: #f8f8f2; 
                font-size: 11px;                       
                border: 1px solid #313244; 
                border-radius: 10px; 
                padding: 8px; 
            }
        """)
        output_layout.addWidget(self.output_code, stretch=4) # Stretch 4 gives more room to code window

        # Right Column: Side Action Panel for Buttons
        side_button_layout = QVBoxLayout()
        side_button_layout.setSpacing(10)
        side_button_layout.setAlignment(Qt.AlignmentFlag.AlignTop) # Keeps buttons grouped at the top right

        self.btn_generate = QPushButton('1. Generate LaTeX Code')
        self.btn_generate.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_generate.setStyleSheet("""
            QPushButton { 
                font-weight: bold; 
                font-size: 13px; 
                padding: 10px 16px; 
                background-color: #4f46e5; 
                color: white; 
                border: none; 
                border-radius: 8px; 
                min-width: 175px;
            }
            QPushButton:hover { background-color: #4338ca; }
        """)
        self.btn_generate.clicked.connect(self.generate_tkz_code)
        side_button_layout.addWidget(self.btn_generate)

        self.btn_preview = QPushButton('2. Compile & Preview')
        self.btn_preview.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_preview.setEnabled(False) 
        self.btn_preview.setStyleSheet("""
            QPushButton { 
                font-weight: bold; 
                font-size: 13px; 
                padding: 10px 16px; 
                background-color: #059669; 
                color: white; 
                border: none; 
                border-radius: 8px; 
                min-width: 175px;
            }
            QPushButton:hover { background-color: #047857; }
            QPushButton:disabled { background-color: #cbd5e1; color: #94a3b8; }
        """)
        self.btn_preview.clicked.connect(self.compile_and_preview_latex)
        side_button_layout.addWidget(self.btn_preview)

        self.btn_copy = QPushButton('Copy Code')
        self.btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy.setStyleSheet("""
            QPushButton { 
                font-weight: bold; 
                font-size: 13px; 
                padding: 10px 16px; 
                background-color: #ffffff; 
                color: #475569; 
                border: 1px solid #cbd5e1; 
                border-radius: 8px; 
                min-width: 175px;
            }
            QPushButton:hover { background-color: #f8fafc; color: #1e293b; }
        """)
        self.btn_copy.clicked.connect(self.copy_to_clipboard)
        side_button_layout.addWidget(self.btn_copy)
        
        # Add a flexible spacer to prevent buttons from stretching vertically
        side_button_layout.addStretch()

        # Add side controls to output frame layout
        output_layout.addLayout(side_button_layout, stretch=1)
        output_group.setLayout(output_layout)
        
        main_layout.addWidget(output_group, stretch=2)

        # ربط اختصارات الكيبورد الـ Undo والـ Redo
        self.undo_shortcut = QShortcut(QKeySequence("Ctrl+Z"), self)
        self.undo_shortcut.activated.connect(self.undo)
        
        self.redo_shortcut = QShortcut(QKeySequence("Ctrl+Y"), self)
        self.redo_shortcut.activated.connect(self.redo)

    def on_preset_changed(self, text):
        preset_value = self.style_presets.get(text, "")
        self.txt_tikzset_content.setText(preset_value)

    def save_state(self):
        if self.is_undoing_redoing: 
            return
        
        state = {
            "rows": self.table.rowCount(),
            "cols": self.table.columnCount(),
            "col_slider": self.col_slider.value(),
            "row_slider": self.row_slider_vert.value(),
            "data": []
        }
        
        for r in range(state["rows"]):
            row_data = []
            for c in range(state["cols"]):
                cell_info = {"type": "item", "text": "", "is_hatched": False, "widget_data": None}
                
                widget = self.table.cellWidget(r, c)
                if widget:
                    if isinstance(widget, RowHeightWidget):
                        cell_info["type"] = "RowHeightWidget"
                        cell_info["val"] = widget.value()
                        cell_info["row_type"] = widget.row_type()
                    elif isinstance(widget, TkzVarCellWidget):
                        cell_info["type"] = "TkzVarCellWidget"
                        cell_info["prefix"] = widget.combo.currentText()
                        cell_info["text"] = widget.line_edit.text()
                else:
                    item = self.table.item(r, c)
                    if item:
                        cell_info["text"] = item.text()
                        cell_info["is_hatched"] = item.data(Qt.ItemDataRole.UserRole) is True
                
                row_data.append(cell_info)
            state["data"].append(row_data)
            
        self.undo_stack.append(state)
        self.redo_stack.clear()

    def undo(self):
        if len(self.undo_stack) <= 1: 
            return
        state = self.undo_stack.pop()
        self.redo_stack.append(state)
        
        previous_state = self.undo_stack[-1]
        self.restore_state(previous_state)

    def redo(self):
        if not self.redo_stack: 
            return
        state = self.redo_stack.pop()
        self.undo_stack.append(state)
        self.restore_state(state)

    def restore_state(self, state):
        self.is_undoing_redoing = True
        self.table.blockSignals(True)
                
        self.col_slider.blockSignals(True)
        self.row_slider_vert.blockSignals(True)
        self.col_slider.setValue(state["col_slider"])
        self.row_slider_vert.setValue(state["row_slider"])
        self.col_slider.blockSignals(False)
        self.row_slider_vert.blockSignals(False)
        self.col_value_label.setText(str(state["col_slider"]))
        self.row_vert_value_label.setText(str(state["row_slider"]))
        
        self.table.setRowCount(state["rows"])
        self.table.setColumnCount(state["cols"])
        self.table.clear()
        
        for r in range(state["rows"]):
            for c in range(state["cols"]):
                info = state["data"][r][c]
                
                if info["type"] == "RowHeightWidget":
                    show_selector = (r != 0)
                    def_type = "Var" if info["row_type"] == "tkzTabVar" else "Line"
                    w = RowHeightWidget(info["val"], show_type_selector=show_selector, default_type=def_type)
                    if show_selector:
                        w.type_combo.currentIndexChanged.connect(lambda idx, row_idx=r: self.on_row_type_changed(idx, row_idx))
                    self.table.setCellWidget(r, c, w)
                    
                elif info["type"] == "TkzVarCellWidget":
                    w = TkzVarCellWidget(default_prefix=info["prefix"], default_text=info["text"])
                    #APPLY BLOCKING LOGIC HERE
                     # Block columns 3, 5, 7...
                    if r==0 and c % 2 != 0 and c > 1:
                        w.set_editable(False)
                    self.table.setCellWidget(r, c, w)
                    
                else:
                    item = QTableWidgetItem(info["text"])
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    if info["is_hatched"]:
                        item.setData(Qt.ItemDataRole.UserRole, True)
                    
                    if r == 0 and c % 2 != 0 and c > 1:
                        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                        
                    self.table.setItem(r, c, item)
                    
        self.table.blockSignals(False)
        self.is_undoing_redoing = False
        self.adjust_row_heights()
        self.table.viewport().update()
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.adjust_row_heights()

    # ============================================================
    # MODIFIED: Fixed row heights instead of proportional sizing
    # ============================================================
    def adjust_row_heights(self):
        for r in range(self.table.rowCount()):
            is_var = False
            # Check row type
            header_widget = self.table.cellWidget(r, 0)
            if header_widget and hasattr(header_widget, "row_type") and header_widget.row_type() == "tkzTabVar":
                is_var = True
            
            height = 95 if is_var else 35
            self.table.setRowHeight(r, height)
            
            # CRITICAL: Force the widget to fill the row perfectly
            widget = self.table.cellWidget(r, 0)
            if widget:
                # setGeometry is more reliable than setFixedSize for table cell widgets
                widget.setGeometry(self.table.columnViewportPosition(0), 
                                   self.table.rowViewportPosition(r), 
                                   self.table.columnWidth(0), 
                                   height)


    # ============================================================
    # END of fixed row heights modification
    # ============================================================

    def closeEvent(self, event):
        self.preview_window.close()
        super().closeEvent(event)

                
    
    def on_row_type_changed(self, index, row):
        header_widget = self.table.cellWidget(row, 0)
        if not header_widget:
            return
        
        self.save_state()
        selected_type = header_widget.row_type()
        col_count = self.table.columnCount()
        
        self.table.blockSignals(True)
        for c in range(2, col_count):
            if selected_type == "tkzTabVar":
                if self.table.cellWidget(row, c): 
                    self.table.removeCellWidget(row, c)
                
                if c % 2 != 0:
                    self.add_centered_item(row, c, "")
                else:
                    x_item = self.table.item(0, c)
                    if x_item and x_item.text().strip():
                        self.table.setCellWidget(row, c, TkzVarCellWidget(is_math=True, default_prefix="", default_text=""))
                    else:
                        self.add_centered_item(row, c, "")
            else:
                if self.table.cellWidget(row, c): 
                    self.table.removeCellWidget(row, c)
                self.add_centered_item(row, c, "")
        self.table.blockSignals(False)
        self.adjust_row_heights()
        self.table.viewport().update()

    def safe_handle_item_changed(self, item):
        QTimer.singleShot(50, lambda: self.process_item_changed(item))

    def process_item_changed(self, item):
        if self.is_undoing_redoing: 
            return
        self.save_state()
        try:
            row = item.row()
            col = item.column()
        except RuntimeError:
            return

        # Ensure text in row 0 value columns (even columns > 1) is centered
        if row == 0 and col >= 2 and col % 2 == 0:
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        self.table.blockSignals(True) 
        if row == 0 and col >= 2:
            text_value = item.text().strip()
            for r in range(1, self.table.rowCount()):
                header_widget = self.table.cellWidget(r, 0)
                if header_widget and header_widget.row_type() == "tkzTabVar":
                    self.table.setRowHeight(r, 60) # Increased to accommodate 11px spacing
                    if col % 2 != 0:
                        self.add_centered_item(r, col, "")
                        continue
                    if text_value:
                        if not self.table.cellWidget(r, col): 
                            self.table.setCellWidget(r, col, TkzVarCellWidget(is_math=True, default_prefix="", default_text=""))
                    else:
                        widget = self.table.cellWidget(r, col)
                        if widget: 
                            self.table.removeCellWidget(r, col)
                        self.add_centered_item(r, col, "")
        self.table.blockSignals(False)
        self.table.viewport().update()

    def toggle_colors_visibility(self):
        is_checked = self.chk_color.isChecked()
        for btn in self.color_buttons.values():
            btn.setVisible(is_checked)
        # Find and toggle color labels in settings_layout
        parent_widget = self.chk_color.parent()
        if parent_widget:
            layout = parent_widget.layout()
            if layout:
                for i in range(layout.count()):
                    widget = layout.itemAt(i).widget()
                    if widget and isinstance(widget, QLabel) and widget.text() in ["colorV:", "colorL:", "colorC:", "colorT:"]:
                        widget.setVisible(is_checked)
        self.table.viewport().update()

    def pick_color(self, key):
        color = QColorDialog.getColor(self.colors[key], self, f"Select {key}")
        if color.isValid():
            self.colors[key] = color
            self.update_button_color(key)
            self.table.viewport().update()
            
    def update_button_color(self, key):
        hex_color = self.colors[key].name()
        self.color_buttons[key].setStyleSheet(f"background-color: {hex_color}; border: 1px solid #cbd5e1; border-radius: 6px; min-height: 24px;")

    def add_centered_item(self, row, col, text):
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        
        is_tabvar = False
        header_widget = self.table.cellWidget(row, 0)
        if header_widget and hasattr(header_widget, 'row_type') and header_widget.row_type() == "tkzTabVar":
            is_tabvar = True

        if (row == 0  or is_tabvar) and col % 2 != 0 and col > 1:
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            
        self.table.setItem(row, col, item)
        
    def setup_initial_table(self):
        self.table.blockSignals(True)
        self.table.setCellWidget(0, 0, RowHeightWidget(1.0, show_type_selector=False)) 
        w1 = RowHeightWidget(1.0, show_type_selector=True, default_type="Line")
        w1.type_combo.currentIndexChanged.connect(lambda idx, r=1: self.on_row_type_changed(idx, r))
        self.table.setCellWidget(1, 0, w1)
        w2 = RowHeightWidget(2.0, show_type_selector=True, default_type="Var")
        w2.type_combo.currentIndexChanged.connect(lambda idx, r=2: self.on_row_type_changed(idx, r))
        self.table.setCellWidget(2, 0, w2)
        
        self.add_centered_item(0, 1, "$x$")
        self.add_centered_item(0, 2, "$-\\infty$")
        self.add_centered_item(0, 4, "$0$")
        self.add_centered_item(0, 6, "$+\\infty$")
        
        # Initialize all odd columns > 1 in row 0 as non-editable (interval separators)
        for c in range(3, self.table.columnCount(), 2):
            self.add_centered_item(0, c, "")
        
        for c in range(2, self.table.columnCount()):
            self.add_centered_item(1, c, "")

        self.add_centered_item(1, 1, "$f'(x)$")
        self.add_centered_item(2, 1, "$f(x)$")
        
        # Set specific values for row 1 (f'(x) line)
        self.add_centered_item(1, 3, "-")
        self.add_centered_item(1, 4, "z")
        self.add_centered_item(1, 5, "+")
        
        # Fill remaining empty cells in rows 1 and 2
        for c in range(2, self.table.columnCount()): 
            if not self.table.item(1, c) or self.table.item(1, c).text() == "":
                self.add_centered_item(1, c, "")
            if c not in [2, 4, 6]:
                if not self.table.item(2, c) or self.table.item(2, c).text() == "":
                    self.add_centered_item(2, c, "")

        self.table.setCellWidget(2, 2, TkzVarCellWidget(default_prefix="+", default_text="$+\\infty$"))
        self.table.setCellWidget(2, 4, TkzVarCellWidget(default_prefix="-", default_text="$1$"))
        self.table.setCellWidget(2, 6, TkzVarCellWidget(default_prefix="+", default_text="$+\\infty$"))
        
        self.table.blockSignals(False)
        self.adjust_row_heights()
                
    def update_table_dimensions(self):
        if self.is_undoing_redoing: 
            return
        self.save_state()
        
        new_col_count = self.col_slider.value() + 1
        # Determine new_row_count from whichever slider triggered this call
        # by comparing with current values
        new_row_count = self.row_slider_vert.value()
        # Sync both sliders
        self.row_slider_vert.blockSignals(True)
        self.row_slider_vert.setValue(new_row_count)
        self.row_slider_vert.blockSignals(False)
        self.row_vert_value_label.setText(str(new_row_count))
        
        self.table.blockSignals(True)
        self.table.setColumnCount(new_col_count)
        self.table.setRowCount(new_row_count)
            
        # ... [Your existing logic to add rows/cells] ...

        # Initialize all odd columns > 1 in row 0 as non-editable when table dimensions change
        for c in range(3, new_col_count, 2):
            existing_item = self.table.item(0, c)
            if not existing_item or existing_item.text() == "":
                self.add_centered_item(0, c, "")

        # Ensure all even columns > 1 in row 0 have centered alignment
        for c in range(2, new_col_count, 2):
            item = self.table.item(0, c)
            if item:
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        for c in range(2, new_col_count):
            item = self.table.item(1, c)
            if item:
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        # Create RowHeightWidget for each row at column 0 (type_combo + spin + arrows)
        for r in range(new_row_count):
            existing_widget = self.table.cellWidget(r, 0)
            if existing_widget and isinstance(existing_widget, RowHeightWidget):
                pass  # Already has a proper widget
            elif r == 0:
                w0 = RowHeightWidget(1.0, show_type_selector=False)
                self.table.setCellWidget(r, 0, w0)
            else:
                # Check if row already has a RowHeightWidget somewhere (shouldn't happen, but safety)
                default_type = "Line"
                # Look up row type from existing header if available
                # Try to derive default from existing row
                init_val = 1.0 if default_type == "Line" else 2.0
                w = RowHeightWidget(init_val, show_type_selector=True, default_type=default_type)
                w.type_combo.currentIndexChanged.connect(lambda idx, row_idx=r: self.on_row_type_changed(idx, row_idx))
                self.table.setCellWidget(r, 0, w)

       # اختصار عملية التوسيط في حلقة واحدة شاملة
        for r in range(1, new_row_count):
            for c in range(1, new_col_count):
                # تخطي الخلايا التي تحتوي على Widgets (لأنها لا تحتاج QTableWidgetItem)
                if not self.table.cellWidget(r, c):
                    item = self.table.item(r, c)
                    if item:
                        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    else:
                        # إنشاء خلية جديدة وتوسيطها إذا كانت فارغة
                        self.add_centered_item(r, c, "")            

        self.table.blockSignals(False)
        self.adjust_row_heights()
        self.table.viewport().update()

    def reset_to_default(self):
        self.save_state()
        self.table.blockSignals(True)
        self.col_slider.setValue(6)
        self.row_slider_vert.setValue(3)
        self.row_vert_value_label.setText("3")
        self.spin_lgt.setValue(2.0)
        self.spin_deltacl.setValue(0.5)
        self.spin_espcl.setValue(2.0)
        self.chk_nocadre.setChecked(False)
        self.chk_help.setChecked(False)
        self.chk_color.setChecked(False)
        for key in self.colors.keys():
            self.colors[key] = QColor("white")
            self.update_button_color(key)

        self.table.setRowCount(3)
        self.table.setColumnCount(7)
        self.table.clear()
        self.setup_initial_table()
        
        self.combo_presets.setCurrentIndex(0)
        self.output_code.clear()
        self.btn_preview.setEnabled(False)
        self.preview_window.hide()
        
        self.table.blockSignals(False)
        self.adjust_row_heights()
        self.table.viewport().update()
        QMessageBox.information(self, "Reset Done", "The table has been reset to its original state!")
            
    def generate_tkz_code(self):
        row_count = self.table.rowCount()
        col_count = self.table.columnCount()
        lgt_val = self.spin_lgt.value()
        espcl_val = self.spin_espcl.value()
        deltacl_val = self.spin_deltacl.value()
        
        options_list = []
        if lgt_val != 2.0: 
            options_list.append(f"lgt={lgt_val}")
        if espcl_val != 2.0:
            options_list.append(f"espcl={espcl_val}")
        if deltacl_val != 0.5: 
            options_list.append(f"deltacl={deltacl_val}")
        if self.chk_nocadre.isChecked():
            options_list.append("nocadre")
        if self.chk_help.isChecked(): 
            options_list.append("help")
        if self.chk_color.isChecked(): 
            options_list.append("color")    
            
        color_definitions = ""
        for key, color in self.colors.items():
            if color.name().lower() == "#ffffff": 
                continue 
            hex_name = color.name().upper().replace("#", "")
            color_definitions += f"\\definecolor{{{key}Custom}}{{HTML}}{{{hex_name}}}\n"
            options_list.append(f"{key}={key}Custom")
            
        options = f"[{', '.join(options_list)}]" if options_list else ""
        
        header_titles = []
        for r in range(row_count):
            title = self.table.item(r, 1).text().strip() if self.table.item(r, 1) else f"y_{r}"
            widget = self.table.cellWidget(r, 0)
            custom_height = widget.value() if widget else 2.0
            if custom_height == int(custom_height):
                custom_height = int(custom_height)
            header_titles.append(f"{title} / {custom_height}")
            
        headers_str = ", ".join(header_titles)
        x_items = []
        for c in range(2, col_count):
            item = self.table.item(0, c)
            if item and item.text().strip(): 
                x_items.append(item.text().strip())
        x_str = ", ".join(x_items)
        
        user_tikzset_text = self.txt_tikzset_content.text().strip()
        tikzset_code = ""
        if user_tikzset_text:
            tikzset_code = f"\\tikzset{{{user_tikzset_text}}}\n"
        
        latex = f"{color_definitions}"
        if tikzset_code:
            latex += f"{tikzset_code}"
            
        latex += "\\begin{tikzpicture}\n"
        latex += f"   \\tkzTabInit{options}\n"
        latex += f"      {{{headers_str}}}\n"
        latex += f"      {{{x_str}}}\n"
        
        for r in range(1, row_count):
            header_widget = self.table.cellWidget(r, 0)
            current_row_type = header_widget.row_type() if header_widget else "tkzTabLine"
            row_items = []
            
            for c in range(2, col_count):
                item = self.table.item(r, c)
                widget = self.table.cellWidget(r, c)
                
                # Check if hatched (either by item user role or widget visibility)
                is_hatched = (item and item.data(Qt.ItemDataRole.UserRole) is True) or \
                             (widget and not widget.isVisible())
                
                if is_hatched:
                    # By returning nothing here, row_items will contain an empty string
                    if current_row_type != "tkzTabVar":
                       row_items.append("h")
                    else:
                       row_items.append("")    
                elif widget and isinstance(widget, TkzVarCellWidget):
                    row_items.append(widget.get_tkz_value())
                else:
                    row_items.append(item.text().strip() if item else "")
            
            if current_row_type == "tkzTabVar":
                # This filter removes the empty strings for hatched segments
                row_items = [v for v in row_items if v]
                latex += f"   \\tkzTabVar{{{ ' , '.join(row_items) }}}\n"
            else:
                latex += f"   \\tkzTabLine{{{ ' , '.join(row_items) }}}\n"
                
        latex += "\\end{tikzpicture}"
        self.output_code.setPlainText(latex)
        self.btn_preview.setEnabled(True) 

    def compile_and_preview_latex(self):
        if not PDF_SUPPORT:
            QMessageBox.warning(self, "Missing Library", "الرجاء تثبيت مكتبة تحويل الصور أولاً عبر الأمر:\npip install pymupdf")
            return
            
        tkz_code = self.output_code.toPlainText().strip()
        if not tkz_code: 
            return
        
        self.preview_window.set_status_text("Compiling LaTeX...")
        
        screen = QApplication.primaryScreen().geometry()
        window_geometry = self.preview_window.frameGeometry()
        center_point = screen.center()
        window_geometry.moveCenter(center_point)
        self.preview_window.move(window_geometry.topLeft())
        self.preview_window.show()
        
        full_document = (
            "\\documentclass{standalone}\n"
            "\\usepackage{tkz-tab}\n"
            "\\usepackage{xcolor}\n" 
            "\\begin{document}\n"
            f"{tkz_code}\n"
            "\\end{document}\n"
        )
        
        unique_id = uuid.uuid4().hex[:8]
        temp_dir = tempfile.gettempdir()
        filename = os.path.join(temp_dir, f"temp_{unique_id}")        
        tex_file = f"{filename}.tex"
        pdf_file = f"{filename}.pdf"
        png_file = f"{filename}.png"

        try:
            with open(tex_file, "w", encoding="utf-8") as f:
                f.write(full_document)
                
            startupinfo = None
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
            process = subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", f"temp_{unique_id}.tex"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                startupinfo=startupinfo, cwd=temp_dir, timeout=5
            )
            
            if process.returncode != 0:
                self.preview_window.set_status_text("LaTeX Compilation Error.")
                QMessageBox.critical(self, "LaTeX Error", "The code processing failed. Please review the table cell values\n to ensure the tkz-tab code is correctly formatted.")
                return

            if os.path.exists(pdf_file):
                doc = fitz.open(pdf_file)
                page = doc.load_page(0)
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                pix.save(png_file)
                doc.close()
                
                pixmap = QPixmap(png_file)
                self.preview_window.show_pixmap(pixmap)
                
                window_geometry = self.preview_window.frameGeometry()
                window_geometry.moveCenter(screen.center())
                self.preview_window.move(window_geometry.topLeft())
            else:
                self.preview_window.set_status_text("Error: Output PDF not found.")
                QMessageBox.warning(self, "Preview Error", "The PDF output file could not be found.")
                
        except subprocess.TimeoutExpired:
            self.preview_window.set_status_text("Compilation timed out.")
            QMessageBox.critical(self, "Timeout Error", "The compiling process took too long and was cancelled.")
        except Exception as e:
            self.preview_window.set_status_text("System Error.")
            QMessageBox.critical(self, "System Error", f"An unexpected error occurred:\n{str(e)}")
        finally:
            # List of temporary files to clean up
            files_to_remove = [f"{filename}{ext}" for ext in [".tex", ".log", ".aux", ".pdf", ".png"]]
            
            for filepath in files_to_remove:
                if os.path.exists(filepath):
                    try:
                        # Attempt to remove the file
                        os.remove(filepath)
                    except OSError as e:
                        # Log the error to your console instead of crashing the UI
                        print(f"DEBUG: Could not remove {filepath}: {e}")
                        # Move on to the next file
                        continue

    def copy_to_clipboard(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.output_code.toPlainText())
        QMessageBox.information(self, "Success", "LaTeX code copied to clipboard successfully!")


if __name__ == '__main__':
    # Add the AppUserModelID block here as before...
    
    app = QApplication.instance()
    if app is None: 
        app = QApplication(sys.argv)
    
    # --- MODIFIED ICON LOADING ---
    try:
        icon_path = resource_path("ic.ico")
        if os.path.exists(icon_path):
            app.setWindowIcon(QIcon(icon_path))
        else:
            print(f"DEBUG: Icon not found at {icon_path}")
    except Exception as e:
        print(f"DEBUG: Could not set icon: {e}")
    # -----------------------------

    ex = TkzTabGridGenerator()
    ex.showMaximized()

    sys.exit(app.exec())