#!/usr/bin/env python3
"""
Testing framework for Slants (Gokigen Naname) puzzle solver.
Reads puzzles from a testsuite file and attempts to solve them.
"""

import argparse
import importlib
import time
import sys

from slants_board import parse_puzzle_line, Board, UNKNOWN


def check_solution_valid(board, solution_string):
    """
    Verify that a solution string is valid for the given board.
    Returns (is_valid, error_msg).
    """
    expected_len = board.width * board.height
    if len(solution_string) != expected_len:
        return False, f"Length mismatch: got {len(solution_string)}, expected {expected_len}"

    # Check for unknown cells
    if '.' in solution_string:
        count = solution_string.count('.')
        return False, f"Contains {count} unsolved cells"

    return True, None


def display_side_by_side(board, width, height):
    """Display the board with ANSI colored output."""
    # ANSI color codes
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RESET = '\033[0m'

    print("Board state:")
    print(board)


def main():
    parser = argparse.ArgumentParser(
        description='Test Slants solver against a testsuite file'
    )
    parser.add_argument('input_file', help='Path to testsuite file')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Output testsuite-compatible lines with work scores')
    parser.add_argument('-d', '--debug', action='store_true',
                        help='Show colored side-by-side grid display for each puzzle')
    parser.add_argument('-f', '--filter', type=str, default=None,
                        help='Filter puzzles by partial name match')
    parser.add_argument('-n', type=int, default=None,
                        help='Maximum number of puzzles to test')
    parser.add_argument('-ofst', type=int, default=1,
                        help='Puzzle number to start at (1-based, default: 1)')
    parser.add_argument('-s', '--solver', type=str, default='PR',
                        choices=['PR', 'BF'],
                        help='Solver to use: PR (production rules) or BF (brute force)')
    parser.add_argument('-ou', '--output_unsolved', action='store_true',
                        help='Output list of unsolved puzzles (sorted by size)')

    args = parser.parse_args()

    # Dynamic import based on solver choice
    solver_module = importlib.import_module(f'solver_{args.solver}')
    solve = solver_module.solve

    # Read and parse testsuite file
    puzzles = []
    with open(args.input_file, 'r') as f:
        for line in f:
            puzzle = parse_puzzle_line(line)
            if puzzle:
                puzzles.append(puzzle)

    if not puzzles:
        print(f"No puzzles found in {args.input_file}", file=sys.stderr)
        sys.exit(1)

    # Apply filter if specified
    if args.filter:
        puzzles = [p for p in puzzles if args.filter in p['name']]
        if not puzzles:
            print(f"No puzzles matching filter '{args.filter}'", file=sys.stderr)
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

    if args.n is not None:
        puzzles = puzzles[:args.n]

    # Solve puzzles
    total_puzzles = len(puzzles)
    solved_count = 0
    unsolved_count = 0
    mult_count = 0
    total_work_score = 0
    unsolved_puzzles = []
    total_unsolved_squares = 0

    start_time = time.time()

    for i, puzzle in enumerate(puzzles):
        puzzle_num = start_idx + i + 1  # 1-based puzzle number

        # Show debug header if in debug mode
        if args.debug:
            print(f"\n{'='*60}")
            print(f"Puzzle {puzzle_num}: {puzzle['name']} ({puzzle['width']}x{puzzle['height']})")
            print(f"Givens: {puzzle['givens']}")
            print(f"{'='*60}")

        status, solution_or_partial, work_score = solve(
            puzzle['givens'],
            width=puzzle['width'],
            height=puzzle['height'],
            verbose=args.debug,
            known_solution=puzzle['answer'] if puzzle['answer'] else None
        )

        # Count unsolved squares
        unsolved_squares = solution_or_partial.count('.')
        total_unsolved_squares += unsolved_squares

        is_solved = (status == "solved")
        is_mult = (status == "mult")

        if is_solved:
            solved_count += 1
            total_work_score += work_score

            # Check against expected solution if available
            if puzzle['answer'] and solution_or_partial != puzzle['answer']:
                # Different solution - might be ok for puzzles with multiple solutions
                if args.debug:
                    print(f"NOTE: Solution differs from expected answer")
                    print(f"  Got:      {solution_or_partial}")
                    print(f"  Expected: {puzzle['answer']}")
        elif is_mult:
            mult_count += 1
            unsolved_puzzles.append(puzzle)
        else:
            unsolved_count += 1
            unsolved_puzzles.append(puzzle)

        # Show result in debug mode
        if args.debug:
            status_display = status.upper()
            print(f"\nStatus: {status_display}, Work score: {work_score}")
            if unsolved_squares > 0:
                print(f"Unsolved cells: {unsolved_squares}")

        if args.verbose:
            # Output testsuite-compatible line
            solution_str = solution_or_partial if is_solved else ''
            comment_parts = []
            if puzzle['comment']:
                comment_parts.append(puzzle['comment'])
            comment_parts.append(f"work_score={work_score}")
            if not is_solved:
                comment_parts.append(f"status={status}")
                if unsolved_squares > 0:
                    comment_parts.append(f"unsolved={unsolved_squares}")
            comment = ' '.join(comment_parts)

            print(f"{puzzle['name']}\t{puzzle['width']}\t{puzzle['height']}\t"
                  f"{puzzle['givens']}\t{solution_str}\t# {comment}")

    elapsed_time = time.time() - start_time

    # Print summary
    solved_pct = (solved_count / total_puzzles * 100) if total_puzzles > 0 else 0
    unsolved_pct = ((unsolved_count + mult_count) / total_puzzles * 100) if total_puzzles > 0 else 0

    if not args.verbose:
        print(f"\nInput file: {args.input_file}")
        print(f"Solver: {args.solver}")
        print(f"Puzzles tested: {total_puzzles}")
        print(f"Solved: {solved_count} ({solved_pct:.1f}%)")
        if mult_count > 0:
            print(f"Multiple solutions: {mult_count}")
        print(f"Unsolved: {unsolved_count} ({unsolved_pct:.1f}%)")
        print(f"Elapsed time: {elapsed_time:.3f}s")
        print(f"Total work score: {total_work_score}")
        if solved_count > 0:
            print(f"Average work score per solved puzzle: {total_work_score / solved_count:.1f}")
    else:
        # Print summary as comment at end
        print(f"# Summary: {solved_count}/{total_puzzles} ({solved_pct:.1f}%) solved, "
              f"time={elapsed_time:.3f}s, total_work_score={total_work_score}")

    # Output unsolved puzzles list if requested
    if args.output_unsolved and unsolved_puzzles:
        print()
        print("Unsolved puzzles (sorted by size):")
        unsolved_sorted = sorted(unsolved_puzzles,
                               key=lambda p: (p['width'] * p['height'], p['name']))
        for puzzle in unsolved_sorted:
            area = puzzle['width'] * puzzle['height']
            print(f"  {puzzle['name']}: {puzzle['width']}x{puzzle['height']} (area={area})")


if __name__ == '__main__':
    main()
