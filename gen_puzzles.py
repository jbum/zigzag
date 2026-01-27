#!/usr/bin/env python3
"""
Puzzle generator for Slants (Gokigen Naname) puzzles.

Generates puzzles by:
1. Creating a random valid solution (no loops)
2. Computing all vertex clues
3. Reducing clues while maintaining unique solvability
"""

import argparse
import importlib
import random
import sys
import time

from slants_board import Board, UNKNOWN, SLASH, BACKSLASH


def generate_random_solution(width, height, rng):
    """
    Generate a random valid solution (no loops) using backtracking.

    Returns a list of cell values (SLASH or BACKSLASH) in row-major order,
    or None if generation fails (shouldn't happen).
    """
    total_cells = width * height
    solution = [UNKNOWN] * total_cells

    # Union-find for loop detection
    num_vertices = (width + 1) * (height + 1)
    parent = list(range(num_vertices))
    rank = [0] * num_vertices

    def find(x):
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]

    def union(x, y):
        rx, ry = find(x), find(y)
        if rx == ry:
            return False  # Would form loop
        if rank[rx] < rank[ry]:
            rx, ry = ry, rx
        parent[ry] = rx
        if rank[rx] == rank[ry]:
            rank[rx] += 1
        return True

    def vertex_index(vx, vy):
        return vy * (width + 1) + vx

    def would_form_loop(cell_idx, value):
        x = cell_idx % width
        y = cell_idx // width
        if value == SLASH:
            v1 = vertex_index(x, y + 1)
            v2 = vertex_index(x + 1, y)
        else:
            v1 = vertex_index(x, y)
            v2 = vertex_index(x + 1, y + 1)
        return find(v1) == find(v2)

    def place(cell_idx, value):
        x = cell_idx % width
        y = cell_idx // width
        if value == SLASH:
            v1 = vertex_index(x, y + 1)
            v2 = vertex_index(x + 1, y)
        else:
            v1 = vertex_index(x, y)
            v2 = vertex_index(x + 1, y + 1)
        return union(v1, v2)

    # Backtracking to fill all cells
    stack = [(0, parent.copy(), rank.copy())]

    while stack:
        cell_idx, saved_parent, saved_rank = stack.pop()

        if cell_idx == total_cells:
            return solution  # Success!

        # Restore state
        parent[:] = saved_parent
        rank[:] = saved_rank

        # Try both diagonals in random order
        options = [SLASH, BACKSLASH]
        rng.shuffle(options)

        for value in options:
            if not would_form_loop(cell_idx, value):
                solution[cell_idx] = value
                place(cell_idx, value)
                stack.append((cell_idx + 1, parent.copy(), rank.copy()))
                break
        else:
            # Both would form loop - backtrack
            solution[cell_idx] = UNKNOWN
            continue

    return None  # Should not reach here for valid grids


def compute_vertex_clues(width, height, solution):
    """
    Compute all vertex clues from a solution.

    Returns list of clues (0-4) for each vertex in row-major order.
    """
    clues = []

    for vy in range(height + 1):
        for vx in range(width + 1):
            touch_count = 0

            # Check 4 adjacent cells
            # Top-left cell (vx-1, vy-1) - backslash touches bottom-right
            if vx > 0 and vy > 0:
                idx = (vy - 1) * width + (vx - 1)
                if solution[idx] == BACKSLASH:
                    touch_count += 1

            # Top-right cell (vx, vy-1) - slash touches bottom-left
            if vx < width and vy > 0:
                idx = (vy - 1) * width + vx
                if solution[idx] == SLASH:
                    touch_count += 1

            # Bottom-left cell (vx-1, vy) - slash touches top-right
            if vx > 0 and vy < height:
                idx = vy * width + (vx - 1)
                if solution[idx] == SLASH:
                    touch_count += 1

            # Bottom-right cell (vx, vy) - backslash touches top-left
            if vx < width and vy < height:
                idx = vy * width + vx
                if solution[idx] == BACKSLASH:
                    touch_count += 1

            clues.append(touch_count)

    return clues


def encode_clues(clues):
    """Encode clues list to RLE string."""
    result = []
    unlabeled_count = 0

    for clue in clues:
        if clue is None:
            unlabeled_count += 1
        else:
            while unlabeled_count > 0:
                run = min(unlabeled_count, 26)
                result.append(chr(ord('a') + run - 1))
                unlabeled_count -= run
            result.append(str(clue))

    while unlabeled_count > 0:
        run = min(unlabeled_count, 26)
        result.append(chr(ord('a') + run - 1))
        unlabeled_count -= run

    return ''.join(result)


def solution_to_string(solution):
    """Convert solution list to string."""
    chars = []
    for val in solution:
        if val == SLASH:
            chars.append('/')
        elif val == BACKSLASH:
            chars.append('\\')
        else:
            chars.append('.')
    return ''.join(chars)


def reduce_clues(width, height, clues, solution, solve_func, rng, symmetry=False, verbose=False):
    """
    Reduce clues while maintaining unique solvability.

    Args:
        width, height: Puzzle dimensions
        clues: List of clue values (modified in place to None for removed clues)
        solution: The target solution string
        solve_func: Solver function to test solvability
        rng: Random number generator
        symmetry: If True, remove clues in symmetric pairs
        verbose: Print progress

    Returns:
        Number of remaining clues
    """
    num_vertices = len(clues)
    indices = list(range(num_vertices))
    rng.shuffle(indices)

    for idx in indices:
        if clues[idx] is None:
            continue

        # Get symmetric index if using symmetry
        if symmetry:
            vx = idx % (width + 1)
            vy = idx // (width + 1)
            sym_vx = width - vx
            sym_vy = height - vy
            sym_idx = sym_vy * (width + 1) + sym_vx
        else:
            sym_idx = None

        # Save current values
        old_val = clues[idx]
        old_sym_val = clues[sym_idx] if sym_idx is not None and sym_idx != idx else None

        # Try removing
        clues[idx] = None
        if sym_idx is not None and sym_idx != idx:
            clues[sym_idx] = None

        # Test if still solvable
        givens = encode_clues(clues)
        try:
            status, result, _, _ = solve_func(givens, width, height,
                                              known_solution=solution,
                                              for_generation=True)
            if status == "solved" and result == solution:
                # Can remove this clue
                if verbose:
                    print(f"  Removed clue at vertex {idx}")
                continue
        except:
            pass

        # Restore clue
        clues[idx] = old_val
        if sym_idx is not None and sym_idx != idx and old_sym_val is not None:
            clues[sym_idx] = old_sym_val

    return sum(1 for c in clues if c is not None)


def generate_puzzle(width, height, solve_func, rng, reduction_passes=3,
                    symmetry=False, verbose=False, very_verbose=False):
    """
    Generate a single puzzle.

    Returns:
        Tuple of (givens_string, solution_string, work_score, num_clues, max_tier) or None if failed
    """
    # Generate random solution
    solution_list = generate_random_solution(width, height, rng)
    if solution_list is None:
        return None

    solution_string = solution_to_string(solution_list)

    # Compute all clues
    all_clues = compute_vertex_clues(width, height, solution_list)

    # Verify puzzle is solvable with all clues
    givens = encode_clues(all_clues)
    try:
        status, result, work_score, max_tier = solve_func(givens, width, height,
                                                           known_solution=solution_string,
                                                           for_generation=True)
        if status != "solved":
            if verbose:
                print(f"  Warning: generated puzzle not solvable with all clues")
            return None
    except Exception as e:
        if verbose:
            print(f"  Error testing initial puzzle: {e}")
        return None

    # Reduce clues
    best_clues = all_clues.copy()
    best_count = sum(1 for c in best_clues if c is not None)

    for pass_num in range(reduction_passes):
        clues = [c for c in all_clues]  # Fresh copy from all clues
        count = reduce_clues(width, height, clues, solution_string, solve_func, rng,
                            symmetry=symmetry, verbose=very_verbose)
        if count < best_count:
            best_clues = clues
            best_count = count
            if verbose:
                print(f"  Pass {pass_num + 1}: reduced to {count} clues")

    # Final verification
    givens = encode_clues(best_clues)
    status, result, work_score, max_tier = solve_func(givens, width, height,
                                                       known_solution=solution_string,
                                                       for_generation=True)
    if status != "solved" or result != solution_string:
        if verbose:
            print(f"  Warning: reduced puzzle verification failed")
        return None

    return givens, solution_string, work_score, best_count, max_tier


def main():
    parser = argparse.ArgumentParser(description='Generate Slants puzzles')
    parser.add_argument('-n', '--number', type=int, default=1,
                        help='Number of puzzles to generate (default: 1)')
    parser.add_argument('-r', '--random-seed', type=int, default=0,
                        help='Random seed (default: 0)')
    parser.add_argument('-s', '--solver', type=str, default='PR', choices=['PR', 'BF'],
                        help='Solver to use (default: PR)')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Verbose output')
    parser.add_argument('-vv', '--very_verbose', action='store_true',
                        help='Very verbose output')
    parser.add_argument('-w', '--width', type=int, default=6,
                        help='Width of generated puzzles (default: 6)')
    parser.add_argument('-ht', '--height', type=int, default=5,
                        help='Height of generated puzzles (default: 5)')
    parser.add_argument('-rp', '--reduction_passes', type=int, default=3,
                        help='Number of reduction passes (default: 3)')
    parser.add_argument('-o', '--output_file', type=str, default=None,
                        help='Output file (default: stdout)')
    parser.add_argument('-sym', '--symmetry', action='store_true',
                        help='Enable symmetry for clue reduction')

    args = parser.parse_args()

    if args.very_verbose:
        args.verbose = True

    # Load solver
    solver_module = importlib.import_module(f'solver_{args.solver}')
    solve_func = solver_module.solve

    # Initialize RNG
    rng = random.Random(args.random_seed)

    start_time = time.time()
    puzzles = []
    retries = 0
    total_clues = 0

    print(f"# Generating {args.number} puzzles ({args.width}x{args.height})", file=sys.stderr)
    print(f"# Solver: {args.solver}, Seed: {args.random_seed}, Reduction passes: {args.reduction_passes}", file=sys.stderr)

    for i in range(args.number):
        if args.verbose:
            print(f"\nGenerating puzzle {i + 1}/{args.number}...", file=sys.stderr)

        attempt = 0
        while True:
            attempt += 1
            result = generate_puzzle(
                args.width, args.height, solve_func, rng,
                reduction_passes=args.reduction_passes,
                symmetry=args.symmetry,
                verbose=args.verbose,
                very_verbose=args.very_verbose
            )

            if result is not None:
                givens, solution, work_score, num_clues, max_tier = result
                puzzles.append((givens, solution, work_score, num_clues, max_tier))
                total_clues += num_clues

                if args.output_file is None:
                    # Print to stdout immediately
                    name = f"gen_{args.width}x{args.height}_{i + 1}"
                    comment = f"# givens={num_clues} work_score={work_score} tier={max_tier}"
                    print(f"{name}\t{args.width}\t{args.height}\t{givens}\t{solution}\t{comment}")

                if args.verbose:
                    print(f"  Generated: {num_clues} clues, work_score={work_score}, tier={max_tier}", file=sys.stderr)
                break

            retries += 1
            if attempt > 100:
                print(f"Warning: Failed to generate puzzle {i + 1} after 100 attempts", file=sys.stderr)
                break

    elapsed = time.time() - start_time

    # Output to file if specified
    if args.output_file:
        # Sort by work score
        puzzles.sort(key=lambda p: p[2])

        with open(args.output_file, 'w') as f:
            f.write(f"# Generated Slants Puzzles\n")
            f.write(f"# Command: {' '.join(sys.argv)}\n")
            f.write(f"# Size: {args.width}x{args.height}, Count: {len(puzzles)}\n")
            f.write(f"# Solver: {args.solver}, Seed: {args.random_seed}\n")
            f.write(f"# Elapsed: {elapsed:.2f}s, Retries: {retries}\n")
            if puzzles:
                avg_clues = total_clues / len(puzzles)
                f.write(f"# Average clues: {avg_clues:.1f}\n")
            f.write("\n")

            for i, (givens, solution, work_score, num_clues, max_tier) in enumerate(puzzles):
                name = f"gen_{args.width}x{args.height}_{i + 1}"
                comment = f"# givens={num_clues} work_score={work_score} tier={max_tier}"
                f.write(f"{name}\t{args.width}\t{args.height}\t{givens}\t{solution}\t{comment}\n")

        print(f"\nWrote {len(puzzles)} puzzles to {args.output_file}", file=sys.stderr)

    # Summary
    print(f"\n# Summary:", file=sys.stderr)
    print(f"# Generated: {len(puzzles)}/{args.number} puzzles", file=sys.stderr)
    print(f"# Retries: {retries}", file=sys.stderr)
    print(f"# Elapsed: {elapsed:.2f}s", file=sys.stderr)
    if puzzles:
        avg_clues = total_clues / len(puzzles)
        print(f"# Average clues: {avg_clues:.1f}", file=sys.stderr)


if __name__ == '__main__':
    main()
