"""
Production Rule Solver for Slants (Gokigen Naname) puzzles.
"""

import sys
from slants_board import Board, SolverDebugError, UNKNOWN
from slants_rules import (
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
    rule_diagonal_ones,
    rule_trial_clue_violation,
    rule_one_step_lookahead,
)


# Rules Registry - rules are tried in order, from easiest/cheapest to hardest
# Format: (name, work_score, tier, rule_function)
# Tier: 1 = score < 8, 2 = score >= 8 and < 10, 3 = score >= 10
RULES = [
    ("clue_finish_b", 1, 1, rule_clue_finish_b),  # Has enough touches, fill avoiders
    ("clue_finish_a", 2, 1, rule_clue_finish_a),  # Needs all remaining to touch
    ("no_loops", 2, 1, rule_no_loops),
    ("edge_clue_constraints", 2, 2, rule_edge_clue_constraints),
    ("border_two_v_shape", 3, 2, rule_border_two_v_shape),
    # ("single_path_extension", 3, 2, rule_single_path_extension),  # Redundant, slows performance
    # ("forced_solution_avoidance", 5, 2, rule_forced_solution_avoidance),  # Redundant, slows performance
    ("loop_avoidance_2", 5, 2, rule_loop_avoidance_2),
    ("v_pattern_with_three", 6, 2, rule_v_pattern_with_three),
    ("adjacent_ones", 8, 2, rule_adjacent_ones),
    ("adjacent_threes", 8, 2, rule_adjacent_threes),
    # ("diagonal_ones", 8, 2, rule_diagonal_ones),  # Redundant, slows performance
    ("trial_clue_violation", 10, 3, rule_trial_clue_violation),
    ("one_step_lookahead", 15, 3, rule_one_step_lookahead),
]

# For puzzle generation, use max_tier=2 to exclude tier 3 backtracking rules
# (trial_clue_violation, one_step_lookahead) which are not human-solvable


def solve(givens_string, width=None, height=None, verbose=False,
          known_solution=None, for_generation=False, max_tier=10):
    """
    Solve a Slants puzzle using production rules.

    Args:
        givens_string: RLE-encoded vertex clues
        width: Width of the puzzle (number of cell columns)
        height: Height of the puzzle (number of cell rows)
        verbose: If True, print progress information
        known_solution: If provided, solver will detect incorrect moves
        for_generation: If True, use rules safe for puzzle generation
        max_tier: Maximum rule tier to use (1, 2, or 3). Default 10 uses all rules.

    Returns:
        Tuple of (status, solution_string, work_score, max_tier_used) where:
        - status is "solved" or "unsolved"
        - solution_string is the board state (/ and \\ characters, . for unknown)
        - work_score is cumulative score of all rules applied
        - max_tier_used is the highest tier of any rule that made progress
    """
    if width is None or height is None:
        raise ValueError("Width and height must be specified for Slants puzzles")

    # Create board
    board = Board(width, height, givens_string, known_solution=known_solution)

    # For generation, cap max_tier at 2 to exclude backtracking rules
    if for_generation:
        max_tier = min(max_tier, 2)

    # Filter rules by tier
    rules = [(name, score, tier, func) for name, score, tier, func in RULES if tier <= max_tier]

    # Main solving loop
    max_iterations = 1000
    iteration = 0
    status = None
    total_work_score = 0
    max_tier_used = 0
    debug_error = None

    while iteration < max_iterations:
        iteration += 1

        # Check if solved
        if board.is_solved():
            if board.is_valid_solution():
                status = "solved"
            else:
                status = "unsolved"  # All cells filled but invalid
            break

        # Try each rule in order
        made_progress = False
        for name, score, tier, rule_func in rules:
            try:
                if rule_func(board):
                    total_work_score += score
                    max_tier_used = max(max_tier_used, tier)
                    made_progress = True
                    if verbose:
                        print(f"  Rule '{name}' (tier {tier}) made progress (iteration {iteration})")
                    break  # Restart from first rule after progress
            except SolverDebugError as e:
                debug_error = f"Rule '{name}' made incorrect move: {e}"
                break
            except ValueError as e:
                # Loop detection error - shouldn't happen with valid rules
                debug_error = f"Rule '{name}' caused error: {e}"
                break

        if debug_error:
            if verbose:
                print(f"\n*** DEBUG ERROR at iteration {iteration} ***")
                print(debug_error)
            status = "unsolved"
            break

        # If no rule made progress, we're stuck
        if not made_progress:
            status = "unsolved"
            break

    if status is None:
        status = "unsolved"

    solution_string = board.to_solution_string()

    if verbose:
        print()
        print(f"Final board ({status}):")
        print(board)
        print()
        print(f"Solution string: {solution_string}")
        print(f"Work score: {total_work_score}")

        # Count solved vs unsolved cells
        unknown_count = len(board.get_unknown_cells())
        total_cells = len(board.cells)
        print(f"Cells: {total_cells - unknown_count}/{total_cells} solved")

    return status, solution_string, total_work_score, max_tier_used


if __name__ == "__main__":
    # Test with the 8x8 puzzle from Simon Tatham's site
    # https://www.chiark.greenend.org.uk/~sgtatham/puzzles/js/slant.html#8x8:c120a0b21h3a2114f3a2b2a4b2110a1a1b1c2132d1b1a33a1a1c0b

    width, height = 8, 8
    givens = "c120a0b21h3a2114f3a2b2a4b2110a1a1b1c2132d1b1a33a1a1c0b"

    print("Testing solver_PR.py")
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

    status, solution, work_score, max_tier = solve(givens, width, height, verbose=True)

    print()
    print("=" * 50)
    print(f"Status: {status}")
    print(f"Work score: {work_score}")
    print(f"Max tier used: {max_tier}")

    if status == "solved":
        print("\nSUCCESS - Puzzle solved!")
    else:
        print("\nPuzzle not fully solved with production rules.")
