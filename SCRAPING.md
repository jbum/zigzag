# SCRAPING.md


## simon tatham's site

URL: https://www.chiark.greenend.org.uk/~sgtatham/puzzles/js/slant.html

It is possible to scrape these puzzles using puppeteer or similar, and we don't need
to make screen snapshots.  The page has a "Type" pulldown for selecting one of the built-in sizes or a custom size.  We will scrape 10 each from the built-in sizes/difficulties (e.g. 5x5 Easy, 5x5 Hard, 8x8 Easy, and so on).  To get the givens for a specific puzzle, look at the button that goes to the link id for the puzzle.  The destination URL contains
the dimensions and givens as a parameter.  For example:

https://www.chiark.greenend.org.uk/~sgtatham/puzzles/js/slant.html#8x8:c120a0b21h3a2114f3a2b2a4b2110a1a1b1c2132d1b1a33a1a1c0b

Use the "New Puzzle" button to generate new puzzles.

## puzzle-slant.com

URL: https://www.puzzle-slant.com/

This site has a series of buttons on the left which navigate to the various built-in sizes, from 5x5 Easy to 20x20 Normal.  Difficulties are Easy and Normal, sizes are 5x5, 7x7, 10x10, 15x15, 20x20.  Ignore the specials.
It is unclear to me if the puzzle is represented in the page source.  If not, you can parse it by taking a snapshot of the puzzle canvas and looking for numbers inside of circles on the vertices. In lieu of taking a snapshot, you can download the progress screenshot, which is given in the sharing links section.  You can download all the screenshots you need and then make a script for parsing them into a test suite separately.

There is a "New Puzzle" button to generate new puzzles at the current size.
https://www.puzzle-slant.com/?pl=3662100d805f93987d1f7f845970ab626976df66f3ea4