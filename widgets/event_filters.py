"""Custom event filters for advanced tooltip and interaction handling."""

import logging
from PyQt6.QtCore import Qt, QObject, QEvent, QPoint
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QToolTip
from constants import DEFAULT_FONT_FAMILY, TOOLTIP_STYLE_TEMPLATE

logger = logging.getLogger(__name__)


class SafeEventFilter(QObject):
    """Smart event filter for displaying tooltips next to the mouse cursor.
    
    This filter shows contextual tooltips when hovering over combo box items,
    safely handling show/hide events without conflicts.
    """

    def __init__(self, combo_widget, tooltips_dict: dict[str, str]) -> None:
        """Initialize the event filter.
        
        Args:
            combo_widget: The combo box widget to filter events for
            tooltips_dict: Dictionary mapping item text to descriptions
        """
        super().__init__(combo_widget)
        self.combo = combo_widget
        self.tooltips = tooltips_dict
        logger.debug(f"SafeEventFilter initialized with {len(tooltips_dict)} tooltips")

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """Handle events for tooltip display.
        
        Args:
            obj: The object that received the event
            event: The event to process
            
        Returns:
            True if event was handled, False otherwise
        """
        if event.type() in [QEvent.Type.MouseMove, QEvent.Type.HoverMove, QEvent.Type.ToolTip]:
            view = self.combo.view()
            if view and view.isVisible():
                try:
                    global_pos = QCursor.pos()
                    local_pos = view.mapFromGlobal(global_pos)
                    index = view.indexAt(local_pos)

                    if index.isValid():
                        item_text = self.combo.itemText(index.row())
                        desc = self.tooltips.get(item_text, "")
                        if desc:
                            styled_tip = TOOLTIP_STYLE_TEMPLATE.format(
                                font=DEFAULT_FONT_FAMILY,
                                key=item_text,
                                description=desc
                            )
                            QToolTip.showText(global_pos + QPoint(15, 15), styled_tip, view)
                            return True
                except Exception as e:
                    logger.error(f"Error in SafeEventFilter: {e}")
            return True

        elif event.type() in [QEvent.Type.Leave, QEvent.Type.Hide, QEvent.Type.MouseButtonPress]:
            QToolTip.hideText()

        return super().eventFilter(obj, event)


class LineEditTooltipFilter(QObject):
    """Event filter for displaying tooltips over text in a line edit widget.
    
    Shows contextual tooltips for keywords found in the text by character position.
    """

    def __init__(self, line_edit, tooltips_dict: dict[str, str]) -> None:
        """Initialize the event filter.
        
        Args:
            line_edit: The line edit widget to filter events for
            tooltips_dict: Dictionary mapping keyword text to descriptions
        """
        super().__init__(line_edit)
        self.line_edit = line_edit
        self.tooltips = tooltips_dict
        logger.debug(f"LineEditTooltipFilter initialized with {len(tooltips_dict)} tooltips")

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """Handle events for tooltip display in line edit.
        
        Args:
            obj: The object that received the event
            event: The event to process
            
        Returns:
            True if event was handled, False otherwise
        """
        if event.type() in [QEvent.Type.MouseMove, QEvent.Type.ToolTip]:
            try:
                global_pos = QCursor.pos()
                local_pos = self.line_edit.mapFromGlobal(global_pos)

                # Use font metrics to find character index under mouse
                fm = self.line_edit.fontMetrics()
                text = self.line_edit.text()

                # Account for internal line edit margins
                content_x = local_pos.x() - self.line_edit.contentsMargins().left() - 2

                # Find the character index
                char_idx = -1
                for i in range(len(text)):
                    prefix_width = fm.horizontalAdvance(text[:i + 1])
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
                        styled_tip = TOOLTIP_STYLE_TEMPLATE.format(
                            font=DEFAULT_FONT_FAMILY,
                            key=matched_key,
                            description=desc
                        )
                        QToolTip.showText(global_pos + QPoint(15, 15), styled_tip, self.line_edit)
                        return True

                QToolTip.hideText()
                return False

            except Exception as e:
                logger.error(f"Error in LineEditTooltipFilter: {e}")
                QToolTip.hideText()
                return False

        elif event.type() in [QEvent.Type.Leave, QEvent.Type.FocusOut]:
            QToolTip.hideText()

        return super().eventFilter(obj, event)
