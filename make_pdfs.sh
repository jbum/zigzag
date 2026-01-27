#!/bin/bash
# Regenerate all puzzle PDFs

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$SCRIPT_DIR/venv/bin/python3"

for puzzle_file in "$SCRIPT_DIR"/puzzledata/puzzles_*.txt; do
    echo "Generating PDF for $puzzle_file..."
    "$PYTHON" "$SCRIPT_DIR/print_puzzles_pdf.py" "$puzzle_file"
done

echo "Done."
