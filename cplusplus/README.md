# Slants Puzzle Solver (C++)

A C++ port of the Python Slants (Gokigen Naname) puzzle solver for performance testing.

## Building

```bash
cd cplusplus
make
```

## Usage

```bash
./solve_puzzles [options] <input_file>
```

### Options

| Flag | Description |
|------|-------------|
| `-v` | Output testsuite-compatible lines with work scores |
| `-d` | Show debug output for each puzzle |
| `-f <filter>` | Filter puzzles by partial name match |
| `-n <count>` | Maximum number of puzzles to test (0 = all) |
| `-ofst <num>` | Puzzle number to start at (1-based, default: 1) |
| `-s <solver>` | Solver to use: `PR` (production rules) or `BF` (brute force, default) |
| `-mt <tier>` | Maximum rule tier to use (1, 2, or 3). Default 10 uses all rules |
| `-ou` | Output list of unsolved puzzles (sorted by size) |

### Examples

```bash
# Solve all puzzles in a testsuite file
./solve_puzzles ../puzzledata/puzzles_8x8.txt

# Solve first 10 puzzles with verbose output
./solve_puzzles -n 10 -v ../puzzledata/puzzles_8x8.txt

# Use production rules solver only
./solve_puzzles -s PR ../puzzledata/puzzles_5x5.txt

# Filter by puzzle name
./solve_puzzles -f "easy" ../puzzledata/puzzles_10x10.txt

# Limit to tier 2 rules (no backtracking lookahead)
./solve_puzzles -mt 2 ../puzzledata/puzzles_8x8.txt
```

## File Structure

- `board.h` / `board.cpp` - Board representation with union-find for loop detection, equivalence classes, v-bitmap tracking
- `rules.h` / `rules.cpp` - Production rules for solving (clue completion, loop avoidance, dead-end avoidance, etc.)
- `solver.h` / `solver.cpp` - BF (brute force with backtracking) and PR (production rules only) solvers
- `main.cpp` - CLI entry point
- `Makefile` - Build system

## Input File Format

Testsuite files use tab-separated values:

```
name	width	height	givens	answer	# comment
```

- `name`: Puzzle identifier
- `width`: Grid width (number of cells)
- `height`: Grid height (number of cells)
- `givens`: RLE-encoded vertex clues (lowercase letters = runs of unlabeled vertices, digits = clues)
- `answer`: Optional solution string (/ and \ characters)
- `comment`: Optional comment starting with #
