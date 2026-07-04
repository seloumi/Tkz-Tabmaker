"""Preview window for displaying compiled LaTeX table output."""

import logging
from typing import Optional
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel

from constants import DEFAULT_FONT_FAMILY

logger = logging.getLogger(__name__)


class PreviewWindow(QWidget):
    """Window for displaying compiled LaTeX table previews.
    
    Shows status messages and rendered table images.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize the preview window.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.setWindowTitle("Live Table Preview")
        self.setStyleSheet(f"QWidget {{ background-color: #ffffff; color: #334155; font-family: '{DEFAULT_FONT_FAMILY}'; }}")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)

        self.preview_label = QLabel("Compiling LaTeX...")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setWordWrap(True)
        self.preview_label.setStyleSheet("color: #94a3b8; font-style: italic; background-color: #ffffff; padding: 10px;")

        layout.addWidget(self.preview_label)
        self.setLayout(layout)
        logger.debug("PreviewWindow initialized")

    def set_status_text(self, text: str) -> None:
        """Display a status message.
        
        Args:
            text: Status text to display
        """
        self.preview_label.setPixmap(QPixmap())
        self.preview_label.setText(text)
        self.preview_label.setStyleSheet("color: #94a3b8; font-style: italic; background-color: #ffffff;")
        self.resize(350, 150)
        logger.info(f"Preview status: {text}")

    def show_pixmap(self, pixmap: QPixmap) -> None:
        """Display a pixmap image.
        
        Args:
            pixmap: QPixmap to display
        """
        self.preview_label.setPixmap(pixmap)
        self.preview_label.setStyleSheet("background-color: #ffffff; border: none;")
        self.preview_label.adjustSize()
        self.adjustSize()
        logger.info("Pixmap displayed in preview window")
