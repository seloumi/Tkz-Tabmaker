"""Configuration constants and styling for Tkz-Tabmaker."""

import sys
from typing import Dict
from PyQt6.QtGui import QColor

# Platform detection
IS_WINDOWS = sys.platform == "win32"
DEFAULT_FONT_FAMILY = "Segoe UI" if IS_WINDOWS else "Arial"

# Table dimensions
DEFAULT_COLUMNS = 6
DEFAULT_ROWS = 3
MIN_COLUMNS = 3
MAX_COLUMNS = 15
MIN_ROWS = 2
MAX_ROWS = 10

# Cell values
DEFAULT_ROW_HEIGHT = 2.0
DEFAULT_LGT = 2.0
DEFAULT_DELTACL = 0.5
DEFAULT_ESPCL = 2.0

# Spinner ranges
LGT_RANGE = (0.5, 5.0)
DELTACL_RANGE = (0.4, 3.0)
ESPCL_RANGE = (0.5, 5.0)
ROW_HEIGHT_RANGE = (0.5, 10.0)
SPINNER_STEP = 0.5

# Colors
COLOR_KEYS = ["colorV", "colorL", "colorC", "colorT"]
DEFAULT_COLORS: Dict[str, QColor] = {
    key: QColor("white") for key in COLOR_KEYS
}

# LaTeX compilation
LATEX_TIMEOUT_SECONDS = 30
LATEX_DPI_SCALE = 2  # Zoom factor for PDF to PNG conversion
HATCH_PATTERN = "h"  # LaTeX hatching marker

# UI dimensions
COMBO_PRESET_WIDTH = 110
COMBO_TYPE_WIDTH = 60
SPINBOX_WIDTH = 75
COLOR_BUTTON_WIDTH = 45
FIRST_COLUMN_WIDTH = 175
ROW_HEIGHT_SPIN_WIDTH = 65
TKZ_VAR_CELL_HEIGHT = 28

# UI spacing
GRID_LAYOUT_SPACING = 4
GRID_LAYOUT_MARGINS = 4
HLAYOUT_SPACING = 8
VLAYOUT_SPACING = 12
COLOR_BUTTON_SPACING = 15
MAIN_MARGIN = 15

# Hatch settings
HATCH_OFFSET = 8
HATCH_PEN_WIDTH = 1.5
HATCH_COLOR = (164, 174, 188)  # RGB tuple

# Border settings
BORDER_PEN_WIDTH = 2
BORDER_COLOR = (0, 0, 0)  # RGB tuple

# Tooltip styling
TOOLTIP_STYLE_TEMPLATE = """
<div style='background-color: #1e293b; color: #f8fafc; border: 1px solid #475569; 
            padding: 6px 10px; border-radius: 6px; font-family: "{font}"; font-size: 12px;'>
    <b style='color: #38bdf8;'>[{key}]:</b> {description}
</div>
"""

# Style presets for tikzset
STYLE_PRESETS: Dict[str, str] = {
    "Custom": "",
    "t style": "t style/.style = {style  = dotted, draw = \\tkzTabDefaultWritingColor}",
    "h style": "h style/.style = {pattern = north west lines, pattern color = \\tkzTabDefaultWritingColor}",
    "node style": "node style/.style = {inner sep = \\tkzTabDefaultSep, outer sep = \\tkzTabDefaultSep, fill = \\tkzTabDefaultBackgroundColor}",
    "arrow style": "arrow style/.style={\\tkzTabDefaultWritingColor, -> ,> = \\tkzTabDefaultArrowStyle, shorten > = \\tkzTabDefaultSep, shorten < = \\tkzTabDefaultSep}",
    "double style ": "double style/.append style = { draw = \\tkzTabDefaultWritingColor,double =  \\tkzTabDefaultBackgroundColor}"
}

# Style variable descriptions
STYLE_VARIABLES: Dict[str, str] = {
    "\\tkzTabDefaultWritingColor": "black",
    "\\tkzTabDefaultBackgroundColor": "white",
    "\\tkzTabDefaultArrowStyle": "latex'",
    "\\tkzTabDefaultSep": "2pt",
}

# TkzVarCellWidget items and their descriptions
TKZ_VAR_ITEMS: Dict[str, str] = {
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
    "+V+": "Like +D+ but without a double bar",
    "-V-": "Like -D- but without a double bar",
    "+V-": "Like +D- but without a double bar",
    "-V+": "Like -D+ but without a double bar",
}

# Split cell scenarios (cells with two inputs)
SPLIT_SCENARIOS = {"+D-", "-D+", "+D+", "-D-", "+CD+", "-CD-", "+CD-", "-CD+", "+V+", "-V-", "+V-", "-V+"}

# Stylesheets
STYLESHEETS: Dict[str, str] = {
    "main_window": """
        QWidget {{ background-color: #f8fafc; color: #334155; font-family: "{font}"; }}
        QLabel {{ color: #475569; font-weight: 500; }}
        QGroupBox {{ font-weight: bold; border: 1px solid #e2e8f0; border-radius: 12px; background-color: #ffffff; padding: 10px; }}
        QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 4px; color: #1e293b; }}
        QToolTip {{ background: transparent; border: none; padding: 0px; }}
    """,
    "table_widget": """
        QTableWidget {{ background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 4px; }}
        QTableWidget::item {{ padding: 4px; }}
        QTableWidget::item:selected {{ background-color: #e0e7ff; color: #4338ca; }}
    """,
    "output_code": """
        QTextEdit {{ background-color: #1e1e2e; color: #f8f8f2; font-family: "Consolas", monospace; font-size: 12px; border: 1px solid #313244; border-radius: 10px; padding: 8px; }}
    """,
    "line_edit": """
        QLineEdit {{ border: 1px solid #e2e8f0; border-radius: 6px; padding: 2px; background-color: #ffffff; }}
        QLineEdit:focus {{ border: 1px solid #6366f1; }}
    """,
    "double_spinbox": """
        QDoubleSpinBox {{
            border: 1px solid #cbd5e1;
            border-radius: 6px;
            padding: 2px;
            background-color: #ffffff;
            font-weight: bold;
        }}
        QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
            width: 16px;
            border-left: 1px solid #cbd5e1;
        }}
        QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {{
            background-color: #e2e8f0;
        }}
    """,
    "combo_preset": """
        QComboBox {{
            border: 1px solid #cbd5e1;
            border-radius: 6px;
            padding: 5px;
            background-color: #f1f5f9;
        }}
        QComboBox::drop-down {{ border: none; }}
    """,
    "combo_type": """
        QComboBox {{
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            padding: 2px 4px;
            background-color: #f8fafc;
            font-size: 11px;
        }}
        QComboBox::drop-down {{ border: none; }}
    """,
    "checkbox": """
        QCheckBox {{ spacing: 6px; font-weight: 500; }}
        QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 4px; border: 1px solid #cbd5e1; }}
        QCheckBox::indicator:checked {{ background-color: #6366f1; border-color: #6366f1; }}
    """,
    "button_primary": """
        QPushButton {{ font-weight: bold; font-size: 13px; padding: 10px 20px; background-color: #4f46e5; color: white; border: none; border-radius: 8px; }}
        QPushButton:hover {{ background-color: #4338ca; }}
    """,
    "button_success": """
        QPushButton {{ font-weight: bold; font-size: 13px; padding: 10px 20px; background-color: #059669; color: white; border: none; border-radius: 8px; }}
        QPushButton:hover {{ background-color: #047857; }}
        QPushButton:disabled {{ background-color: #cbd5e1; color: #94a3b8; }}
    """,
    "button_danger": """
        QPushButton {{ font-weight: bold; font-size: 11px; padding: 4px 10px; background-color: #ef4444; color: white; border: none; border-radius: 6px; }}
        QPushButton:hover {{ background-color: #dc2626; }}
    """,
    "button_secondary": """
        QPushButton {{ font-weight: bold; font-size: 13px; padding: 10px 20px; background-color: #ffffff; color: #475569; border: 1px solid #cbd5e1; border-radius: 8px; }}
        QPushButton:hover {{ background-color: #f8fafc; color: #1e293b; }}
    """,
    "tikzset_content": """
        QLineEdit {{
            border: 1px solid #cbd5e1;
            border-radius: 6px;
            padding: 6px;
            font-family: 'Consolas', monospace;
            font-size: 12px;
            background-color: #f8fafc;
        }}
        QLineEdit:focus {{ border: 1px solid #6366f1; background-color: #ffffff; }}
    """,
}
