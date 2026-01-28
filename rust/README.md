# Slants Puzzle Solver (Rust)

A Rust port of the Python Slants (Gokigen Naname) puzzle solver for performance testing.

## Building

```bash
cd rust
cargo build --release
```

The binary will be at `target/release/slants_solver`.

## Usage

```bash
# Basic usage (uses PR solver by default)
./target/release/slants_solver ../testsuites/test_sample.txt

# Use BF (brute force) solver
./target/release/slants_solver -s BF ../testsuites/test_sample.txt

# Limit to first N puzzles
./target/release/slants_solver -n 10 ../testsuites/SGT_testsuite.txt

# Start from puzzle number 5
./target/release/slants_solver -ofst 5 ../testsuites/SGT_testsuite.txt

# Filter puzzles by name
./target/release/slants_solver -f "8x8" ../testsuites/SGT_testsuite.txt

# Verbose output (testsuite-compatible format)
./target/release/slants_solver -v ../testsuites/test_sample.txt

# Limit maximum rule tier (1, 2, or 3)
./target/release/slants_solver -mt 2 ../testsuites/test_sample.txt
```

## Command Line Options

| Option | Description |
|--------|-------------|
| `-s, --solver <PR\|BF>` | Solver to use: PR (production rules) or BF (brute force). Default: PR |
| `-n <N>` | Maximum number of puzzles to test |
| `-ofst <N>` | Puzzle number to start at (1-based). Default: 1 |
| `-f, --filter <STR>` | Filter puzzles by partial name match |
| `-v, --verbose` | Output testsuite-compatible lines with work scores |
| `-mt, --max_tier <N>` | Maximum rule tier to use (1, 2, or 3). Default: 10 (all) |
| `-h, --help` | Show help message |

## Solvers

### PR (Production Rules)
Uses a set of logical deduction rules to solve puzzles. Rules are applied in order until no more progress can be made. This solver is faster but may not solve all puzzles.

### BF (Brute Force)
Uses production rules combined with stack-based backtracking. Can solve puzzles that require guessing but marks those as tier 3.

## Testsuite File Format

```
# Comment line
name	width	height	givens	answer	# optional comment
```

Example:
```
SGT_8x8_test_1	8	8	c120a0b21h3a2114f3a2b2a4b2110a1a1b1c2132d1b1a33a1a1c0b		# From Simon Tatham's site
```

## Comparison with Python Version

This Rust version mirrors the Python `solve_puzzles.py` script:

```bash
# Python version
pypy3 solve_puzzles.py testsuites/SGT_testsuite.txt -s PR

# Rust version (equivalent)
./rust/target/release/slants_solver testsuites/SGT_testsuite.txt -s PR
```

## Performance Testing

To compare Rust vs PyPy3:

```bash
# Time the Rust solver
time ./rust/target/release/slants_solver testsuites/SGT_testsuite.txt -s BF

# Time the Python solver
time pypy3 solve_puzzles.py testsuites/SGT_testsuite.txt -s BF
```

## Known Limitations

The Rust PR solver has incomplete tier 2 rule implementations. It solves tier 1 puzzles correctly but may fail on puzzles requiring advanced rules. The BF solver will solve all solvable puzzles via backtracking.

Benchmark results on SGT_testsuite.txt (60 puzzles):
- Rust PR: 0.008s, 50% solve rate (tier 1 only)
- Rust BF: 1.57s, 100% solve rate (with backtracking)
- Python PR: 0.53s, 100% solve rate (full tier 2)
- Python BF: 0.59s, 100% solve rate (full tier 2)

## Updating Rust

Your Rust installation (1.64.0 from 2022) is outdated. To update:

```bash
rustup update
```

## Notes

- The Rust version implements the core rules but some tier 2 rules need refinement
- Work scores and tier tracking follow the same system as Python
- The BF solver uses the same cell selection heuristics for branching
