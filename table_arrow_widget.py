"""Custom QTableWidget with arrow drawing capabilities."""

from PyQt6.QtCore import Qt, QPoint, QRect
from PyQt6.QtGui import QPainter, QPen, QColor, QPolygon, QBrush
from PyQt6.QtWidgets import QTableWidget, QAbstractItemView


class Arrow:
    """Represents an arrow on the table."""
    
    def __init__(self, start_row, start_col, end_row, end_col, arrow_type="down", color=QColor(0, 0, 255)):
        self.start_row = start_row
        self.start_col = start_col
        self.end_row = end_row
        self.end_col = end_col
        self.arrow_type = arrow_type  # "down", "up", "curved_down", "curved_up"
        self.color = color
        self.width = 2
        self.arrow_size = 15
    
    def draw(self, painter, table_widget):
        """Draw the arrow on the painter."""
        # Get cell rectangles
        start_rect = table_widget.cellRect(self.start_row, self.start_col)
        end_rect = table_widget.cellRect(self.end_row, self.end_col)
        
        if not start_rect.isValid() or not end_rect.isValid():
            return
        
        # Get table positions relative to viewport
        table_offset = table_widget.pos()
        
        # Calculate start and end points (center bottom/top of cells)
        if self.arrow_type in ["down", "curved_down"]:
            start_point = QPoint(
                start_rect.center().x() + table_offset.x(),
                start_rect.bottom() + table_offset.y()
            )
            end_point = QPoint(
                end_rect.center().x() + table_offset.x(),
                end_rect.top() + table_offset.y()
            )
        else:  # up or curved_up
            start_point = QPoint(
                start_rect.center().x() + table_offset.x(),
                start_rect.top() + table_offset.y()
            )
            end_point = QPoint(
                end_rect.center().x() + table_offset.x(),
                end_rect.bottom() + table_offset.y()
            )
        
        # Set pen
        pen = QPen(self.color)
        pen.setWidth(self.width)
        painter.setPen(pen)
        
        # Draw line
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        
        if "curved" in self.arrow_type:
            # Draw curved arrow using a path
            from PyQt6.QtGui import QPainterPath
            path = QPainterPath()
            path.moveTo(start_point)
            
            # Calculate control points for curve
            mid_y = (start_point.y() + end_point.y()) / 2
            control_x = start_point.x() + 50
            
            path.cubicTo(control_x, start_point.y(), control_x, end_point.y(), end_point.x(), end_point.y())
            painter.drawPath(path)
        else:
            # Draw straight line
            painter.drawLine(start_point, end_point)
        
        # Draw arrowhead
        self._draw_arrowhead(painter, start_point, end_point)
    
    def _draw_arrowhead(self, painter, start_point, end_point):
        """Draw an arrowhead at the end point."""
        import math
        
        # Calculate angle
        dx = end_point.x() - start_point.x()
        dy = end_point.y() - start_point.y()
        angle = math.atan2(dy, dx)
        
        # Arrowhead points
        arrow_p1 = QPoint(
            int(end_point.x() - self.arrow_size * math.cos(angle - math.pi / 6)),
            int(end_point.y() - self.arrow_size * math.sin(angle - math.pi / 6))
        )
        arrow_p2 = QPoint(
            int(end_point.x() - self.arrow_size * math.cos(angle + math.pi / 6)),
            int(end_point.y() - self.arrow_size * math.sin(angle + math.pi / 6))
        )
        
        # Draw filled arrowhead
        arrowhead = QPolygon([end_point, arrow_p1, arrow_p2])
        painter.setBrush(QBrush(self.color))
        painter.drawPolygon(arrowhead)


class TableWidgetWithArrows(QTableWidget):
    """Custom QTableWidget that supports drawing arrows between cells."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.arrows = []
        self.is_drawing_arrow = False
        self.arrow_start_row = None
        self.arrow_start_col = None
        
        # Store arrow drawing parameters
        self.arrow_type = "down"
        self.arrow_color = QColor(0, 0, 255)
        
        # Enable custom painting
        self.setMouseTracking(True)
        self.viewport().installEventFilter(self)
    
    def add_arrow(self, start_row, start_col, end_row, end_col, arrow_type="down", color=None):
        """Add an arrow to the table."""
        if color is None:
            color = self.arrow_color
        
        arrow = Arrow(start_row, start_col, end_row, end_col, arrow_type, color)
        self.arrows.append(arrow)
        self.viewport().update()
    
    def remove_arrow(self, arrow_index):
        """Remove an arrow by index."""
        if 0 <= arrow_index < len(self.arrows):
            self.arrows.pop(arrow_index)
            self.viewport().update()
    
    def clear_arrows(self):
        """Clear all arrows."""
        self.arrows.clear()
        self.viewport().update()
    
    def set_arrow_type(self, arrow_type):
        """Set the arrow type for new arrows (down, up, curved_down, curved_up)."""
        self.arrow_type = arrow_type
    
    def set_arrow_color(self, color):
        """Set the arrow color for new arrows."""
        self.arrow_color = color
    
    def get_arrow_count(self):
        """Get the number of arrows."""
        return len(self.arrows)
    
    def paintEvent(self, event):
        """Override paintEvent to draw arrows on top of table."""
        super().paintEvent(event)
        
        # Draw arrows
        painter = QPainter(self.viewport())
        for arrow in self.arrows:
            arrow.draw(painter, self)
    
    def mousePressEvent(self, event):
        """Handle mouse press for arrow drawing."""
        super().mousePressEvent(event)
        
        if event.button() == Qt.MouseButton.RightButton:
            # Start arrow drawing with right click
            index = self.indexAt(event.pos())
            if index.isValid():
                self.is_drawing_arrow = True
                self.arrow_start_row = index.row()
                self.arrow_start_col = index.column()
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release for arrow drawing."""
        if self.is_drawing_arrow and event.button() == Qt.MouseButton.RightButton:
            self.is_drawing_arrow = False
            
            # Get the end cell
            index = self.indexAt(event.pos())
            if index.isValid():
                end_row = index.row()
                end_col = index.column()
                
                # Add arrow if valid
                if (end_row != self.arrow_start_row or end_col != self.arrow_start_col):
                    self.add_arrow(
                        self.arrow_start_row,
                        self.arrow_start_col,
                        end_row,
                        end_col,
                        self.arrow_type,
                        self.arrow_color
                    )
        
        super().mouseReleaseEvent(event)
