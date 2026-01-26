# prompt history

Read PROJECT.md and begin the steps.

Our last session got interrupted.  Let's continue working on the scraping task from PROJECT.md. It looks like
  we have a candidate version of scrape_sgt.py, but I only see one puzzle in the SGT test suite.

Continue debugging the puzzle-slant scraper.

Make your own plan version of PROGRESS.md so you can track progress.  You are now on step 9.

(At this point, it was 10pm.  I probably should have said step 10, because I had already manually tested, and determined that the BF script was getting bogged down on some harder 15x15  puzzles in the PS test suite. I was curious to see if it would figure this out on it’s own and stop testing on those.  It wasted several minutes and then I interrupted it. )

10:10pm
I'm aware that the brute force solver is too slow on the larger (15x15 and 20x20) puzzles in the PS test suite.  That's okay, we don't need to fix that.  Otherwise, I think the solvers are working, so let's proceed with step 10.

(It correctly figured out that for step 10, in which it fetched answers for test suites, it could skip the larger PS puzzles.  Still annoyingly asking for permissions.).

Yes. Continue with succesive steps as well, when the prior steps are completed successfully.


[ It quickly got to step 11, and improved the PR solver significantly by implementing more rules, including a 1-level look-ahead. Then it quickly got to step 15, and started working on the generator.  Then quickly generated a large test suite and made it to step 20 (10:27pm). It generated 3 sets of 60 puzzles.  Started working on the printing script.  Read my old script.  ]

10:30pm
At this point it compacted the conversation and initiated a new instance.  Good idea!

It continued working on the print script.  At this point, I was worried because I had provided a picture, but not verbally described the appearance of these puzzles.

At 10:34 it reported project complete. It had managed to print the puzzles with pypy3 (I don’t think I ever figured out how to get that to work with reportlab).

The PDFs show valid puzzles. They don’t look quite right, but I was able to fix this with a few additional prompts (I saved them so we can show a screenshot).  This is the kind of task for which LLMs are perhaps less well suited, something Yann Lecun has pointed out.

Very good!  Just one more thing.  I can see on the PDFs that the numbers are printed directly on the vertices and well centered.  That's correct.  However, in a typical Slants puzzle, the givens numbers have circles behind them so you can see them more easily. Each circle has a white fill and black outline.  Also make the givens font a tad bigger.  The sample_puzzle.png shows what it looks like.

[that worked, but created a new problem]

When fitting the puzzle into its quadrant, you need to take the circle radii into account, so the circles don't extend out of the quadrant, or into the puzzle number.  You can either change the way you compute the printed width/height, or compensate via downscaling when you render the puzzle.

Puzzle number is still a little too close to the puzzle, and overlaps circles in the upper/left corner vertex,  when they occur. You may need to leave a gap for it and give it more distance from the puzzle.

[ at this point, I’d see we’ve accomplished our goa.l ]

Nice!  Let's make a couple more sample puzzle sets.  60 12x12 puzzles, 60 15x15 puzzles.

Let's make some larger brute force testsuites, akin to testsuites/GEN_small_testsuite.txt but larger.  Keep increasing the size by 2 in each dimension until it takes longer than 30 minutes to generate a suite.  Then  tell me how well the PR solver is doing on the new suites.
