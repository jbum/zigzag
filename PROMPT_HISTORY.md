# prompt history

This project was developed using a series of prompts in Claude code. The prompts are recorded here for posterity.

Read PROJECT.md and begin the steps.

[ This worked suprisingly well and only needed a few subsequent prompts, given here, to urge it forward.  Nonetheless, I wasn't sure how reliable this was, so I tried it two more times, in fresh directories, and those attempts did not work as well.  The problem was that the PROJECT.md file did not contain enough explicit language about regression testing, so it would mark steps complete even if they weren't implemented properly.  For this first run, however, it worked well, and did the necessary testing along the way. ]

[ The scraping subtask crashed at this point, while the foreground task was stuck at step 9. So I asked it to continue in the foreground, so I could monitor progress. ]

Our last session got interrupted.  Let's continue working on the scraping task from PROJECT.md. It looks like we have a candidate version of scrape_sgt.py, but I only see one puzzle in the SGT test suite.

Continue debugging the puzzle-slant scraper.

Make your own plan version of PROGRESS.md so you can track progress.  You are now on step 9.

(At this point, it was 10pm.  I probably should have said step 10, because I had already manually tested, and determined that the BF script was getting bogged down on some harder 15x15  puzzles in the PS test suite. I was curious to see if it would figure this out on its own and stop testing on those.  It wasted several minutes and then I interrupted it. )

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

### Refinements

Let's make some larger brute force testsuites, akin to testsuites/GEN_small_testsuite.txt but larger.  Keep increasing the size by 2 in each dimension until it takes longer than 30 minutes to generate a suite.  Then  tell me how well the PR solver is doing on the new suites.

commit these changes

What is the cost/tokens for this session?

The drawing function in the print script is currently drawing the solution after drawing the givens, which causes the slashes to overlap the givens.  Draw the solution prior to drawing the givens (and their circles) so that the givens are atop the solution.  Then regenerate the PDFs.

I've decided to publish this puzzle as "Zigzag" since "Slant" is considered a racial slur these days. Change the default title to "Zigzag Puzzles" in the print script and regenerate the pdfs.  Prior to regenerating the print scripts, make a utility shell script for regenerating the PDFs, make_pdfs.sh, so you can just run that.

Using grep, make some new filtered test suites. SGT_easy.txt is all the easy puzzles from SGT_testsuite.txt, SGT_hard is all the hard puzzles from SGT_testsuite.txt.  PS_easy is all the easy puzzles from PS_testsuite.txt and PS_normal is all the so-called normal puzzles from PS_testsuite.txt.  We'll use these new test suites to make some improvements.

Okay, I suspect a fairly small subset of the rules in the solver_PR can be used to solve the easy puzzles. Let's figure that out using the new easy test suites.  Add a new field to the rule lists (for both solvers PR and BF), "tier", which is 1 for the rules with a score less than 8, 2 for rules with a score >= 8 and < 10, and 3 for the remaining hard rules.  To the solve functions, add support for a max_tier parameter. If max_tier is 2, then only rules with a tier of <= 2 are used. An efficient way to accomplish this would be to pre-filter the working rule set. Once this is done, modify the solve_puzzles.py script to support max_tier specification (default to 10, a number we will likely never reach which will insure all rules are used).  Then, use solve_puzzles.py to figure out if both of the new easy test suites can be solved using -mt 1 (max_tier of 1).

The RULES_GENERATION list in the PR solver contains some redundant information.  Now that we've added tiers, it seems apparent that that list is just the regular RULES list with the tier 3 rules omitted.  If that is correct,  then we can simplify the generation solve logic to simply cap the max-tier at 2 for generation, and then use a single rule list.

commit the current changes

We have added tiers to the rules in both solvers and determined that PR solver can solve both of the "easy" testsuites with just the tier 1 rules (using -mt 1 with solve_puzzles.py). I suspect some of these easy rules (the ones lowest in the list, with higher work scores) are still not needed to solve all the easy puzzles, and therefore should be promoted to tier 2 (medium).  One at a time, working bottom up until you get to the no_loops rule, which is definitely required, try promoting an easy rule from tier 1 to tier 2, and then testing if we can still solve all the easy puzzles in both test suites.  If we can, leave the rule at tier=2, and proceed with the rule above it. When you're done, let me know which rules were promoted, if any.  If a rule is required for one of the test suites, but not the other, let me know that as well (there may be a difference in the difficulty levels between the two easy test suites).

[ this worked well ]

I am curious if either of the easy test suites can be solved without the no_loops rule.

[ nope ]

One at a time, try commenting out corner_zero and corner_four from the rule lists.  I suspect they may not be necessary to solve the easy puzzles, and may worsen solve time, since they probably only need to be checked once.

Check if removing both of these rules improves our solve times for the larger test suites for solve_PR.  If so, omit them from the rules file and omit from both solvers.

[ rules removed ]

/compact

I suspect we may be able to get a minor performance improvement by combining the two easy clue_finish rules into a single rule with a single vertex loop that checks both conditions (a and b).  Test if this is the case, using the larger test suites. If performance improves, replace the two rules with the new unified clue_finish rule.  Then update RULES.md to reflect the current rule sets.

[ i was wrong ]

Okay!  Let's examine the medium (tier=2) rules.  Check if removing any of them has no effect on our cumulative success rate on the large test suites, and improves our average performance.  For all these tests, use the PR solver with -mt 2 (so we won't invoke the hard rules).  If any medium rule is shown to be redundant AND worsening performance, leave it commented out, with a note.  After we've done all those tests, if any rules are commented out, also check if commenting them out from the BF solver improves performance.  Note that the BF solver currently can't solve the larger non-easy puzzles from the PS suite in a reasonable amount of time.

Nice. For the rules which did not worsen the success rate, but worsened the timing, indicate in RULES.md that these are heuristics which are redundant, but improve solve time.

Let's run `gen_puzzles.py -n 60 -w 10 -ht 10 -r 1 -s PR -sym -o puzzledata/puzzles_10x10_symmetry.txt` to test the effect of the symmetric clue removal. I am curious what the effect is on the average #givens, compared to the non-symmetric 10x10s.  Go ahead and print these to pdf so I can take a look.

open puzzledata/puzzles_10x10_symmetry.pdf

Modify the both solvers to return max-tier used during the solving process (the maximum tier# of any rule which made progress).  For the generator, output this information in the comment (tier=x). For the BF solver, if the solve invokes any stack-pushing, then the solve routine should automatically promote the puzzle to tier 3.  Since we don't use tier 3 rules for the PR solver when generating puzzles, I would expect that the max tier we should see on generated puzzles made with it is tier=2.  Confirm this is the case.  After all this, regenerate the puzzles in puzzledata/ so that we have max tier annotations.

I'm curious if there are some defaults causing the generated puzzles to always be tier 1, either in gen_puzzles or solve_PR.  I suspect not, but can you confirm?

[ at this point, it was determined that none of the current tier 2 rules were making enough progress to solve additional puzzles -- they basically functioned as speed heuristics for faster tier 3 solving ]

/compact

`grep Elapsed puzzledata/* shows that the 15x15s took 35.49s and the 12x12s took 12.75s.  Let's generate a set of 16x16.  Then you can get an expected lower bound on the time for the 17x17s by comparing the time for the 16x16s to the 15x15s.  Use pypy3 for generating these. Keep increasing the size until the expected lower bound exceeds 20 minutes.  I want to see how big we can get in a reasonable amount of time.

After we generate 25x25, go ahead and stop. 

[ ultimately made it to 27x27 manually ]


### more print fixes

Modify make_pdfs.sh to use 1 puzzle per page and 6 answers per page when puzzles are larger than 12x12.  If the shell script is getting unwieldy, convert it to python.

Modify the print script (print_puzzles_pdf.py) so that 12 answers-per-page is 3 columns and 4 rows and 6pp is 2 columns 3 rows. It is currently the inverse.  This new arrangement should better fit the portrait rectangle of the paper.  Then rerun make_pdfs.py.

modify make_pdfs.py to output the pdfs to the new ./pdfs/ directory, instead of ./puzzledata/

I am currently seeing about an inch of white space between the bottom of the last answer and the logo/instructions area, and the answers are too tightly packed.  Can you increase the available space so there is only 1/4 inch above the logo and the answers have more room?  If the answers are still overlapping, reduce them in size a bit.  Also, the answer numbers should now be lower down, but further to the left of the puzzle, where there is more room.

[ 10 similar prompts as we fixed the pdfs, it's spatial reasoning for pdf generation not great ]

/compress

### Mult test

I want to confirm the BF solver correctly identifies mults (puzzles with multiple solutions) and does not "solve" them. Ideally, after finding a solution, it should continue looking for additional solutions.  If it finds a second solution, then it can exit and should treat the puzzle as unsolved.  To test this, let's create a test suite with a single 2x2 puzzle that contains a single given vertex in the upper-left corner with a 1. This would be encoded as "1h".  Such a puzzle has multiple solutions.  Call this testsuites/mult_puzzle.txt.  Use solve_puzzles.py to run the BF puzzle on this puzzle and check if it thinks it is solvable.

[ it worked as desired, mult checking implemented correctly ]

Good. Now, the ./puzzledata/ directory contains several 60-puzzle collections that were generated with the PR solver.  I now want to create a few additional 60-puzzle collections with the BF solver. The first will be called ./puzzledata/puzzles_5x5_BF.txt (the _BF to distinguish it from the PR generated puzzles).  In all likelihood the BF solver is going to take a lot longer to generate these puzzles.  As we increase in size, compare the elapsed time of the two previous iterations and make a prediction about how long the next size is going to take.  If it's going to take longer than 10 minutes, stop.

Use -r 1 on these files. You can reference the existing collections to see the command lines that were used.

### Copying idea from Simon Tatham

The file /Users/jbum/Development/jbum_projects/puzzles/simon/puzzles-r8972/slant.c contains C source code for a constructor for Slant puzzles (the same kind we are working on).  I am curious if its solver contains any additional rules that are not currently in our rule set, or is it simply doing a brute force solve?

[ it identified 3 new rules ]

One at a time, let's add 3 equivalent rules to our PR solver, in the medium tier (2).  My goal is to be able to solve more of our test suite puzzles at -mt 2 than we can currently solve at -mt 1, without needing to invoke backtracking.  For each rule added, do a test and track what the improvement is.  Work score for these rules should be higher than our current medium rules, but lower than for our tier 3 rules (raise the scores for tier 3, if necessary).

[ over next few prompts, implementation was bugged, eventually fixed ]

Let's update our board representation (slants_board.py) so that equivalent groups of cells are tracked during the solve process.  The equivalence tracker rule should make progress when new equivalence deductions are made. I am hoping that this will help it work together with the v-bitmap or any other rule which needs equivalence info.  Also, if we have a known solution, and we make a mistaken equivalence assumption, we should catch it immediately, as we do for incorrect slashes.

I suspect the SGT test suite may have been generated with a newer version of the solver (since we're not yet solving SFT_hard at tier 2).  I've saved the latest version of Simon's solver in ./simon_slant.c.  Does it contain any new rules that were not in the older version we were looking at?  Is it pretty much the same?


Can you check to see if there is other information from Simon's rules that needs to be perpetuated in the board class in order for the rules to work together?  If the problem runs deeper than that, consider implementing simon's rules as a single rule that more closely mimics what he is doing.

/compact

The SGT hard puzzles were all generated by simon_slant.c.  Does this solver use look-ahead, in addition to the rules we've been working on?  If not, then there must be another reason why we can't solve the SGT hard testsuite with PR at -mt 2. Let's figure this out.

[ this finaly fixed the issue ]

Nice.  How are we doing on the PS testsuite?  try at -mt 1, -mt 2, -mt 3

Generate a set of 1000 10x10 puzzles using -PR tier 2. Then try to solve them with -BF.  I want to make sure the new tier 2 rules are suitable for generation (unlike our tier 3 rules). If these rules aren't, there will be puzzles that -BF can't solve.

Okay.  Try adding the simon rules to the BF solver.  I'm curious if it can solve the SGT test suite or the puzzles you just generated any faster with them, rather than without them.  (If not, then let's not keep them).
[ it improved performance significantly ]

Okay, can we finally solve the PS test suite in a reasonable amount of time with the BF solver?

[yes]

Did you save the 1000 puzzles you generated somewhere, where I can look at them?

[ i copied them out of /tmp ]

Okay.  Let's modify solve_puzzles.py to output an additional status line that shows the distribution of solved puzzles by tier.  Something like Tiers: 1=45 (45%) 2=40 (40%) 3=15 (15%)

### Generated Puzzle difficulty control

Okay.  The new rules are working well.  I want to add two new args to the gen_puzzles.py script -mingt (default=1) -maxgt (default=2) to help us get desired difficulty.  These are mininum generated tier and maximum generated tier respectively.  When -mingt == -maxgt, then we should generate puzzles all with the same tier level.  If -maxgt is 1, then we should only use easy rules as we reduce the givens, this should result in easy puzzles with more givens. If -mingt is 2, then we should use all the generation suitable rules, and throw out puzzles that are tier 1 after clue reduction.  Now the complicated bit: if -mingt is 1, and -maxgt is 2 (the defaults), then we want to generate roughly 50/50 puzzles of each type.  If we do nothing we're gonna get something like 98% puzzles which are tier 2. We don't want that.  Keep track of the current ratio and keep it 50/50.  If we have more tier 2 puzzles, generate more tier 1 puzzles, and vice versa doing something like (tier_to_generate = 2 if sum_tier_1 > sum-tier_2 else 1). Make a plan for this improvement to the generator, and then execute it.

[ this worked well ]

Read the Commands from the files in samplepuzzles/.  Then make a sh script called generate_samples.sh that executes each of these commands, using pypy3.

my bad, I meant puzzledata/*.txt

### Tool test
[ I installed some tools and wanted to test them]

How many puzzles varieties are on the krazydad.com website?



* * *

I've made a golang subdirectory.  In that directory, make a GO language port of solve_puzzles.py (and it's two solvers) so I can do a performance test of GO vs pypy3 for solving my test suites. In that directory, documenthow to invoke the solve_puzzles script. I am unsure if I have GO installed on this machine. If so, it probably needs to be updated.

[ GO ended up being 23x faster than pypy3]

[same with rust]

[ same with c++]

[ Since rust was the fastest, I ended up porting the generator to rust as well, and then managed to generate a larger test suite of brute force puzzles in a reasonable amount of time. ]

### Mults testing

The puzzles in puzzledata with _BF in the name were generated using a brute force solver with clues minimized. Theoretically, if I remove a single clue from these clues, it should result in a puzzle with multiple solutions. Such puzzles will be useful for testing the BF solver. Let's make a script make_mult_puzzles.py, it accepts an input file, such as puzzles_10x10_BF.txt. For each puzzle, it expands the givens, removes a single clue, and then reencodes the givens.  It then produces a new file with the same name as the input file with _mults added to the name.  It should use the recomputed givens, and leave the answer blank, since these puzzles don't have a single answer. In the comment block at the top, indicate how this file was produced. Run the script on puzzledata/puzzles_10x10_BF.txt, and then test the new file with the BF solver. I am expecitng to get a bunch of mults, but we'll see. Make a plan for this, and then execute it.

[ this worked well ]

Do the same mults conversion to puzzles_15x15_BF_rust.txt. Compare the BF solve times of the original with the mults version.

[ esc ] Perform the tests with pypy3 rather than python3
[ esc ] This run seems to be taking a long time!  Consider testing only 10 puzzles using the -n option.

Okay. I am assuming the BF solver always stops once a second mult is found. We don't want to waste time looking for additional mults, since 1 mult is enough to reject a puzzle.  Let's look at the cplusplus, golang and rust versions of the solver and confirm that they are detecting the mults, and doing so efficiently.

[ as before, Rust is fastest, then C, then Go, then Pypy3.  All solvers correctly identified the mults, and did so efficiently. ]

/compact

Let's make a new solver solver_SAP.py that will also work with our test harness. It should use a SAP algorithm and be able to solve all solvable puzzles. If you can have it do correct tier assignment, as solver_BF does, that would be nice (typically the tier 1 and tier 2 puzzles don't require look ahead and can be found prior to invoking the SAP algorithm).  I'm curious if this would be faster than solve_BF on puzzledata/puzzles_10x10_BF.txt.  Make a plan first.

[ esc ] Sorry, I meant SAT (boolean satisfiability).

[ worked a long time, did a lot of confirmation prompts -- this is a tough problem, due to the anti-loop rules in the puzzle, which make simple SAT solvers fail. Ultimately, the SAT solver proved to be slower and less reliable than the more targetted BF solver. I will likely encounterer similar issues with fillomino and slitherlink as well. ]