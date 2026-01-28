# Slants (Gokigen Naname) Puzzle Generator and Solver

This project contains a complete set of Python scripts for generating, solving, and publishing Slants (also known as Gokigen Naname) puzzles.

## About the Puzzle

Slants is a logic puzzle where you fill a grid with diagonal lines. Each cell must contain either a forward slash (`/`) or a backslash (`\`). The puzzle includes numbered clues at the vertices (intersections) of the grid, which indicate how many diagonal lines touch that vertex. The numbers range from 0 to 4, representing the count of diagonals that connect to that corner.

**Key Rules:**
- Each cell contains exactly one diagonal line (`/` or `\`)
- The numbers at vertices indicate how many diagonals touch that corner
- The diagonal lines must **not form closed loops**

For more information, see the [Wikipedia article on Gokigen Naname](https://en.wikipedia.org/wiki/Gokigen_Naname).

## Puzzle Tiers

Puzzles are classified into tiers based on the complexity of rules needed to solve them:

- **Tier 1 (Easy)**: Solvable using only basic, human-friendly rules. These are the simplest puzzles that can be solved through straightforward logical deduction without trial-and-error.

- **Tier 2 (Hard)**: Requires intermediate rules that are still human-solvable but involve more complex pattern recognition and logical reasoning. These puzzles are challenging but can be solved without guessing.

- **Tier 3 (Unpublishable)**: Requires trial-and-error or lookahead techniques that are not considered human-solvable. These puzzles are typically not suitable for publication as they require backtracking or guessing, which goes against the spirit of logic puzzles.

When generating puzzles for publication, only tiers 1 and 2 are used (tier 3 is excluded).

## Python Scripts

### Core Solver Scripts

- **`solver_PR.py`** - Production Rule solver. Uses a set of logical rules organized by tier to solve puzzles. Rules are applied from easiest to hardest until the puzzle is solved or no more progress can be made. This solver is designed to mimic human solving strategies.

- **`solver_BF.py`** - Brute Force solver. Uses production rules first, then falls back to depth-first search with backtracking when needed. Can solve puzzles that the PR solver cannot, but uses trial-and-error methods.

- **`slants_board.py`** - Board representation class. Provides data structures for representing the puzzle grid, cells, vertices, and their states.

- **`slants_rules.py`** - Contains all the solving rules organized by tier. Rules range from simple (e.g., "if a clue has enough touches, fill the remaining cells to avoid it") to complex pattern recognition.

### Puzzle Generation

- **`gen_puzzles.py`** - Puzzle generator. Creates new Slants puzzles by:
  1. Generating a random valid solution (no loops)
  2. Computing all vertex clues from the solution
  3. Reducing clues while maintaining unique solvability
  4. Classifying puzzles by tier based on solving difficulty

  Options include:
  - `-n`: Number of puzzles to generate
  - `-w`, `-ht`: Width and height
  - `-s`: Solver to use (PR or BF)
  - `-r`: Random seed for reproducibility
  - `-sym`: Enable symmetry for clue reduction
  - `-mingt`, `-maxgt`: Minimum and maximum generation tier

### Testing and Validation

- **`solve_puzzles.py`** - Testing harness for evaluating solvers against test suites. Reads puzzle files and attempts to solve them, reporting success rates, work scores, and tier distributions.

  Options include:
  - `-s`: Solver to use (PR or BF)
  - `-mt`: Maximum tier to use
  - `-v`: Verbose output with work scores
  - `-d`: Debug mode with colored grid display
  - `-f`: Filter puzzles by name
  - `-n`: Maximum number of puzzles to test
  - `-ou`: Output list of unsolved puzzles

### Puzzle Scraping

- **`scrape_ps.py`** - Scrapes puzzles from [puzzle-slant.com](https://www.puzzle-slant.com/). Uses Selenium to extract puzzle data from the website and save it in the standard puzzle format.

- **`scrape_sgt.py`** - Scrapes puzzles from [Simon Tatham's puzzle collection](https://www.chiark.greenend.org.uk/~sgtatham/puzzles/js/slant.html). Extracts puzzle data from the web interface.

### PDF Generation

- **`print_puzzles_pdf.py`** - Generates PDF files from puzzle data files. Creates formatted puzzle pages with clues and separate answer pages. Supports various layouts (puzzles per page, answers per page) and handles different puzzle sizes appropriately.

- **`print_logo.py`** - Utility for rendering SVG logos in PDF output. Used by the PDF generation script.

- **`make_pdfs.py`** - Convenience script that regenerates all PDFs from puzzle data files in the `puzzledata/` directory. Automatically detects puzzle sizes and applies appropriate layout settings (e.g., 1 puzzle per page for large puzzles, 4 per page for smaller ones).

## Shell Scripts

- **`generate_samples.sh`** - Batch script to generate sample puzzle collections. Generates 60 puzzles each for various sizes (5x5, 8x8, 10x10, 12x12, 15x15, 21x21, 25x25) using both PR and BF solvers. Uses a fixed random seed for reproducibility.

## File Formats

Puzzle files use a tab-delimited text format:

```
puzzle-name    width    height    givens    answer    # comment
```

- **puzzle-name**: Unique identifier for the puzzle
- **width, height**: Grid dimensions (number of cells)
- **givens**: Run-length encoded vertex clues. Lowercase letters (a-z) represent runs of unlabeled vertices (a=1, b=2, ..., z=26). Digits 0-4 represent clues.
- **answer**: Solution string of `/` and `\` characters (or empty if unknown)
- **comment**: Optional metadata (e.g., `# givens=12 work_score=7 tier=1`)

Example:
```
gen_5x5_1    5    5    1a0a0i42a10b3a2g0a0a0    \\/\/\\//\\/\\\///\//\/\/    # givens=12 work_score=7 tier=1
```

## Directory Structure

- **`puzzledata/`** - Contains puzzle data files in text format
- **`pdfs/`** - Generated PDF files ready for printing
- **`testsuites/`** - Test puzzle collections for solver validation
- **`assets/`** - Supporting files (logos, etc.) for PDF generation

## Usage Examples

Generate 60 easy puzzles (5x5):
```bash
pypy3 gen_puzzles.py -n 60 -w 5 -ht 5 -r 1 -s PR -mingt 1 -maxgt 1 -o puzzledata/puzzles_5x5_easy.txt
```

Test solver on a test suite:
```bash
pypy3 solve_puzzles.py testsuites/SGT_testsuite.txt -s PR -mt 2
```

Generate PDF from puzzle file:
```bash
pypy3 print_puzzles_pdf.py puzzledata/puzzles_10x10.txt -o pdfs/puzzles_10x10.pdf
```

Regenerate all PDFs:
```bash
pypy3 make_pdfs.py
```

## Development Notes

- The project uses `pypy3` for better performance (as noted in `CLAUDE.md`)
- A virtual environment is used (activated via `.autoenv` scripts)
- See `PROJECT.md` for the original development plan
- See `RULES.md` for details on the solving rules and their tiers
- See `PROGRESS.md` for development history that was maintained during the initial development process.
