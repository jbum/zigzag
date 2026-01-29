### The Project

We’re gonna create a set of python scripts for generating, solving and publishing Slants or Gokigen Naname puzzles.  There is a Wikipedia article about these puzzles at https://en.wikipedia.org/wiki/Gokigen_Naname which can give you insight.

In this puzzle you fill the cells in a grid with diagonal lines, connecting the opposite corners, which come in two kinds: Slash and Backslash.  The clues to the puzzle are numbers positioned over some of the vertices of the grid. The numbers, from 0-4, reveal how many diagonal lined connect to the vertex.

In test suites, and generated puzzle files, the puzzles will be represented as tab-delimited text files. Empty lines, and lines starting with \s*[#;] are ignored. Otherwise, lines are expected to be puzzles, containing the following fields
1. puzzle-title, such as slants-1, slants-2 etc.
2. width 
3. height 
4. givens. Givens are a (width+1)x(height+1) run-length encoded string representing the vertices. Lower case letters are runs of unlabeled vertices, a=1,…z=26. Runs of more than 26 represented by multiple letters. Numbers (0-4) are givens.
5. answer. Answers, when provided, are strings of slashes and backslashes (or empty string, if answer unknown)
6. comment (or empty string, if no comments.  comments start with #). Comments are used to store info like work-score, #givens, and other info about the puzzle.

The puzzle and answer depicted in sample_puzzle.png are given by

puzzle-1    5   5   g4b12b12a31113b113a12g  \//\\/\\\\\\\/\\/\\\\\\//   # givens=15

Here is the plan for making this software.  Make a PROGRESS.md file to track our progress through these steps.

1. Procure a couple test suites of puzzles.  We will procure our puzzles from these two sites, https://www.puzzle-slant.com/, and https://www.chiark.greenend.org.uk/~sgtatham/puzzles/js/slant.html and save them in ./testsuites/PS_testsuite.txt and testsuites/SGT_testsuite.txt, respectively.  Suggestions for scraping the sites are in SCRAPING.md. We will want 10 of each size/difficulty puzzle offered by each site.  Initially our testsuites won’t have answers, but we will supply them later.  This can be done in parallel with the following steps.  The resultant test suites aren't needed til step 9.

2. Implement a representation class of the board and its cells and vertices for use in solvers. For vertices we need to know its given if it has one. For cells they either have the value UNKNOWN (0), SLASH (1) or BACKSLASH (2).

3. Generate a production rule (non-brute force) solver in solver_PR.txt that implements a solve function. Initial rules are explicated in RULES.md.  We repeatedly loop thru rules from easiest to hardest until we hit one that makes progress or the puzzle is fully solved.  The **main** functionality tests the sample puzzle given above by default, or accepts a new set of givens on the command line.  We will be reusing the rule set, so keep the rules in a reuseable slants_rules.py file.

5. Add additional rules using observations from the wikipedia article. It contains several simple patterns we can follow.

6. If we are solving the test puzzle find another we are not solving, from the test suites, if possible.

7. Implement a brute force solver in solver_BF.txt which uses our production rules to force moves, but then does trial and error DFS when it needs to, to find all possible solutions to a solvable puzzle.  Get it to solve the same puzzle that the PR solver cannot solve.  Its solve function should take the same arguments as solver_PR.py.

8. Implement a solving harness, solve_puzzles.py, that works with both solvers (loading via importlib), and can be tested on a testsuite of puzzles.  It will be used for testing the solvers as we develop them further, and for regression and performance tests.  It will accept these arguments:
    
positional arguments:
  input_file            Path to testsuite file

options:
  -h, --help            show this help message and exit
  -v, --verbose         Output testsuite-compatible lines with work scores
  -d, --debug           Show ansi colored side-by-side grid display for each puzzle
  -f FILTER, --filter FILTER
                        Filter puzzles by partial name match
  -n N                  Maximum number of puzzles to test
  -ofst OFST            Puzzle number to start at (1-based, default: 1)
  -s {PR,BF}, --solver {PR,BF}
                        Solver to use: PR (production rules) or BF (brute force)
  -ou, --output_unsolved
                        Output list of unsolved puzzles (sorted by size)    

  This script loops thru the testsuite and attempts to solve all the puzzles, and reports on the results.

9. Wait for test suites to become avaiable if they are being generated in another thread. Then let’s debug the brute force solver using our test suites and solve_puzzles.py. It needs to be able to solve most of them.  Some of the test suites may contain large puzzles (15x15 or larger) which take too long to solve. We can ignore those.

10. Use the brute force solver and solving harness to obtain answers for the test suites (for puzzles which are tractible).  Add the answers to the test suites.

11. Modify the PR solver (and solve_puzzles.py) to detect, when the answer is known, when we make an inaccurate move as we solve the puzzle.  If we do, the solver is bugged, and we should debug rules which make false moves.  We should output warning messages when this happens.

12. Get a baseline for how the PR solver is doing on the test suites. Debug any current issues detected using the solving harness.  From here on out, keep a history of our progress on the test suites with this solver, summarizing what changes were made, and the elapsed times and solve% on each test suite.

13. If the PR solver isn’t solving the majority of the test puzzles, continue working on improving the ruleset until it is solving the majority of the test puzzles without using trial and error or no more than 1-level of lookahead.

14. Assign work scores to the rules which are proportional to their complexity. Make each solver return a cumulative work score for the puzzle.  For the BF puzzle, stack pushes/pops should also contribute a good bit to the score.

15. Make a new script, gen_puzzles.py, that accepts these arguments.
    
  -h, --help            show this help message and exit
  -n NUMBER, --number NUMBER
                        Number of puzzles to generate (default: 1)
  -r RANDOM_SEED, --random-seed RANDOM_SEED
                        Random seed (default: 0)
  -s {PR,BF}, --solver {PR,BF}
                        Solver to use (PR, BF) (default: PR)
  -v, --verbose         Verbose output
  -vv, --very_verbose   Very verbose output
  -w WIDTH, --width WIDTH
                        Width of generated puzzles (default: 6)
  -ht HEIGHT, --height HEIGHT
                        Height of generated puzzles (default: 5)
  -rp REDUCTION_PASSES, --reduction_passes REDUCTION_PASSES
                        Number of reduction passes during puzzle refinement (default: 3)
  -o OUTPUT_FILE, --output_file OUTPUT_FILE
                        Output file to write puzzles to (default: stdout)
  -sym, --symmetry      Enable symmetry for clue reduction

    It generates a puzzle by filling a grid with slashes that don’t form loops, using a simple backtracker.  It then assigns givens to all the vertices. 
    
    The puzzle is then tested, it should be trivial to solve, but if unsolvable is thrown away (retries should be counted and reported. I am hoping they will be rare, but if not, we may need to use heuristics in our candidate generator to help reduce them).
    
    We then do a a series of clue-reduction passes, keeping the puzzle with the fewest givens after clue-reduction.
    
    The clue reduction pass scrambles the vertices and removes clues on at a time, testing that the resulting puzzle is solvable by the selected solver.  If removing the clue/given makes the puzzle unsolvable or ambiguous, we keep the clue.
    
    We output finished puzzles to the output file, or stdout.  Puzzles saved to files should be sorted by cumulative work score (which is reported in puzzle comment). When outputing to stdout, print puzzles as they are generated so we can better monitor progress.  Also output comments with info such as command line used, elapsed time, average #givens.
    
16. Use gen_puzzles to make a new, larger, test suites using the BF solver.  Generate a lot of small puzzles, like 1000 of them.  These should be non-square grids (e.g. 5x4) to help us avoid bugs in which h/v are confused.  When generating puzzles, use -r 1 to ensure repeatability.

17. Use those small puzzles test suites to identify small puzzles that the PR solver cannot solve. Try to formulate new rules that will make headway on those unsolved puzzles.

18. Keep a record of improved progress on our test suites by the PR solver.  If we are solving > 96% of the puzzles, make a BF test suite of larger grid puzzles and work with that.

19. Use cProfile to optimize the solvers for speed.

20. Generate several sets of 60 puzzles, using the PR solver at -r 1 at an assortment of sizes (sm, med, lg) in ./puzzledata/

21. Make a script print_puzzles_pdf.pl which produced PDFs of puzzles with answer pages.  Mimic the print_puzzles_pdf.py scripts in reference dir: ./sample_finished_puzzle/ (a symbolic link to a parallel directory).  That script uses some support files you should copy over (assets/ etc)

22. Print a PDF for each of the puzzledata collections, 4 puzzles per page w answers.  Store them in ./pdfs/.  The printed digits at the vertices should be a little oversized (font-height at least half the cell height). They should have circles behind them with white fills and black outlines.  Use sample_puzzle.png for a visual reference.  Also, the circles extend past the grid's area and contribute to the puzzle's size. Don't let the circles extend out of the puzzle's quadrant, or overlap the puzzle#.

