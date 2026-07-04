import sys
import os
import subprocess
import uuid
import tempfile
from PyQt6.QtCore import Qt, QLocale, QTimer, QObject, QEvent, QPoint
from PyQt6.QtGui import QColor, QBrush, QFont, QPainter, QPen, QPixmap, QCursor, QKeySequence, QShortcut

from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                             QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QSpinBox, 
                             QDoubleSpinBox, QCheckBox, QTextEdit, QPushButton, QMessageBox, 
                             QGroupBox, QColorDialog, QComboBox, QLineEdit, QSpacerItem, QSizePolicy,
                             QStyledItemDelegate, QToolTip)

try:
    import fitz  # PyMuPDF
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

FONT_FAMILY = "Segoe UI" if sys.platform == "win32" else "Arial"


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
                        return True
            return True
        
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
            # Convert global/local positions to pinpoint the text character index
            global_pos = QCursor.pos()
            local_pos = self.line_edit.mapFromGlobal(global_pos)
            
            # Use font metrics to find which character index is under the mouse
            fm = self.line_edit.fontMetrics()
            text = self.line_edit.text()
            
            # Account for internal line edit margins/paddings
            content_x = local_pos.x() - self.line_edit.contentsMargins().left() - 2 
            
            # Find the character index
            char_idx = -1
            for i in range(len(text)):
                prefix_width = fm.horizontalAdvance(text[:i+1])
                if prefix_width >= content_x:
                    char_idx = i
                    break
            if char_idx == -1 and len(text) > 0:
                char_idx = len(text) - 1

            if char_idx >= 0 and char_idx < len(text):
                # Check if any keyword matches the hovered text block
                matched_key = None
                for key in self.tooltips.keys():
                    # Find all occurrences of the key in the raw string
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
    def __init__(self, initial_value=2.0, show_type_selector=True, default_type="Line"):
        super().__init__()
        layout = QGridLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)
        
        self.type_combo = None
        if show_type_selector:
            self.type_combo = QComboBox()
            self.type_combo.addItem("TabLine", "tkzTabLine")
            self.type_combo.addItem("TabVar", "tkzTabVar")
            
            self.type_combo.setFixedWidth(60)
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
        else:
            spacer = QSpacerItem(60, 20, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)
            layout.addItem(spacer, 0, 0)
            
        self.spin = CustomDoubleSpinBox()
        self.spin.setRange(0.5, 10.0)
        self.spin.setSingleStep(0.5) 
        self.spin.setDecimals(2)      
        self.spin.setValue(float(initial_value))
        self.spin.setFixedWidth(65)   
        self.spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.spin, 0, 1, Qt.AlignmentFlag.AlignCenter)
        
        self.arrow_label = QLabel("⇳")
        self.arrow_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.arrow_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #6366f1;")
        layout.addWidget(self.arrow_label, 0, 2, Qt.AlignmentFlag.AlignCenter)
            
        self.setStyleSheet("background-color: transparent; border: none;")

    def value(self):
        return self.spin.value()
        
    def row_type(self):
        if self.type_combo:
            return self.type_combo.currentData()
        return "tkzTabInit" 


class TkzVarCellWidget(QWidget):
    def __init__(self, default_prefix="", default_text=""):
        super().__init__()
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(4, 4, 4, 4)
        self.main_layout.setSpacing(0)
        
        self.container_widget = QWidget()
        self.container_layout = QHBoxLayout(self.container_widget)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(4)
        
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
            QComboBox::drop-down { 
                border: none; 
            }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                border: 1px solid #cbd5e1;
            }
        """)
               
        self.items_tooltips = {
            "-": "Unique expression centered at the bottom",
            "+": "Unique expression centered at the top",
            "R": "Nothing, we move on to the next expression",
            "-C": "Extension by continuity downwards, centered",
            "+C": "Extension by continuity at the top, centered",
            "-H": "Expression at the bottom and centered, then forbidden zone",
            "+H": "Expression at the top and centered, then forbidden zone",
            "+D": "Discontinuity, expression at the top left",
            "-D": "Discontinuity, expression at the bottom left",
            "D+": "Discontinuity, expression at the upper right",
            "D-": "Discontinuity, expression at the top right",
            "+DH": "Discontinuity on the left and at the top, then forbidden zone",
            "-DH": "Discontinuity on the left and at the bottom, then forbidden zone",
            "+CH": "Expression at the top left, extension by continuity then forbidden zone",
            "-CH": "Expression at the bottom left, extension by continuity then forbidden zone",
            "+D-": "Discontinuity, two expressions top left + bottom right",
            "-D+": "Discontinuity, two expressions bottom left + top right",
            "+D+": "Discontinuity, two expressions top left + top right",
            "-D-": "Discontinuity, two expressions bottom left + bottom right",
            "+CD+": "Extension by continuity to the top left and the top right",
            "-CD-": "Extension by continuity to the bottom left and the bottom right",
            "+CD-": "Extension by continuity to the bottom left and the bottom right",
            "-CD+": "Extension by continuity to the bottom left and the top right",
            "+V+":  "Like +D+ but without a double bar",
            "-V-":  "Like -D- but without a double bar",
            "+V-":  "Like +D- but without a double bar",
            "-V+":  "Like -D+ but without a double bar",
        }

        for text in self.items_tooltips.keys():
            self.combo.addItem(text)
 
        self._filter = SafeEventFilter(self.combo, self.items_tooltips)
        self.combo.installEventFilter(self._filter)
        if self.combo.view():
            self.combo.view().installEventFilter(self._filter)
            self.combo.view().setMouseTracking(True)

        # Style definition for fields
        line_edit_style = """
            QLineEdit { border: 1px solid #e2e8f0; border-radius: 6px; padding: 2px; background-color: #ffffff; }
            QLineEdit:focus { border: 1px solid #6366f1; }
        """

        # First text field (used as the singular entry or Left entry)
        self.line_edit = QLineEdit()
        self.line_edit.setPlaceholderText("Val 1")
        self.line_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.line_edit.setStyleSheet(line_edit_style)

        # Second text field (Only visible when split entries like -D-, +D-, etc. are picked)
        self.line_edit_2 = QLineEdit()
        self.line_edit_2.setPlaceholderText("Val 2")
        self.line_edit_2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.line_edit_2.setStyleSheet(line_edit_style)
        self.line_edit_2.setVisible(False) 
        
        self.container_layout.addWidget(self.combo)
        self.container_layout.addWidget(self.line_edit)
        self.container_layout.addWidget(self.line_edit_2)
        
        self.main_layout.addWidget(self.container_widget)
        self.setStyleSheet("background-color: transparent;")
        
        self.combo.currentTextChanged.connect(self.update_elements_alignment)
        
        # Handle population of initial data if passed down
        if default_text:
            if " / " in default_text:  # If it has split contents already
                parts = default_text.split(" / ")
                self.line_edit.setText(parts[0])
                if len(parts) > 1:
                    self.line_edit_2.setText(parts[1])
            else:
                self.line_edit.setText(default_text)

        if default_prefix:
            found = False
            for i in range(self.combo.count()):
                if self.combo.itemText(i) == default_prefix:
                    self.combo.setCurrentIndex(i)
                    found = True
                    break
            if not found:
                for i in range(self.combo.count()):
                    if self.combo.itemText(i).startswith(default_prefix):
                        self.combo.setCurrentIndex(i)
                        break

        QTimer.singleShot(0, lambda: self.update_elements_alignment(self.combo.currentText()))
        
    def update_elements_alignment(self, text):
        # Remove the widget first to re-apply the layout alignment cleanly
        self.main_layout.removeWidget(self.container_widget)
        
        # Check for split scenarios (starts with sign and ends with sign/letter like +D-, -D+, etc.)
        is_split = text in ["+D-", "-D+", "+D+", "-D-", "+CD+", "-CD-", "+CD-", "-CD+", "+V+", "-V-", "+V-", "-V+"]
        
        if is_split:
            self.line_edit_2.setVisible(True)
            self.line_edit.setPlaceholderText("Left")
            # Dual-value combinations sit centered vertically within the row cell
            # Change the position of BOTH the combo box and the line edit together
            if text.startswith('+'):
                align = Qt.AlignmentFlag.AlignTop
            elif text.startswith('-'):
                align = Qt.AlignmentFlag.AlignBottom
            else:
                # Fallback check for items ending with signs if no prefix sign exists
                if text.endswith('+'):
                   align = Qt.AlignmentFlag.AlignTop
                elif text.endswith('-'):
                   align = Qt.AlignmentFlag.AlignBottom
                else:
                   align = Qt.AlignmentFlag.AlignCenter  
        else:
            self.line_edit_2.setVisible(False)
            self.line_edit.setPlaceholderText("Value")
            
            # Change the position of BOTH the combo box and the line edit together
            if text.startswith('+'):
                align = Qt.AlignmentFlag.AlignTop
            elif text.startswith('-'):
                align = Qt.AlignmentFlag.AlignBottom
            else:
                # Fallback check for items ending with signs if no prefix sign exists
                if text.endswith('+'):
                   align = Qt.AlignmentFlag.AlignTop
                elif text.endswith('-'):
                   align = Qt.AlignmentFlag.AlignBottom
                else:
                   align = Qt.AlignmentFlag.AlignCenter
            
        # Add the entire layout row widget back with the updated dynamic vertical alignment
        self.main_layout.addWidget(self.container_widget, alignment=align)
        self.container_widget.update()
            
    def get_tkz_value(self):
        current_str = self.combo.currentText().strip()
        text1 = self.line_edit.text().strip()
        text2 = self.line_edit_2.text().strip() if self.line_edit_2.isVisible() else ""
        
        if current_str:
            if text2:
                # Returns context in "PREFIX/ LeftVal / RightVal" syntax 
                return f"{current_str}/ {text1} / {text2}"
            elif text1:
                return f"{current_str}/ {text1}"
            else:
                return f"{current_str}/"
        return text1
    
class BorderAndHatchDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.nocadre_checkbox = None

    def paint(self, painter, option, index):
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

        is_hatched = index.data(Qt.ItemDataRole.UserRole)
        if is_hatched:
            hatch_pen = QPen(QColor(164, 174, 188), 1.5, Qt.PenStyle.SolidLine)
            painter.setPen(hatch_pen)
            offset = 8  
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

        border_pen = QPen(QColor(0, 0, 0), 2, Qt.PenStyle.SolidLine)
        painter.setPen(border_pen)

        if row == 0:
            if not nocadre:
                painter.drawLine(rect.left(), rect.top(), rect.right(), rect.top())
        else:
            painter.drawLine(rect.left(), rect.top(), rect.right(), rect.top())

        if row == total_rows - 1:
            if not nocadre:
                painter.drawLine(rect.left(), bottom:=rect.bottom(), rect.right(), bottom)
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
        
        self.preview_label = QLabel("Compiling LaTeX...")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setWordWrap(True)
        self.preview_label.setStyleSheet("color: #94a3b8; font-style: italic; background-color: #ffffff; padding: 10px;")
        
        layout.addWidget(self.preview_label)
        self.setLayout(layout)

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


class TkzTabGridGenerator(QWidget):
    def __init__(self):
        super().__init__()
        self.colors = {
            "colorV": QColor("white"),  
            "colorL": QColor("white"),  
            "colorC": QColor("white"),  
            "colorT": QColor("white")   
        }
        
        # مكررات ومخازن الـ Undo و الـ Redo
        self.undo_stack = []
        self.redo_stack = []
        self.is_undoing_redoing = False

        self.preview_window = PreviewWindow() 
        self.initUI()
        
        # حفظ الحالة الافتراضية بعد بناء الواجهة
        QTimer.singleShot(100, self.save_state)
        
    def initUI(self):
        self.setWindowTitle('tkz-tabmaker Table Generator Assistant')
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
        tikzset_layout = QHBoxLayout()  # Changed to QHBoxLayout to hold combo and line edit side-by-side
        tikzset_layout.setSpacing(8)
        
        # Style preset configurations
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
        
        # Enable tracking and attach the hover tooltip filter
        self.txt_tikzset_content.setMouseTracking(True)
        self._line_edit_filter = LineEditTooltipFilter(self.txt_tikzset_content, self.styles_tooltips)
        self.txt_tikzset_content.installEventFilter(self._line_edit_filter)

        # Connect combo change event to automatically fill the line edit
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
        settings_layout = QHBoxLayout()
        settings_layout.setSpacing(10)

        settings_layout.addWidget(QLabel('Columns:'))
        self.spin_columns = QSpinBox()
        self.spin_columns.setMinimum(3)
        self.spin_columns.setMaximum(15)
        self.spin_columns.setValue(6) 
        self.spin_columns.setFixedWidth(75)
        self.spin_columns.valueChanged.connect(self.update_table_dimensions)
        settings_layout.addWidget(self.spin_columns)
        
        settings_layout.addWidget(QLabel('Rows:'))
        self.spin_rows = QSpinBox()
        self.spin_rows.setMinimum(2)
        self.spin_rows.setMaximum(10)
        self.spin_rows.setValue(3)
        self.spin_rows.setFixedWidth(75)
        self.spin_rows.valueChanged.connect(self.update_table_dimensions)
        settings_layout.addWidget(self.spin_rows)
        
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
        
        self.colors_group = QGroupBox("Table Background Colors")
        colors_layout = QHBoxLayout()
        self.color_buttons = {}
        color_labels = {"colorV": "colorV:", "colorL": "colorL:", "colorC": "colorC:", "colorT": "colorT:"}
        
        for key, label_text in color_labels.items():
            colors_layout.addWidget(QLabel(label_text))
            btn = QPushButton()
            btn.setFixedWidth(45)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, k=key: self.pick_color(k))
            colors_layout.addWidget(btn)
            self.color_buttons[key] = btn
            colors_layout.addSpacing(15)
        colors_layout.addStretch()
        self.colors_group.setLayout(colors_layout)
        main_layout.addWidget(self.colors_group)
        self.colors_group.setVisible(False)
        
        self.table = QTableWidget()
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
        self.table.setColumnWidth(0, 175) 
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.setShowGrid(False) 
        
        self.table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked | QTableWidget.EditTrigger.AnyKeyPressed)
        self.table.editTriggered = lambda index: False if (index.column() % 2 != 0 and index.column() > 1 and (index.row() == 0 or (self.table.cellWidget(index.row(), 0) and self.table.cellWidget(index.row(), 0).row_type() == "tkzTabVar"))) else True
        
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.handle_right_click)
        
        self.setup_initial_table()
        
        self.table.itemChanged.connect(self.safe_handle_item_changed)
        main_layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        self.btn_generate = QPushButton('1. Generate LaTeX Code')
        self.btn_generate.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_generate.setStyleSheet("""
            QPushButton { font-weight: bold; font-size: 13px; padding: 10px 20px; background-color: #4f46e5; color: white; border: none; border-radius: 8px; }
            QPushButton:hover { background-color: #4338ca; }
        """)
        self.btn_generate.clicked.connect(self.generate_tkz_code)
        
        self.btn_preview = QPushButton('2. Compile & Preview')
        self.btn_preview.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_preview.setEnabled(False) 
        self.btn_preview.setStyleSheet("""
            QPushButton { font-weight: bold; font-size: 13px; padding: 10px 20px; background-color: #059669; color: white; border: none; border-radius: 8px; }
            QPushButton:hover { background-color: #047857; }
            QPushButton:disabled { background-color: #cbd5e1; color: #94a3b8; }
        """)
        self.btn_preview.clicked.connect(self.compile_and_preview_latex)
        
        self.btn_copy = QPushButton('Copy Code')
        self.btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy.setStyleSheet("""
            QPushButton { font-weight: bold; font-size: 13px; padding: 10px 20px; background-color: #ffffff; color: #475569; border: 1px solid #cbd5e1; border-radius: 8px; }
            QPushButton:hover { background-color: #f8fafc; color: #1e293b; }
        """)
        self.btn_copy.clicked.connect(self.copy_to_clipboard)
        
        btn_layout.addWidget(self.btn_generate)
        btn_layout.addWidget(self.btn_preview)
        btn_layout.addWidget(self.btn_copy)
        main_layout.addLayout(btn_layout)
        
        self.output_code = QTextEdit()
        self.output_code.setReadOnly(False)
        self.output_code.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.output_code.setPlaceholderText("\\begin{tikzpicture} code will appear here...")
        self.output_code.setMinimumHeight(150)
        self.output_code.setStyleSheet("""
            QTextEdit { background-color: #1e1e2e; color: #f8f8f2; font-family: "Consolas", monospace; font-size: 12px; border: 1px solid #313244; border-radius: 10px; padding: 8px; }
        """)
       
        main_layout.addWidget(QLabel('Generated LaTeX Code:'))
        main_layout.addWidget(self.output_code)

        # ربط اختصارات الكيبورد الـ Undo والـ Redo
        self.undo_shortcut = QShortcut(QKeySequence("Ctrl+Z"), self)
        self.undo_shortcut.activated.connect(self.undo)
        
        self.redo_shortcut = QShortcut(QKeySequence("Ctrl+Y"), self)
        self.redo_shortcut.activated.connect(self.redo)

    def on_preset_changed(self, text):
        preset_value = self.style_presets.get(text, "")
        self.txt_tikzset_content.setText(preset_value)

    # دالة حفظ الحالة الشاملة للجدول ومكوناته
    def save_state(self):
        if self.is_undoing_redoing: return
        
        state = {
            "rows": self.table.rowCount(),
            "cols": self.table.columnCount(),
            "spin_columns": self.spin_columns.value(),
            "spin_rows": self.spin_rows.value(),
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
        if len(self.undo_stack) <= 1: return
        state = self.undo_stack.pop()
        self.redo_stack.append(state)
        
        previous_state = self.undo_stack[-1]
        self.restore_state(previous_state)

    def redo(self):
        if not self.redo_stack: return
        state = self.redo_stack.pop()
        self.undo_stack.append(state)
        self.restore_state(state)

    def restore_state(self, state):
        self.is_undoing_redoing = True
        self.table.blockSignals(True)
        
        self.spin_columns.blockSignals(True)
        self.spin_rows.blockSignals(True)
        self.spin_columns.setValue(state["spin_columns"])
        self.spin_rows.setValue(state["spin_rows"])
        self.spin_columns.blockSignals(False)
        self.spin_rows.blockSignals(False)
        
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

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.adjust_row_heights()

    def adjust_row_heights(self):
        row_count = self.table.rowCount()
        if row_count == 0: return
        
        total_height = self.table.viewport().height()
        shares = []
        for r in range(row_count):
            if r == 0:
                shares.append(1)
            else:
                header_widget = self.table.cellWidget(r, 0)
                if header_widget and header_widget.row_type() == "tkzTabVar":
                    shares.append(3) 
                else:
                    shares.append(1)
                    
        total_shares = sum(shares)
        if total_shares == 0: return
        
        single_share_height = total_height / total_shares
        for r in range(row_count):
            self.table.verticalHeader().setSectionResizeMode(r, QHeaderView.ResizeMode.Interactive)
            self.table.setRowHeight(r, int(single_share_height * shares[r]))
        
    def closeEvent(self, event):
        self.preview_window.close()
        super().closeEvent(event)

    def handle_right_click(self, pos):
        index = self.table.indexAt(pos)
        if index.isValid():
            self.basculer_hachure(index.row(), index.column())

    def basculer_hachure(self, row, col):
        if row == 0 or col == 0: return

        item = self.table.item(row, col)
        if not item:
            item = QTableWidgetItem("")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, col, item)

        is_hatched = item.data(Qt.ItemDataRole.UserRole)
        widget = self.table.cellWidget(row, col)

        if not is_hatched and col > 1:
            # --- 1. تفعيل التهشير ---
            item.setData(Qt.ItemDataRole.UserRole, True)
            
            if widget:
                # إذا كانت الخلية تحتوي على ويدجت مركب (مثل خلايا TabVar)
                widget.setVisible(False)
                if not item.text().strip(): 
                    item.setText("h")
            else:
                # إذا كانت خلية نصية عادية (مثل خلايا TabLine)
                original_text = item.text()
                # حفظ النص الأصلي في مخزن مخصص لكي لا يضيع
                item.setData(Qt.ItemDataRole.UserRole + 1, original_text)
                # إخفاء النص واستبداله بحرف التهشير للمولد
                item.setText("h")
                
        else:
            # --- 2. إلغاء التهشير ---
            item.setData(Qt.ItemDataRole.UserRole, False)
            
            if widget:
                # إعادة إظهار الويدجت المركب
                widget.setVisible(True)
                if item.text() == "h": 
                    item.setText("")
            else:
                # استعادة النص الأصلي للخلية العادية الذي قمنا بحفظه مسبقاً
                saved_text = item.data(Qt.ItemDataRole.UserRole + 1)
                if saved_text is not None:
                    item.setText(saved_text)
                elif item.text() == "h":
                    item.setText("")

        self.table.viewport().update()

    def on_row_type_changed(self, index, row):
        header_widget = self.table.cellWidget(row, 0)
        if not header_widget: return
        
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
                        self.table.setCellWidget(row, c, TkzVarCellWidget("", ""))
                    else:
                        self.add_centered_item(row, c, "")
            else:
                if self.table.cellWidget(row, c): self.table.removeCellWidget(row, c)
                self.add_centered_item(row, c, "")
        self.table.blockSignals(False)
        self.adjust_row_heights()
        self.table.viewport().update()

    def safe_handle_item_changed(self, item):
        QTimer.singleShot(50, lambda: self.process_item_changed(item))

    def process_item_changed(self, item):
        if self.is_undoing_redoing: return
        self.save_state()
        try:
            row = item.row()
            col = item.column()
        except RuntimeError:
            return

        self.table.blockSignals(True) 
        if row == 0 and col >= 2:
            text_value = item.text().strip()
            for r in range(1, self.table.rowCount()):
                header_widget = self.table.cellWidget(r, 0)
                if header_widget and header_widget.row_type() == "tkzTabVar":
                    if col % 2 != 0:
                        self.add_centered_item(r, col, "")
                        continue
                    if text_value:
                        if not self.table.cellWidget(r, col): 
                            self.table.setCellWidget(r, col, TkzVarCellWidget("", ""))
                    else:
                        widget = self.table.cellWidget(r, col)
                        if widget: 
                            self.table.removeCellWidget(r, col)
                        self.add_centered_item(r, col, "")
        self.table.blockSignals(False)
        self.table.viewport().update()

    def toggle_colors_visibility(self):
        self.colors_group.setVisible(self.chk_color.isChecked())
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

        if (row == 0 or is_tabvar) and col % 2 != 0 and col > 1:
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
        
        for c in [3, 5]:
            item = QTableWidgetItem("")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(0, c, item)

        self.add_centered_item(1, 1, "$f'(x)$")
        self.add_centered_item(2, 1, "$f(x)$")
        
        for c in range(2, 7): 
            self.add_centered_item(1, c, "")
            if c not in [2, 4, 6]: 
                self.add_centered_item(2, c, "")
            
        self.add_centered_item(1, 3, "-")
        self.add_centered_item(1, 4, "z")
        self.add_centered_item(1, 5, "+")

        self.table.setCellWidget(2, 2, TkzVarCellWidget(default_prefix="+", default_text="$+\\infty$"))
        self.table.setCellWidget(2, 4, TkzVarCellWidget(default_prefix="-", default_text="$1$"))
        self.table.setCellWidget(2, 6, TkzVarCellWidget(default_prefix="+", default_text="$+\\infty$"))
        
        self.table.blockSignals(False)
        self.adjust_row_heights()
                
    def update_table_dimensions(self):
        if self.is_undoing_redoing: return
        self.save_state()
        
        new_col_count = self.spin_columns.value() + 1
        new_row_count = self.spin_rows.value()
        old_col_count = self.table.columnCount()
        old_row_count = self.table.rowCount()
        
        self.table.blockSignals(True)
        self.table.setColumnCount(new_col_count)
        self.table.setRowCount(new_row_count)
            
        for r in range(new_row_count):
            if r >= old_row_count:
                w = RowHeightWidget(2.0, show_type_selector=True, default_type="Line")
                w.type_combo.currentIndexChanged.connect(lambda idx, row_idx=r: self.on_row_type_changed(idx, row_idx))
                self.table.setCellWidget(r, 0, w)
            if r >= old_row_count and not self.table.item(r, 1): self.add_centered_item(r, 1, "")
                
            for c in range(new_col_count):
                if c > 0 and (r >= old_row_count or c >= old_col_count):
                    header_widget = self.table.cellWidget(r, 0)
                    is_tabvar = header_widget and header_widget.row_type() == "tkzTabVar"
                    
                    if (r == 0 or is_tabvar) and c % 2 != 0:
                        item = QTableWidgetItem("")
                        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                        self.table.setItem(r, c, item)
                        continue

                    if header_widget and header_widget.row_type() == "tkzTabVar":
                        x_item = self.table.item(0, c)
                        if x_item and x_item.text().strip():
                            if not self.table.cellWidget(r, c): self.table.setCellWidget(r, c, TkzVarCellWidget("", ""))
                        else: self.add_centered_item(r, c, "")
                    else:
                        if not self.table.item(r, c) and not self.table.cellWidget(r, c): self.add_centered_item(r, c, "")
                        
        self.table.blockSignals(False)
        self.adjust_row_heights()
        self.table.viewport().update()

    def reset_to_default(self):
        self.save_state()
        self.table.blockSignals(True)
        self.spin_columns.setValue(6)
        self.spin_rows.setValue(3)
        self.spin_lgt.setValue(2.0)
        self.spin_deltacl.setValue(0.5)
        self.spin_espcl.setValue(2.0)
        self.chk_nocadre.setChecked(False)
        self.chk_help.setChecked(False)
        self.chk_color.setChecked(False)
        self.colors_group.setVisible(False)
        
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
        if lgt_val != 2.0: options_list.append(f"lgt={lgt_val}")
        if espcl_val != 2.0: options_list.append(f"espcl={espcl_val}")
        if deltacl_val != 0.5: options_list.append(f"deltacl={deltacl_val}")
        if self.chk_nocadre.isChecked(): options_list.append("nocadre")
        if self.chk_help.isChecked(): options_list.append("help")
        if self.chk_color.isChecked(): options_list.append("color")    
            
        color_definitions = ""
        for key, color in self.colors.items():
            if color.name().lower() == "#ffffff": continue 
            hex_name = color.name().upper().replace("#", "")
            color_definitions += f"\\definecolor{{{key}Custom}}{{HTML}}{{{hex_name}}}\n"
            options_list.append(f"{key}={key}Custom")
            
        options = f"[{', '.join(options_list)}]" if options_list else ""
        
        header_titles = []
        for r in range(row_count):
            title = self.table.item(r, 1).text().strip() if self.table.item(r, 1) else f"y_{r}"
            widget = self.table.cellWidget(r, 0)
            custom_height = widget.value() if widget else 2.0
            if custom_height == int(custom_height): custom_height = int(custom_height)
            header_titles.append(f"{title} / {custom_height}")
            
        headers_str = ", ".join(header_titles)
        x_items = []
        for c in range(2, col_count):
            item = self.table.item(0, c)
            if item and item.text().strip(): x_items.append(item.text().strip())
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
                widget = self.table.cellWidget(r, c)
                if widget and isinstance(widget, TkzVarCellWidget):
                    val = widget.get_tkz_value()
                else:
                    item = self.table.item(r, c)
                    if item and item.data(Qt.ItemDataRole.UserRole) is True: val = "h"  
                    else: val = item.text().strip() if item else ""
                row_items.append(val)
            
            if current_row_type == "tkzTabVar":
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
        if not tkz_code: return
        
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
            for ext in [".tex", ".log", ".aux", ".pdf", ".png"]:
                target = f"{filename}{ext}"
                if os.path.exists(target):
                    try: os.remove(target)
                    except: pass

    def copy_to_clipboard(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.output_code.toPlainText())
        QMessageBox.information(self, "Success", "LaTeX code copied to clipboard successfully!")


if __name__ == '__main__':
    app = QApplication.instance()
    if app is None: app = QApplication(sys.argv)
    ex = TkzTabGridGenerator()
    ex.showMaximized()
    for k in ex.colors.keys(): ex.update_button_color(k)
    app.exec()