#!/usr/bin/env python3
"""
Regenerate all puzzle PDFs with appropriate layout settings based on puzzle size.
"""

import subprocess
import sys
import re
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PYTHON = SCRIPT_DIR / "venv" / "bin" / "python3"
PUZZLE_DIR = SCRIPT_DIR / "puzzledata"
PDF_DIR = SCRIPT_DIR / "pdfs"


def get_puzzle_size(filename):
    """Extract puzzle dimensions from filename like 'puzzles_15x15.txt'."""
    match = re.search(r'(\d+)x(\d+)', filename)
    if match:
        return int(match.group(1)), int(match.group(2))
    return None, None


def main():
    puzzle_files = sorted(PUZZLE_DIR.glob("puzzles_*.txt"))

    if not puzzle_files:
        print("No puzzle files found in", PUZZLE_DIR)
        sys.exit(1)

    # Create output directory if it doesn't exist
    PDF_DIR.mkdir(exist_ok=True)

    for puzzle_file in puzzle_files:
        print(f"Generating PDF for {puzzle_file}...")

        width, height = get_puzzle_size(puzzle_file.name)

        # Output PDF to pdfs/ directory
        output_file = PDF_DIR / puzzle_file.with_suffix(".pdf").name

        cmd = [str(PYTHON), str(SCRIPT_DIR / "print_puzzles_pdf.py"), str(puzzle_file),
               "-o", str(output_file)]

        # Use different layout for larger puzzles
        if width and height and (width > 12 or height > 12):
            cmd.extend(["--puzzles-per-page", "1", "--answers-per-page", "6"])

        subprocess.run(cmd, check=True)

    print("Done.")


if __name__ == "__main__":
    main()
