"""Utility helper functions for Tkz-Tabmaker."""

import logging
import contextlib
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def setup_logging(level: int = logging.INFO) -> None:
    """Configure logging for the application.
    
    Args:
        level: Logging level (default: logging.INFO)
    """
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('tkz_tabmaker.log')
        ]
    )


def cleanup_temp_file(filepath: str) -> None:
    """Safely remove a temporary file.
    
    Args:
        filepath: Path to file to remove
    """
    with contextlib.suppress(OSError):
        Path(filepath).unlink(missing_ok=True)


def cleanup_temp_files(base_path: str, extensions: list[str]) -> None:
    """Clean up multiple temporary files.
    
    Args:
        base_path: Base path without extension
        extensions: List of extensions to remove (e.g., ['.tex', '.log', '.pdf'])
    """
    for ext in extensions:
        cleanup_temp_file(f"{base_path}{ext}")
    logger.debug(f"Cleaned up temporary files: {base_path}.*")


def escape_latex_special_chars(text: str) -> str:
    """Escape LaTeX special characters in text.
    
    Args:
        text: Text to escape
        
    Returns:
        Escaped text safe for LaTeX
    """
    # Characters that need escaping in LaTeX
    replacements = {
        '\\': r'\textbackslash{}',
        '{': r'\{',
        '}': r'\}',
        '%': r'\%',
        '$': r'\$',
        '&': r'\&',
        '#': r'\#',
        '_': r'\_',
        '~': r'\textasciitilde{}',
        '^': r'\textasciicircum{}',
    }
    result = text
    for char, escaped in replacements.items():
        result = result.replace(char, escaped)
    return result


def validate_latex_math_mode(text: str) -> bool:
    """Validate that LaTeX math mode is properly balanced.
    
    Args:
        text: Text to validate
        
    Returns:
        True if math mode delimiters are balanced
    """
    # Simple check for balanced $ delimiters in math mode
    count_single = text.count('$')
    count_double = text.count('$$')
    # Each $$ counts as 2 $, so subtract them
    adjusted_count = count_single - (2 * count_double)
    return adjusted_count % 2 == 0


def format_float(value: float, decimals: int = 2) -> str:
    """Format a float value, removing trailing zeros.
    
    Args:
        value: Float value to format
        decimals: Number of decimal places
        
    Returns:
        Formatted string
    """
    if value == int(value):
        return str(int(value))
    formatted = f"{value:.{decimals}f}".rstrip('0').rstrip('.')
    return formatted


def parse_latex_error(stderr_output: str) -> list[str]:
    """Parse LaTeX compilation errors from stderr.
    
    Args:
        stderr_output: stderr output from pdflatex
        
    Returns:
        List of error messages
    """
    errors = []
    lines = stderr_output.split('\n')
    
    for i, line in enumerate(lines):
        if '!' in line or 'error' in line.lower():
            errors.append(line.strip())
            # Get the next line for context if available
            if i + 1 < len(lines):
                errors.append(lines[i + 1].strip())
    
    return errors if errors else ["Unknown compilation error"]


def get_alignment_from_prefix(prefix: str) -> str:
    """Determine vertical alignment from prefix character.
    
    Args:
        prefix: Prefix text (e.g., '+', '-', 'R')
        
    Returns:
        Alignment name ('top', 'bottom', or 'center')
    """
    if prefix and prefix[0] == '+':
        return 'top'
    elif prefix and prefix[0] == '-':
        return 'bottom'
    elif prefix and prefix[-1] == '+':
        return 'top'
    elif prefix and prefix[-1] == '-':
        return 'bottom'
    return 'center'
