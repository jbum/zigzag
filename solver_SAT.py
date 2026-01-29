"""
SAT-based Solver for Slants (Gokigen Naname) puzzles.
Uses production rules (tier 1-2) plus SAT solving (tier 3) for remaining cells.
"""

import sys
import time

from pysat.solvers import Solver as SATSolver
from pysat.card import CardEnc, EncType

from slants_board import Board, SolverDebugError, UNKNOWN, SLASH, BACKSLASH
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
    rule_dead_end_avoidance,
    rule_equivalence_classes,
    rule_vbitmap_propagation,
    rule_simon_unified,
)


# Rules used by SAT solver (tier 1-2 only, same as BF)
# Format: (name, work_score, tier, rule_function)
RULES = [
    ("clue_finish_b", 1, 1, rule_clue_finish_b),
    ("clue_finish_a", 2, 1, rule_clue_finish_a),
    ("no_loops", 2, 1, rule_no_loops),
    ("edge_clue_constraints", 2, 2, rule_edge_clue_constraints),
    ("border_two_v_shape", 3, 2, rule_border_two_v_shape),
    ("loop_avoidance_2", 5, 1, rule_loop_avoidance_2),
    ("v_pattern_with_three", 6, 2, rule_v_pattern_with_three),
    ("adjacent_ones", 8, 2, rule_adjacent_ones),
    ("adjacent_threes", 8, 2, rule_adjacent_threes),
    ("dead_end_avoidance", 9, 2, rule_dead_end_avoidance),
    ("equivalence_classes", 9, 2, rule_equivalence_classes),
    ("vbitmap_propagation", 9, 2, rule_vbitmap_propagation),
    ("simon_unified", 9, 2, rule_simon_unified),
]


def apply_rules_until_stuck(board, debug=False, rules=None):
    """
    Apply rules repeatedly until no more progress can be made.
    Returns tuple of (total_work_score, max_tier_used).
    """
    if rules is None:
        rules = RULES

    total_work_score = 0
    max_tier_used = 0
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
        for name, score, tier, rule_func in rules:
            try:
                if rule_func(board):
                    total_work_score += score
                    max_tier_used = max(max_tier_used, tier)
                    made_progress = True
                    if debug:
                        print(f"  [Rules] Applied {name} (tier={tier}, score={score}, iteration={iteration})")
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

    return total_work_score, max_tier_used


def cell_to_var(x, y, width):
    """Convert cell coordinates to SAT variable (1-indexed)."""
    return y * width + x + 1


def var_to_cell(var, width):
    """Convert SAT variable back to cell coordinates."""
    var = var - 1  # Convert to 0-indexed
    y = var // width
    x = var % width
    return x, y


def check_for_loops(board, assignment, width, height):
    """
    Check if the given assignment (combined with pre-filled cells) would create loops.
    Uses union-find to detect cycles.

    Args:
        board: The Board object with some cells already filled
        assignment: Dict mapping (x, y) -> SLASH or BACKSLASH for SAT-assigned cells
        width, height: Board dimensions

    Returns:
        List of cell coordinates that form loops, or empty list if no loops.
        Only returns SAT-assigned cells (from assignment), not pre-filled ones.
    """
    # Initialize union-find for all vertices
    num_vertices = (width + 1) * (height + 1)
    parent = list(range(num_vertices))
    rank = [0] * num_vertices

    def find(x):
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]

    def union(x, y):
        """Returns False if x and y were already connected (would form loop)."""
        rx, ry = find(x), find(y)
        if rx == ry:
            return False  # Already connected
        if rank[rx] < rank[ry]:
            rx, ry = ry, rx
        parent[ry] = rx
        if rank[rx] == rank[ry]:
            rank[rx] += 1
        return True

    def vertex_index(vx, vy):
        return vy * (width + 1) + vx

    loop_cells = []

    # First, process all pre-filled cells from the board (these don't cause loop reports)
    for y in range(height):
        for x in range(width):
            cell = board.get_cell(x, y)
            if cell.value == UNKNOWN:
                continue  # Will be handled from assignment

            value = cell.value

            if value == SLASH:
                v1 = vertex_index(x, y + 1)
                v2 = vertex_index(x + 1, y)
            else:  # BACKSLASH
                v1 = vertex_index(x, y)
                v2 = vertex_index(x + 1, y + 1)

            # Pre-filled cells should never form loops (they were validated during placement)
            union(v1, v2)

    # Now process SAT-assigned cells - these can form loops
    for y in range(height):
        for x in range(width):
            cell = board.get_cell(x, y)
            if cell.value != UNKNOWN:
                continue  # Already processed above

            if (x, y) not in assignment:
                continue

            value = assignment[(x, y)]

            if value == SLASH:
                v1 = vertex_index(x, y + 1)
                v2 = vertex_index(x + 1, y)
            else:  # BACKSLASH
                v1 = vertex_index(x, y)
                v2 = vertex_index(x + 1, y + 1)

            if not union(v1, v2):
                loop_cells.append((x, y))

    return loop_cells


def solve_with_sat(board, width, height, verbose=False):
    """
    Solve remaining cells using SAT.

    Args:
        board: Board with some cells already filled by production rules
        width, height: Board dimensions
        verbose: Print debug info

    Returns:
        dict with keys:
        - status: "solved", "unsolved", or "mult"
        - solution: assignment dict mapping (x, y) -> SLASH/BACKSLASH
        - iterations: number of SAT iterations (loop blocking)
        - work_score: SAT-specific work score
    """
    # Track the next available variable (for cardinality encoding)
    next_var = width * height + 1

    # Create SAT solver
    solver = SATSolver(name='g3')  # Glucose3 is fast

    # Collect all clauses for cardinality constraints
    all_clauses = []

    # 1. Add unit clauses for already-decided cells
    for y in range(height):
        for x in range(width):
            cell = board.get_cell(x, y)
            if cell.value != UNKNOWN:
                var = cell_to_var(x, y, width)
                if cell.value == SLASH:
                    all_clauses.append([var])  # var = True means SLASH
                else:  # BACKSLASH
                    all_clauses.append([-var])  # var = False means BACKSLASH

    # 2. Encode vertex clue constraints using cardinality constraints
    for vertex in board.get_clued_vertices():
        clue = vertex.clue
        vx, vy = vertex.vx, vertex.vy

        # Get adjacent cells and their touch relationships
        adjacent = board.get_adjacent_cells_for_vertex(vertex)

        # Build list of literals that represent "touches this vertex"
        touch_literals = []

        for cell, slash_touches, backslash_touches in adjacent:
            var = cell_to_var(cell.x, cell.y, width)

            if slash_touches:
                # SLASH (var=True) touches this vertex
                touch_literals.append(var)
            else:
                # BACKSLASH (var=False) touches this vertex
                # So NOT var means touches
                touch_literals.append(-var)

        if not touch_literals:
            continue

        # Create "exactly N" constraint using PySAT's cardinality encoding
        # CardEnc.equals returns clauses that encode "exactly bound of lits are true"
        if len(touch_literals) > 0:
            cnf = CardEnc.equals(
                lits=touch_literals,
                bound=clue,
                top_id=next_var - 1,
                encoding=EncType.seqcounter
            )
            # Update next_var to account for auxiliary variables
            if cnf.nv >= next_var:
                next_var = cnf.nv + 1
            all_clauses.extend(cnf.clauses)

    # Add all clauses to solver
    for clause in all_clauses:
        solver.add_clause(clause)

    # 3. Iterative solve with loop detection
    iterations = 0
    max_iterations = 5000  # Increased to handle harder puzzles
    loop_blocking_clauses = 0

    while iterations < max_iterations:
        iterations += 1

        if not solver.solve():
            # UNSAT - no solution
            if verbose:
                print(f"  [SAT] UNSAT after {iterations} iterations and {loop_blocking_clauses} loop-blocking clauses")
            solver.delete()
            return {
                'status': 'unsolved',
                'solution': {},
                'iterations': iterations,
                'work_score': 50 + iterations * 5 + loop_blocking_clauses * 10
            }

        # Get the model (assignment)
        model = solver.get_model()
        model_set = set(model)  # Convert to set for O(1) lookup

        # Convert model to assignment dict
        assignment = {}
        for y in range(height):
            for x in range(width):
                var = cell_to_var(x, y, width)
                if var in model_set:
                    assignment[(x, y)] = SLASH
                elif -var in model_set:
                    assignment[(x, y)] = BACKSLASH
                else:
                    # Variable not in model - use default (shouldn't happen)
                    assignment[(x, y)] = SLASH

        # Check for loops
        loop_cells = check_for_loops(board, assignment, width, height)

        if not loop_cells:
            # Valid solution found! Now check for multiple solutions.
            first_solution = assignment.copy()

            # Add blocking clause for this solution
            blocking_clause = []
            for y in range(height):
                for x in range(width):
                    var = cell_to_var(x, y, width)
                    if assignment[(x, y)] == SLASH:
                        blocking_clause.append(-var)
                    else:
                        blocking_clause.append(var)

            solver.add_clause(blocking_clause)

            # Try to find second solution
            second_iterations = 0
            has_second = False

            while second_iterations < 2000:  # Increased for harder puzzles
                second_iterations += 1

                if not solver.solve():
                    break

                model2 = solver.get_model()
                model2_set = set(model2)
                assignment2 = {}
                for y in range(height):
                    for x in range(width):
                        var = cell_to_var(x, y, width)
                        if var in model2_set:
                            assignment2[(x, y)] = SLASH
                        elif -var in model2_set:
                            assignment2[(x, y)] = BACKSLASH
                        else:
                            assignment2[(x, y)] = SLASH

                # Check this solution for loops
                loop_cells2 = check_for_loops(board, assignment2, width, height)

                if not loop_cells2:
                    # Second valid solution found
                    has_second = True
                    break
                else:
                    # Block entire solution (same strategy as first solution search)
                    blocking = []
                    for y in range(height):
                        for x in range(width):
                            cell = board.get_cell(x, y)
                            if cell.value != UNKNOWN:
                                continue
                            var = cell_to_var(x, y, width)
                            if assignment2[(x, y)] == SLASH:
                                blocking.append(-var)
                            else:
                                blocking.append(var)
                    solver.add_clause(blocking)

            solver.delete()

            if has_second:
                return {
                    'status': 'mult',
                    'solution': first_solution,
                    'iterations': iterations + second_iterations,
                    'work_score': 50 + (iterations + second_iterations) * 5 + loop_blocking_clauses * 10
                }
            else:
                return {
                    'status': 'solved',
                    'solution': first_solution,
                    'iterations': iterations + second_iterations,
                    'work_score': 50 + (iterations + second_iterations) * 5 + loop_blocking_clauses * 10
                }

        # Loop found - add blocking clause
        # Strategy: Block all unknown cells involved in the current invalid solution
        # This is more aggressive than blocking just loop cells, but ensures faster convergence
        blocking_clause = []
        for y in range(height):
            for x in range(width):
                cell = board.get_cell(x, y)
                if cell.value != UNKNOWN:
                    continue
                var = cell_to_var(x, y, width)
                if assignment[(x, y)] == SLASH:
                    blocking_clause.append(-var)
                else:
                    blocking_clause.append(var)

        solver.add_clause(blocking_clause)
        loop_blocking_clauses += 1

        if verbose:
            loop_strs = [f"({x},{y})={'/' if assignment[(x,y)]==SLASH else chr(92)}" for x, y in loop_cells]
            print(f"  [SAT] Iteration {iterations}: found loop with {len(loop_cells)} cells: {loop_strs}, blocking entire solution")

    solver.delete()
    return {
        'status': 'unsolved',
        'solution': {},
        'iterations': iterations,
        'work_score': 50 + iterations * 5 + loop_blocking_clauses * 10
    }


def solve(givens_string, width=None, height=None, verbose=False, known_solution=None,
          for_generation=False, max_tier=10):
    """
    Solve a Slants puzzle using production rules + SAT.

    Args:
        givens_string: RLE-encoded vertex clues
        width: Width of the puzzle (number of cell columns)
        height: Height of the puzzle (number of cell rows)
        verbose: If True, print progress information
        known_solution: If provided, solver will detect incorrect moves during initial rule application
        for_generation: Ignored by SAT solver (included for API compatibility)
        max_tier: Maximum rule tier to use (1, 2, or 3). Default 10 uses all rules.
                  If max_tier < 3, SAT solver won't be invoked.

    Returns:
        Tuple of (status, solution_string, work_score, max_tier_used) where:
        - status is "solved", "unsolved", or "mult"
        - solution_string is the board state
        - work_score is cumulative score
        - max_tier_used is the highest tier used (3 if SAT was invoked)
    """
    if width is None or height is None:
        raise ValueError("Width and height must be specified for Slants puzzles")

    # Create board
    board = Board(width, height, givens_string, known_solution=known_solution)

    # Filter rules by tier (only tier 1-2 for production rules)
    rule_max_tier = min(max_tier, 2)
    filtered_rules = [(name, score, tier, func) for name, score, tier, func in RULES if tier <= rule_max_tier]

    debug = verbose

    if debug:
        print(f"\n{'='*60}")
        print(f"Starting SAT-based solve")
        print(f"Givens: {givens_string}")
        print(f"Size: {width}x{height}")
        print(f"{'='*60}\n")

    start_time = time.time()

    # Phase 1: Apply production rules (tier 1-2)
    try:
        work_score, max_tier_used = apply_rules_until_stuck(board, debug=debug, rules=filtered_rules)
    except SolverDebugError as e:
        if debug:
            print(f"\n*** DEBUG ERROR during solve ***")
            print(str(e))
        return "unsolved", board.to_solution_string(), 0, 0

    if debug:
        unknown_count = len(board.get_unknown_cells())
        print(f"\n  [Phase 1] Production rules complete")
        print(f"  Work score: {work_score}, Max tier: {max_tier_used}")
        print(f"  Unknown cells remaining: {unknown_count}")

    # Check if already solved
    if board.is_solved():
        if board.is_valid_solution():
            elapsed_time = time.time() - start_time
            if debug:
                print(f"\n  [SOLVED] by production rules alone!")
                print(f"  Elapsed time: {elapsed_time:.3f}s")
            return "solved", board.to_solution_string(), work_score, max_tier_used
        else:
            return "unsolved", board.to_solution_string(), work_score, max_tier_used

    # Check if we're allowed to use SAT (tier 3)
    if max_tier < 3:
        if debug:
            print(f"\n  [STOPPED] max_tier={max_tier} prevents SAT solver invocation")
        return "unsolved", board.to_solution_string(), work_score, max_tier_used

    # Disable debug checking for SAT phase (it explores many branches)
    if known_solution:
        board.disable_debug_checking()

    # Phase 2: SAT solving for remaining cells
    if debug:
        print(f"\n  [Phase 2] Invoking SAT solver...")

    sat_result = solve_with_sat(board, width, height, verbose=debug)

    # Merge SAT results
    work_score += sat_result['work_score']
    max_tier_used = 3  # SAT solver invoked = tier 3

    if sat_result['status'] == 'solved' or sat_result['status'] == 'mult':
        # Apply SAT solution to board
        for (x, y), value in sat_result['solution'].items():
            cell = board.get_cell(x, y)
            if cell.value == UNKNOWN:
                cell.value = value

    elapsed_time = time.time() - start_time

    if debug:
        print(f"\n{'='*60}")
        print(f"SAT solve complete:")
        print(f"  Status: {sat_result['status']}")
        print(f"  SAT iterations: {sat_result['iterations']}")
        print(f"  Total work score: {work_score}")
        print(f"  Elapsed time: {elapsed_time:.3f}s")
        print(f"{'='*60}\n")

    solution_string = board.to_solution_string()

    if verbose:
        print(f"Final board ({sat_result['status']}):")
        print(board)
        print()
        print(f"Solution string: {solution_string}")

    return sat_result['status'], solution_string, work_score, max_tier_used


if __name__ == "__main__":
    # Test with the 8x8 puzzle from Simon Tatham's site
    width, height = 8, 8
    givens = "c120a0b21h3a2114f3a2b2a4b2110a1a1b1c2132d1b1a33a1a1c0b"

    print("Testing solver_SAT.py")
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
    elif status == "mult":
        print("\nMultiple solutions found.")
    else:
        print("\nPuzzle not solved.")
