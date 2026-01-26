"""
Brute Force Solver for Slants (Gokigen Naname) puzzles.
Uses production rules plus stack-based backtracking.
"""

import sys
import time

from slants_board import Board, SolverDebugError, UNKNOWN, SLASH, BACKSLASH
from slants_rules import (
    rule_corner_zero,
    rule_corner_four,
    rule_clue_finish_a,
    rule_clue_finish_b,
    rule_no_loops,
    rule_forced_solution_avoidance,
    rule_loop_avoidance_2,
    rule_edge_clue_constraints,
    rule_adjacent_ones,
    rule_adjacent_threes,
    rule_v_pattern_with_three,
    rule_border_two_v_shape,
    rule_single_path_extension,
)


# Rules used by BF solver (same as PR solver)
RULES = [
    ("corner_zero", 1, rule_corner_zero),
    ("corner_four", 1, rule_corner_four),
    ("clue_finish_b", 1, rule_clue_finish_b),
    ("clue_finish_a", 2, rule_clue_finish_a),
    ("no_loops", 2, rule_no_loops),
    ("edge_clue_constraints", 2, rule_edge_clue_constraints),
    ("border_two_v_shape", 3, rule_border_two_v_shape),
    ("single_path_extension", 3, rule_single_path_extension),
    ("forced_solution_avoidance", 5, rule_forced_solution_avoidance),
    ("loop_avoidance_2", 5, rule_loop_avoidance_2),
    ("v_pattern_with_three", 6, rule_v_pattern_with_three),
    ("adjacent_ones", 8, rule_adjacent_ones),
    ("adjacent_threes", 8, rule_adjacent_threes),
]


def apply_rules_until_stuck(board, debug=False):
    """
    Apply rules repeatedly until no more progress can be made.
    Returns the total work score.
    """
    total_work_score = 0
    max_iterations = 1000
    iteration = 0

    while iteration < max_iterations:
        iteration += 1

        # Check if solved
        if board.is_solved():
            if debug:
                print(f"  [Rules] Solved at iteration {iteration}")
            break

        # Check for validity
        if not board.is_valid():
            if debug:
                print(f"  [Rules] Invalid state at iteration {iteration}")
            break

        # Try each rule in order
        made_progress = False
        for name, score, rule_func in RULES:
            try:
                if rule_func(board):
                    total_work_score += score
                    made_progress = True
                    if debug:
                        print(f"  [Rules] Applied {name} (score={score}, iteration={iteration})")
                    break
            except SolverDebugError as e:
                if debug:
                    print(f"  [Rules] ERROR: Rule '{name}' made incorrect move: {e}")
                raise
            except ValueError as e:
                # Loop or other error
                if debug:
                    print(f"  [Rules] Error in {name}: {e}")
                break

        if not made_progress:
            if debug:
                print(f"  [Rules] Stuck at iteration {iteration}")
            break

    return total_work_score


def pick_best_cell(board):
    """
    Pick the best cell for branching.
    Prioritizes cells adjacent to clued vertices with tight constraints.
    """
    unknown_cells = board.get_unknown_cells()
    if not unknown_cells:
        return None

    def cell_score(cell):
        """
        Score a cell by how constrained it is.
        Higher score = more constrained = better to try first.
        """
        score = 0
        corners = board.get_cell_corners(cell)

        for corner in corners:
            if corner is None:
                continue
            if corner.clue is None:
                continue

            current, unknown = board.count_touches(corner)
            clue = corner.clue

            # How close is this vertex to being finished?
            remaining_needed = clue - current
            remaining_slots = unknown

            # Tight constraints are good
            if remaining_needed == remaining_slots:
                score += 100  # All remaining must touch
            elif remaining_needed == 0:
                score += 100  # All remaining must avoid
            elif remaining_slots > 0:
                # Preference for vertices that are nearly determined
                score += 50 / remaining_slots

        return score

    # Sort by score descending
    unknown_cells.sort(key=cell_score, reverse=True)
    return unknown_cells[0]


def get_valid_values(board, cell):
    """
    Get valid values for a cell, checking for loops and vertex constraints.
    Returns list of (value, priority) tuples, sorted by priority.
    """
    valid = []

    for value in [SLASH, BACKSLASH]:
        # Check if placing this value would form a loop
        if board.would_form_loop(cell, value):
            continue

        # Check if this would violate any vertex clue
        # (make a clue exceed its limit)
        x, y = cell.x, cell.y
        tl = board.get_vertex(x, y)
        tr = board.get_vertex(x + 1, y)
        bl = board.get_vertex(x, y + 1)
        br = board.get_vertex(x + 1, y + 1)

        # SLASH touches tr and bl
        # BACKSLASH touches tl and br
        if value == SLASH:
            touches = [tr, bl]
        else:
            touches = [tl, br]

        is_valid = True
        priority = 0

        for corner in touches:
            if corner and corner.clue is not None:
                current, _ = board.count_touches(corner)
                if current >= corner.clue:
                    # Would exceed clue
                    is_valid = False
                    break
                # Bonus for filling a needed slot
                priority += 10

        if is_valid:
            valid.append((value, priority))

    # Sort by priority descending
    valid.sort(key=lambda x: -x[1])
    return [v for v, _ in valid]


def solve(givens_string, width=None, height=None, verbose=False, known_solution=None,
          for_generation=False):
    """
    Solve a Slants puzzle using brute-force backtracking.

    Args:
        givens_string: RLE-encoded vertex clues
        width: Width of the puzzle (number of cell columns)
        height: Height of the puzzle (number of cell rows)
        verbose: If True, print progress information
        known_solution: If provided, solver will detect incorrect moves during initial rule application
        for_generation: Ignored by BF solver (included for API compatibility)

    Returns:
        Tuple of (status, solution_string, work_score) where:
        - status is "solved", "unsolved", or "mult"
        - solution_string is the board state
        - work_score is cumulative score
    """
    if width is None or height is None:
        raise ValueError("Width and height must be specified for Slants puzzles")

    # Create board
    board = Board(width, height, givens_string, known_solution=known_solution)

    debug = verbose

    if debug:
        print(f"\n{'='*60}")
        print(f"Starting brute-force solve")
        print(f"Givens: {givens_string}")
        print(f"Size: {width}x{height}")
        print(f"{'='*60}\n")

    # Brute-force search with backtracking
    start_time = time.time()

    solutions = []
    stack = [(board.save_state(), None)]  # (state, eliminated_choice)
    total_work_score = 0
    search_depth = 0
    max_depth = 0
    backtrack_count = 0
    iterations = 0
    push_pop_score = 0  # Track stack operations

    while stack and len(solutions) < 2:
        iterations += 1
        state, eliminated_value = stack.pop()
        board.restore_state(state)
        push_pop_score += 1  # Count pop

        # Track depth
        if eliminated_value is None:
            search_depth = 0
        else:
            search_depth += 1
            max_depth = max(max_depth, search_depth)

        # Apply rules
        try:
            work_score = apply_rules_until_stuck(board, debug=debug and search_depth < 3)
            total_work_score += work_score
        except SolverDebugError as e:
            if debug:
                print(f"\n*** DEBUG ERROR during solve ***")
                print(str(e))
            return "unsolved", board.to_solution_string(), 0
        except ValueError:
            # Loop error during rule application
            backtrack_count += 1
            continue

        # Disable debug checking after first iteration
        if eliminated_value is None and known_solution:
            board.disable_debug_checking()

        # Check validity
        if not board.is_valid():
            backtrack_count += 1
            if debug and search_depth < 3:
                print(f"  [Backtrack] Invalid state")
            continue

        # Check if solved
        if board.is_solved():
            if board.is_valid_solution():
                solution = board.to_solution_string()
                solutions.append(solution)
                if debug:
                    print(f"  [SOLUTION FOUND] Solution #{len(solutions)}")
                continue
            else:
                backtrack_count += 1
                if debug and search_depth < 3:
                    print(f"  [Backtrack] Invalid solution")
                continue

        # Choose cell for branching
        cell = pick_best_cell(board)
        if cell is None:
            backtrack_count += 1
            continue

        # Get valid values
        valid_values = get_valid_values(board, cell)

        if not valid_values:
            backtrack_count += 1
            if debug and search_depth < 3:
                print(f"  [Backtrack] No valid values for cell ({cell.x},{cell.y})")
            continue

        if debug and search_depth < 3:
            val_str = ', '.join('/' if v == SLASH else '\\' for v in valid_values)
            print(f"  [Branch] Cell ({cell.x},{cell.y}), values: {val_str}")

        # Push states for each valid value
        saved_state = board.save_state()
        for value in reversed(valid_values):
            board.restore_state(saved_state)
            try:
                board.place_value(cell, value)
                stack.append((board.save_state(), value))
                push_pop_score += 1  # Count push
            except ValueError:
                # Would form loop - skip
                pass
        board.restore_state(saved_state)

    # Determine status
    if len(solutions) >= 2:
        status = "mult"
    elif len(solutions) == 1:
        status = "solved"
    else:
        status = "unsolved"

    # Get the board state
    if len(solutions) == 1:
        solution_string = solutions[0]
    else:
        solution_string = board.to_solution_string()

    # Add push/pop score to total (weighted)
    total_work_score += push_pop_score * 2

    elapsed_time = time.time() - start_time

    if debug:
        print(f"\n{'='*60}")
        print(f"Search complete:")
        print(f"  Status: {status}")
        print(f"  Solutions found: {len(solutions)}")
        print(f"  Iterations: {iterations}")
        print(f"  Elapsed time: {elapsed_time:.2f}s")
        print(f"  Max search depth: {max_depth}")
        print(f"  Backtracks: {backtrack_count}")
        print(f"  Push/pop operations: {push_pop_score}")
        print(f"  Total work score: {total_work_score}")
        print(f"{'='*60}\n")

    if verbose:
        print(f"Final board ({status}):")
        print(board)
        print()
        print(f"Solution string: {solution_string}")

    return status, solution_string, total_work_score


if __name__ == "__main__":
    # Test with the 8x8 puzzle from Simon Tatham's site
    width, height = 8, 8
    givens = "c120a0b21h3a2114f3a2b2a4b2110a1a1b1c2132d1b1a33a1a1c0b"

    print("Testing solver_BF.py")
    print("=" * 50)
    print(f"Puzzle: {width}x{height}")
    print(f"Givens: {givens}")
    print()

    # Allow command line override
    if len(sys.argv) >= 4:
        width = int(sys.argv[1])
        height = int(sys.argv[2])
        givens = sys.argv[3]
        print(f"Using command line puzzle: {width}x{height}")
        print(f"Givens: {givens}")
        print()

    status, solution, work_score = solve(givens, width, height, verbose=True)

    print()
    print("=" * 50)
    print(f"Status: {status}")
    print(f"Work score: {work_score}")

    if status == "solved":
        print("\nSUCCESS - Puzzle solved!")
    elif status == "mult":
        print("\nMultiple solutions found.")
    else:
        print("\nPuzzle not solved.")
