"""State management for undo/redo functionality."""

import logging
from typing import Optional, Any, Dict, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class CellInfo:
    """Information about a single cell state."""
    cell_type: str  # 'item', 'RowHeightWidget', 'TkzVarCellWidget'
    text: str = ""
    is_hatched: bool = False
    value: Optional[float] = None
    row_type: Optional[str] = None
    prefix: str = ""
    widget_data: Optional[Dict[str, Any]] = field(default_factory=dict)


@dataclass
class TableState:
    """Complete table state snapshot."""
    rows: int
    cols: int
    spin_columns: int
    spin_rows: int
    data: List[List[CellInfo]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary.
        
        Returns:
            Dictionary representation of state
        """
        return {
            "rows": self.rows,
            "cols": self.cols,
            "spin_columns": self.spin_columns,
            "spin_rows": self.spin_rows,
            "data": [[{"type": cell.cell_type, "text": cell.text, "is_hatched": cell.is_hatched,
                      "value": cell.value, "row_type": cell.row_type, "prefix": cell.prefix}
                     for cell in row] for row in self.data]
        }


class StateManager:
    """Manages undo/redo state history.
    
    Uses a command pattern-like approach with state snapshots.
    """

    def __init__(self, max_history: int = 50) -> None:
        """Initialize the state manager.
        
        Args:
            max_history: Maximum number of states to keep in history
        """
        self.undo_stack: List[TableState] = []
        self.redo_stack: List[TableState] = []
        self.max_history = max_history
        self.is_processing = False
        logger.debug(f"StateManager initialized with max_history={max_history}")

    def save_state(self, state: TableState) -> None:
        """Save a new state to the undo stack.
        
        Args:
            state: TableState to save
        """
        if self.is_processing:
            return

        self.undo_stack.append(state)
        self.redo_stack.clear()

        # Limit history size
        if len(self.undo_stack) > self.max_history:
            self.undo_stack.pop(0)

        logger.debug(f"State saved. Undo stack size: {len(self.undo_stack)}")

    def undo(self) -> Optional[TableState]:
        """Undo the last operation.
        
        Returns:
            Previous state if available, None otherwise
        """
        if len(self.undo_stack) <= 1:
            return None

        current_state = self.undo_stack.pop()
        self.redo_stack.append(current_state)
        previous_state = self.undo_stack[-1]

        logger.debug(f"Undo performed. Undo stack size: {len(self.undo_stack)}")
        return previous_state

    def redo(self) -> Optional[TableState]:
        """Redo the last undone operation.
        
        Returns:
            Next state if available, None otherwise
        """
        if not self.redo_stack:
            return None

        state = self.redo_stack.pop()
        self.undo_stack.append(state)

        logger.debug(f"Redo performed. Undo stack size: {len(self.undo_stack)}")
        return state

    def can_undo(self) -> bool:
        """Check if undo is available.
        
        Returns:
            True if undo is available
        """
        return len(self.undo_stack) > 1

    def can_redo(self) -> bool:
        """Check if redo is available.
        
        Returns:
            True if redo is available
        """
        return len(self.redo_stack) > 0

    def clear_history(self) -> None:
        """Clear all undo/redo history."""
        self.undo_stack.clear()
        self.redo_stack.clear()
        logger.debug("History cleared")
