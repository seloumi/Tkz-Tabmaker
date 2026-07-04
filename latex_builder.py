"""LaTeX code generation and building for tkz-tab tables."""

import logging
from typing import Optional
from PyQt6.QtGui import QColor

from utils import escape_latex_special_chars, validate_latex_math_mode
from constants import DEFAULT_LGT, DEFAULT_DELTACL, DEFAULT_ESPCL, HATCH_PATTERN

logger = logging.getLogger(__name__)


class LatexBuilder:
    """Builder for constructing LaTeX tkz-tab table code.
    
    Handles validation, escaping, and formatting of LaTeX code generation.
    """

    def __init__(self) -> None:
        """Initialize the LaTeX builder."""
        self.code_lines: list[str] = []
        logger.debug("LatexBuilder initialized")

    def reset(self) -> None:
        """Clear all code lines."""
        self.code_lines.clear()
        logger.debug("LatexBuilder reset")

    def add_line(self, line: str) -> None:
        """Add a code line.
        
        Args:
            line: Line of code to add
        """
        self.code_lines.append(line)

    def add_color_definition(self, color_name: str, color: QColor) -> None:
        """Add a LaTeX color definition.
        
        Args:
            color_name: Name for the color variable
            color: QColor object
        """
        if color.name().lower() == "#ffffff":
            return  # Skip white (default)

        hex_color = color.name().upper().replace("#", "")
        line = f"\\definecolor{{{color_name}Custom}}{{HTML}}{{{hex_color}}}"
        self.add_line(line)
        logger.debug(f"Added color definition: {color_name} = {hex_color}")

    def add_tikzset(self, tikzset_content: str) -> None:
        """Add a tikzset style definition.
        
        Args:
            tikzset_content: tikzset style content
        """
        if tikzset_content.strip():
            line = f"\\tikzset{{{tikzset_content}}}"
            self.add_line(line)
            logger.debug(f"Added tikzset: {tikzset_content[:50]}...")

    def add_begin_tikzpicture(self, options: str = "") -> None:
        """Add tikzpicture environment start.
        
        Args:
            options: Optional tikzpicture options
        """
        if options:
            self.add_line(f"\\begin{{tikzpicture}}{options}")
        else:
            self.add_line("\\begin{tikzpicture}")

    def add_end_tikzpicture(self) -> None:
        """Add tikzpicture environment end."""
        self.add_line("\\end{tikzpicture}")

    def add_tkz_tab_init(self, headers: str, x_values: str, options: str = "") -> None:
        """Add tkzTabInit command.
        
        Args:
            headers: Comma-separated header definitions
            x_values: Comma-separated x-axis values
            options: Optional options string
        """
        options_str = options if options else ""
        self.add_line(f"   \\tkzTabInit{options_str}")
        self.add_line(f"      {{{headers}}}")
        self.add_line(f"      {{{x_values}}}")
        logger.debug(f"Added tkzTabInit with {len(headers.split(','))} headers")

    def add_tkz_tab_line(self, items: list[str]) -> None:
        """Add tkzTabLine command.
        
        Args:
            items: List of cell values
        """
        # Filter out empty items for cleaner output
        filtered_items = [item for item in items if item]
        line = f"   \\tkzTabLine{{ {' , '.join(filtered_items)} }}"
        self.add_line(line)
        logger.debug(f"Added tkzTabLine with {len(filtered_items)} items")

    def add_tkz_tab_var(self, items: list[str]) -> None:
        """Add tkzTabVar command.
        
        Args:
            items: List of cell values
        """
        # Filter out empty items
        filtered_items = [item for item in items if item]
        line = f"   \\tkzTabVar{{ {' , '.join(filtered_items)} }}"
        self.add_line(line)
        logger.debug(f"Added tkzTabVar with {len(filtered_items)} items")

    def get_code(self) -> str:
        """Get the complete LaTeX code.
        
        Returns:
            Generated LaTeX code
        """
        return "\n".join(self.code_lines)

    @staticmethod
    def build_options_string(lgt: float = DEFAULT_LGT,
                            espcl: float = DEFAULT_ESPCL,
                            deltacl: float = DEFAULT_DELTACL,
                            nocadre: bool = False,
                            help_enabled: bool = False,
                            color_enabled: bool = False,
                            color_options: Optional[list[str]] = None) -> str:
        """Build the options string for tkzTabInit.
        
        Args:
            lgt: Table length parameter
            espcl: Column spacing parameter
            deltacl: Delta column parameter
            nocadre: Whether to disable borders
            help_enabled: Whether to enable help lines
            color_enabled: Whether to enable colors
            color_options: List of color option strings
            
        Returns:
            Formatted options string (e.g., "[lgt=2.0, nocadre]")
        """
        options_list = []

        if lgt != DEFAULT_LGT:
            options_list.append(f"lgt={lgt}")
        if espcl != DEFAULT_ESPCL:
            options_list.append(f"espcl={espcl}")
        if deltacl != DEFAULT_DELTACL:
            options_list.append(f"deltacl={deltacl}")
        if nocadre:
            options_list.append("nocadre")
        if help_enabled:
            options_list.append("help")
        if color_enabled:
            options_list.append("color")

        if color_options:
            options_list.extend(color_options)

        if options_list:
            return f"[{', '.join(options_list)}]"
        return ""

    @staticmethod
    def escape_cell_value(value: str) -> str:
        """Escape special characters in a cell value.
        
        Args:
            value: Raw cell value
            
        Returns:
            Escaped value safe for LaTeX
        """
        if not value:
            return value

        # Don't escape if already in math mode
        if value.startswith('$') and value.endswith('$'):
            if validate_latex_math_mode(value):
                return value

        return escape_latex_special_chars(value)

    @staticmethod
    def format_header(title: str, height: float) -> str:
        """Format a header string.
        
        Args:
            title: Header title
            height: Row height
            
        Returns:
            Formatted header
        """
        if height == int(height):
            height = int(height)
        return f"{title} / {height}"
