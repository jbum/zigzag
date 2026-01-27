#!/usr/bin/env python3
"""
Print Slants (Gokigen Naname) puzzles to PDF files.
Reads puzzle files in tab-separated format and generates PDFs with puzzles and answers.
"""

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch
from reportlab.lib.utils import simpleSplit
import argparse
import sys
from print_logo import print_logo


def parse_puzzle_line(line):
    """
    Parse a line from a puzzle file.
    Format: name\twidth\theight\tgivens\tsolution\t# comment
    or: name\twidth\theight\tgivens\t\t# comment (no solution)

    Lines starting with # are treated as comments.

    Returns dict with keys: name, width, height, givens, solution, comment
    or None if the line is a comment or invalid.
    """
    line = line.strip()
    if not line or line.startswith('#'):
        return None

    parts = line.split('\t')
    if len(parts) < 4:
        return None

    result = {
        'name': parts[0],
        'width': int(parts[1]),
        'height': int(parts[2]),
        'givens': parts[3],
        'solution': parts[4] if len(parts) > 4 and parts[4] else None,
        'comment': parts[5] if len(parts) > 5 else ''
    }

    return result


def decode_givens(givens_string, num_vertices):
    """
    Decode RLE-encoded givens string to vertex clues.

    Lowercase letters represent runs of unlabeled vertices (a=1, b=2, ..., z=26).
    Digits 0-4 represent clues.

    Returns list of clues (None for unlabeled, int for clues).
    """
    result = []
    for char in givens_string:
        if char.isdigit():
            result.append(int(char))
        elif char.islower():
            run_length = ord(char) - ord('a') + 1
            result.extend([None] * run_length)

    # Pad or truncate to match expected vertices
    if len(result) < num_vertices:
        result.extend([None] * (num_vertices - len(result)))
    elif len(result) > num_vertices:
        result = result[:num_vertices]

    return result


def draw_puzzle(canv, puzzle_data, available_width, available_height, ox, oy, show_answer=False):
    """
    Draw a single Slants puzzle with square cells.

    Args:
        canv: ReportLab canvas
        puzzle_data: Dict with 'name', 'width', 'height', 'givens', 'solution'
        available_width, available_height: Available space for the puzzle
        ox, oy: Origin position (top-left of available area)
        show_answer: If True, show solution; otherwise show only givens

    Returns:
        The y coordinate of the top of the grid (for positioning labels above it)
    """
    width = puzzle_data['width']
    height = puzzle_data['height']
    givens = puzzle_data['givens']
    solution = puzzle_data['solution']

    if show_answer and solution is None:
        return oy  # Can't show answer without solution

    # Circle radius is cell_size * 0.42 * 0.7 = cell_size * 0.294
    # Circles extend beyond grid edges, so account for this in sizing
    circle_overhang_factor = 0.42 * 0.7  # ~0.294

    # Calculate square cell size, accounting for circle overhang on all sides
    # Total width needed = width * cell_size + 2 * cell_size * circle_overhang_factor
    #                    = cell_size * (width + 2 * circle_overhang_factor)
    cell_width_by_width = available_width / (width + 2 * circle_overhang_factor)
    cell_height_by_height = available_height / (height + 2 * circle_overhang_factor)
    cell_size = min(cell_width_by_width, cell_height_by_height)

    # Calculate actual puzzle dimensions (grid only, not including circle overhang)
    puzzle_width = cell_size * width
    puzzle_height = cell_size * height

    # Total dimensions including circle overhang
    total_width = puzzle_width + 2 * cell_size * circle_overhang_factor
    total_height = puzzle_height + 2 * cell_size * circle_overhang_factor

    # Center the puzzle (including overhang) within the available area
    offset_x = (available_width - total_width) / 2 + cell_size * circle_overhang_factor
    offset_y = (available_height - total_height) / 2 + cell_size * circle_overhang_factor

    # Adjust origin to account for centering
    puzzle_ox = ox + offset_x
    puzzle_oy = oy - offset_y

    cell_width = cell_size
    cell_height = cell_size

    # Draw grid lines
    line_width = cell_width * 0.015  # 1.5% of cell width for thin lines
    thick_line_width = cell_width * 0.06  # 6% for thick border frame
    canv.setLineWidth(line_width)
    canv.setStrokeGray(0.5)  # Gray for thin lines

    # Draw thin lines
    for i in range(1, width):
        x = puzzle_ox + i * cell_width
        canv.line(x, puzzle_oy, x, puzzle_oy - puzzle_height)

    for i in range(1, height):
        y = puzzle_oy - i * cell_height
        canv.line(puzzle_ox, y, puzzle_ox + puzzle_width, y)

    # Draw thick border
    canv.setLineWidth(thick_line_width)
    canv.setStrokeGray(0)  # Black for border
    canv.rect(puzzle_ox, puzzle_oy - puzzle_height, puzzle_width, puzzle_height)

    # Decode vertex clues
    num_vertices = (width + 1) * (height + 1)
    vertex_clues = decode_givens(givens, num_vertices)

    # Draw solution diagonals first (if showing answer) so givens appear on top
    if show_answer and solution:
        diagonal_line_width = cell_width * 0.04  # 4% of cell width
        canv.setLineWidth(diagonal_line_width)
        canv.setStrokeGray(0)

        for y in range(height):
            for x in range(width):
                idx = y * width + x
                if idx < len(solution):
                    char = solution[idx]
                    # Cell corners
                    left = puzzle_ox + x * cell_width
                    right = puzzle_ox + (x + 1) * cell_width
                    top = puzzle_oy - y * cell_height
                    bottom = puzzle_oy - (y + 1) * cell_height

                    if char == '/':
                        # Slash: bottom-left to top-right
                        canv.line(left, bottom, right, top)
                    elif char == '\\':
                        # Backslash: top-left to bottom-right
                        canv.line(left, top, right, bottom)

    # Draw vertex clues (at intersections) with circles behind them
    font_size = cell_width * 0.42  # Slightly larger font
    circle_radius = font_size * 0.7  # Circle radius slightly larger than font
    circle_line_width = cell_width * 0.02  # Circle outline thickness

    for vy in range(height + 1):
        for vx in range(width + 1):
            idx = vy * (width + 1) + vx
            clue = vertex_clues[idx]
            if clue is not None:
                # Position at vertex intersection
                cx = puzzle_ox + vx * cell_width
                cy = puzzle_oy - vy * cell_height

                # Draw white-filled circle with black outline
                canv.setLineWidth(circle_line_width)
                canv.setStrokeGray(0)  # Black outline
                canv.setFillGray(1)  # White fill
                canv.circle(cx, cy, circle_radius, stroke=1, fill=1)

                # Draw the number
                canv.setFont('Helvetica-Bold', font_size)
                canv.setFillGray(0)  # Black text
                canv.drawCentredString(cx, cy - font_size * 0.35, str(clue))

    # Return the top y coordinate including circle overhang for positioning labels
    # Add circle_radius (for top-left corner circle) plus padding
    circle_radius = cell_size * circle_overhang_factor
    return puzzle_oy + circle_radius + 4  # 4 points extra padding


def main():
    parser = argparse.ArgumentParser(description='Print Slants puzzles to PDF')
    parser.add_argument('input_file', help='Input puzzle file (tab-separated format)')
    parser.add_argument('-o', '--output', help='Output PDF file (default: input filename with .pdf extension)')
    parser.add_argument('--pagesize', choices=['letter', 'A4'], default='letter',
                       help='Page size (default: letter)')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Verbose output')
    parser.add_argument('--puzzles-per-page', type=int, default=4,
                       help='Number of puzzles per page (default: 4)')
    parser.add_argument('--answers-per-page', type=int, default=12,
                       help='Number of answers per page (default: 12)')
    parser.add_argument('-n', '--nbr_to_print', type=int, default=None,
                       help='Maximum number of puzzles to print')
    parser.add_argument('-ofst', type=int, default=1,
                       help='Puzzle number to start at (1-based, default: 1)')

    args = parser.parse_args()

    # Determine output filename
    if args.output:
        output_file = args.output
    else:
        if args.input_file.endswith('.txt'):
            output_file = args.input_file[:-4] + '.pdf'
        else:
            output_file = args.input_file + '.pdf'

    # Read puzzles
    puzzles = []
    with open(args.input_file, 'r') as f:
        for line in f:
            puzzle = parse_puzzle_line(line)
            if puzzle:
                puzzles.append(puzzle)

    if not puzzles:
        print(f"No puzzles found in {args.input_file}", file=sys.stderr)
        sys.exit(1)

    # Apply offset and limit
    start_idx = args.ofst - 1  # Convert to 0-based
    if start_idx < 0:
        start_idx = 0
    if start_idx >= len(puzzles):
        print(f"Offset {args.ofst} is beyond the number of puzzles ({len(puzzles)})",
              file=sys.stderr)
        sys.exit(1)

    puzzles = puzzles[start_idx:]

    if args.nbr_to_print is not None:
        puzzles = puzzles[:args.nbr_to_print]

    if args.verbose:
        print(f"Loaded {len(puzzles)} puzzles from {args.input_file} (starting at puzzle {args.ofst})")

    # Set up page size
    if args.pagesize == 'letter':
        page_width, page_height = letter
    else:
        page_width, page_height = A4

    # Create PDF canvas
    c = canvas.Canvas(output_file, pagesize=(page_width, page_height))

    # Configuration
    margin = 0.5 * inch
    logo_height = 0.4 * inch
    title_height = 0.3 * inch
    title_bottom_spacing = 10  # Space below title baseline

    # Calculate puzzle grid layout
    puzzles_per_page = args.puzzles_per_page
    answers_per_page = args.answers_per_page

    # For puzzles: arrange in a grid
    import math
    puzzles_across = int(math.ceil(math.sqrt(puzzles_per_page)))
    puzzles_down = int(math.ceil(puzzles_per_page / puzzles_across))

    # For answers: arrange in a grid
    answers_across = int(math.ceil(math.sqrt(answers_per_page)))
    answers_down = int(math.ceil(answers_per_page / answers_across))

    # Available space on page
    total_available_width = page_width - 2 * margin

    # Calculate title and logo positions
    title_y = page_height - margin - logo_height - 10  # Title baseline
    logo_top = margin + logo_height  # Approximate bottom of logo area
    puzzle_space_top = title_y - title_bottom_spacing  # Top of puzzle area
    puzzle_space_bottom = logo_top + margin  # Bottom of puzzle area

    # Total vertical space available for puzzles (between title and logo)
    total_puzzle_space = puzzle_space_top - puzzle_space_bottom

    # Calculate puzzle/answer area sizes (these will be adjusted for centering)
    puzzle_area_width = (total_available_width / puzzles_across) * 0.9  # 90% of space, with gaps
    answer_area_width = (total_available_width / answers_across) * 0.9

    # Instructions text for Slants
    instructions_text = ("Fill each cell with a diagonal line (/ or \\). "
                        "The numbers at the intersections indicate how many diagonals "
                        "touch that corner. The diagonal lines must not form a closed loop.")

    logo_width = 150  # Approximate logo width

    # Draw puzzle pages
    puzzle_idx = 0
    while puzzle_idx < len(puzzles):
        # Instructions and logo at bottom
        c.setFont('Helvetica', 9)
        c.setFillGray(0)
        # Position instructions to the left of the logo
        instructions_x = page_width - margin - logo_width - 10  # 10 points gap before logo
        instructions_y = margin + logo_height
        # Wrap text to fit in available space
        instructions_lines = simpleSplit(instructions_text, 'Helvetica', 9,
                                         instructions_x - margin)
        for i, line in enumerate(instructions_lines):
            c.drawString(margin, instructions_y - i * 12, line)

        # Logo at bottom right
        print_logo(c, page_width, page_height, page_width - margin, page_height - margin - 20, justify='right')

        # Title
        c.setFont('Helvetica-Bold', 18)
        c.setFillGray(0)
        c.drawCentredString(page_width / 2, title_y, 'Zigzag Puzzles')

        # Calculate puzzle area height based on available space
        puzzle_area_height = total_puzzle_space / puzzles_down * 0.9

        # Calculate starting y position to center the puzzle grid
        total_grid_height = puzzle_area_height * puzzles_down
        extra_space = total_puzzle_space - total_grid_height
        grid_start_y = puzzle_space_top - extra_space / 2

        # Draw puzzles in grid
        for gy in range(puzzles_down):
            for gx in range(puzzles_across):
                if puzzle_idx >= len(puzzles):
                    break

                puzzle = puzzles[puzzle_idx]
                # Calculate position of puzzle area (top-left corner)
                px = margin + gx * (total_available_width / puzzles_across) + (total_available_width / puzzles_across - puzzle_area_width) / 2
                py = grid_start_y - gy * puzzle_area_height

                # Draw puzzle
                grid_top_y = draw_puzzle(c, puzzle, puzzle_area_width, puzzle_area_height, px, py, show_answer=False)

                # Puzzle number
                original_puzzle_num = start_idx + puzzle_idx + 1
                c.setFont('Helvetica', 10)
                c.drawString(px, grid_top_y + 2, f"#{original_puzzle_num}")

                puzzle_idx += 1

            if puzzle_idx >= len(puzzles):
                break

        c.showPage()

    # Draw answer pages
    answer_idx = 0
    while answer_idx < len(puzzles):
        # Instructions and logo at bottom
        c.setFont('Helvetica', 9)
        c.setFillGray(0)
        instructions_x = page_width - margin - logo_width - 10
        instructions_y = margin + logo_height
        instructions_lines = simpleSplit(instructions_text, 'Helvetica', 9,
                                         instructions_x - margin)
        for i, line in enumerate(instructions_lines):
            c.drawString(margin, instructions_y - i * 12, line)

        # Logo at bottom right
        print_logo(c, page_width, page_height, page_width - margin, page_height - margin - 20, justify='right')

        # Title
        c.setFont('Helvetica-Bold', 18)
        c.setFillGray(0)
        c.drawCentredString(page_width / 2, title_y, 'Zigzag Answers')

        # Calculate answer area height based on available space
        answer_area_height = total_puzzle_space / answers_down * 0.9

        # Calculate starting y position to center the answer grid
        total_grid_height = answer_area_height * answers_down
        extra_space = total_puzzle_space - total_grid_height
        grid_start_y = puzzle_space_top - extra_space / 2

        # Draw answers in grid
        for gy in range(answers_down):
            for gx in range(answers_across):
                if answer_idx >= len(puzzles):
                    break

                puzzle = puzzles[answer_idx]
                if puzzle['solution'] is None:
                    answer_idx += 1
                    continue

                # Calculate position of answer area (top-left corner)
                px = margin + gx * (total_available_width / answers_across) + (total_available_width / answers_across - answer_area_width) / 2
                py = grid_start_y - gy * answer_area_height

                # Draw answer
                grid_top_y = draw_puzzle(c, puzzle, answer_area_width, answer_area_height, px, py, show_answer=True)

                # Answer number
                original_answer_num = start_idx + answer_idx + 1
                c.setFont('Helvetica', 10)
                c.drawString(px, grid_top_y + 2, f"#{original_answer_num}")

                answer_idx += 1

            if answer_idx >= len(puzzles):
                break

        c.showPage()

    c.save()
    print(f"Wrote {len(puzzles)} puzzles to {output_file}")


if __name__ == '__main__':
    main()
