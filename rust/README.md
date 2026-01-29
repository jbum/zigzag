# Slants Puzzle Solver & Generator (Rust)

A Rust port of the Python Slants (Gokigen Naname) puzzle solver and generator.

For complete documentation of the puzzle format, solving rules, and Python scripts, see the main [README.md](../README.md) in the project root.

## Building

```bash
cd rust
cargo build --release
```

Binaries will be at `target/release/solve_puzzles` and `target/release/gen_puzzles`.

## solve_puzzles

Reads puzzles from a testsuite file and solves them.

```bash
# Basic usage (uses PR solver by default)
./target/release/solve_puzzles ../testsuites/test_sample.txt

# Use BF (brute force) solver
./target/release/solve_puzzles -s BF ../testsuites/test_sample.txt

# Limit to first N puzzles
./target/release/solve_puzzles -n 10 ../testsuites/SGT_testsuite.txt

# Start from puzzle number 5
./target/release/solve_puzzles -ofst 5 ../testsuites/SGT_testsuite.txt

# Filter puzzles by name
./target/release/solve_puzzles -f "8x8" ../testsuites/SGT_testsuite.txt

# Verbose output (testsuite-compatible format)
./target/release/solve_puzzles -v ../testsuites/test_sample.txt

# Limit maximum rule tier (1, 2, or 3)
./target/release/solve_puzzles -mt 2 ../testsuites/test_sample.txt
```

### solve_puzzles Options

| Option | Description |
|--------|-------------|
| `-s, --solver <PR\|BF>` | Solver to use: PR (production rules) or BF (brute force). Default: PR |
| `-n <N>` | Maximum number of puzzles to test |
| `-ofst <N>` | Puzzle number to start at (1-based). Default: 1 |
| `-f, --filter <STR>` | Filter puzzles by partial name match |
| `-v, --verbose` | Output testsuite-compatible lines with work scores |
| `-mt, --max_tier <N>` | Maximum rule tier to use (1, 2, or 3). Default: 10 (all) |
| `-h, --help` | Show help message |

## gen_puzzles

Generates puzzles by creating random valid solutions, computing vertex clues, and reducing clues while maintaining unique solvability.

```bash
# Generate 10 puzzles (6x5, default size)
./target/release/gen_puzzles -n 10

# Generate 8x8 puzzles with a specific seed
./target/release/gen_puzzles -n 20 -w 8 -ht 8 -r 42

# Use BF solver for generation (allows tier 3 puzzles)
./target/release/gen_puzzles -n 10 -w 12 -ht 12 -s BF

# Output to a file (sorts by work score)
./target/release/gen_puzzles -n 60 -w 10 -ht 10 -r 0 -o puzzles.txt

# Generate only tier 2 (hard) puzzles
./target/release/gen_puzzles -n 10 -w 8 -ht 8 -mingt 2 -maxgt 2

# Enable symmetric clue reduction
./target/release/gen_puzzles -n 10 -w 10 -ht 10 -sym

# Verbose progress
./target/release/gen_puzzles -n 5 -w 8 -ht 8 -v
```

### gen_puzzles Options

| Option | Description |
|--------|-------------|
| `-n, --number <N>` | Number of puzzles to generate. Default: 1 |
| `-r, --random-seed <N>` | Random seed. Default: 0 |
| `-s, --solver <PR\|BF>` | Solver to use. Default: PR |
| `-v, --verbose` | Verbose output to stderr |
| `-w, --width <N>` | Puzzle width. Default: 6 |
| `-ht, --height <N>` | Puzzle height. Default: 5 |
| `-rp, --reduction_passes <N>` | Number of clue reduction passes. Default: 3 |
| `-o, --output_file <FILE>` | Output file (default: stdout) |
| `-sym, --symmetry` | Enable symmetric clue reduction |
| `-mingt, --min_gen_tier <N>` | Minimum generated tier (1 or 2). Default: 1 |
| `-maxgt, --max_gen_tier <N>` | Maximum generated tier (1 or 2). Default: 2 |
| `-h, --help` | Show help message |

## Solvers

### PR (Production Rules)
Uses logical deduction rules to solve puzzles. Rules are applied in order until no more progress can be made. Solves tier 1 and tier 2 puzzles.

### BF (Brute Force)
Uses production rules combined with stack-based backtracking. Can solve all solvable puzzles; those requiring guessing are classified as tier 3.

## Testsuite File Format

```
# Comment line
name	width	height	givens	answer	# optional comment
```

## Comparison with Python Version

```bash
# Python solver
pypy3 solve_puzzles.py testsuites/SGT_testsuite.txt -s PR

# Rust solver (equivalent)
./rust/target/release/solve_puzzles ../testsuites/SGT_testsuite.txt -s PR

# Python generator
pypy3 gen_puzzles.py -n 20 -w 10 -ht 10 -r 42 -s PR

# Rust generator (equivalent)
./rust/target/release/gen_puzzles -n 20 -w 10 -ht 10 -r 42 -s PR
```

## Performance

### Solver Performance

Benchmark results on puzzles_12x12.txt (60 puzzles, PR solver -mt 2):
- Rust: 0.013s
- PyPy3: 0.903s (~70x slower)

Benchmark results on puzzles_12x12_BF.txt (60 puzzles, BF solver):
- Rust: 1.34s
- PyPy3: 23.4s (~17x slower)

### Generator Performance

Generating 10 puzzles (12x12, BF solver, seed 99):
- Rust: 7.1s
- Note: PR generator is much faster (~0.6s for 20 10x10 puzzles)

## Updating Rust

If your Rust installation is outdated:

```bash
rustup update
```
