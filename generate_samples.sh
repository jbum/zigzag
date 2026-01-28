#!/bin/bash
# Generate sample puzzles for various sizes and solvers

set -e  # Exit on error

echo "Generating sample puzzles..."

# PR solver puzzles
pypy3 gen_puzzles.py -n 60 -w 5 -ht 5 -r 1 -s PR -o puzzledata/puzzles_5x5.txt
pypy3 gen_puzzles.py -n 60 -w 8 -ht 8 -r 1 -s PR -o puzzledata/puzzles_8x8.txt
pypy3 gen_puzzles.py -n 60 -w 10 -ht 10 -r 1 -s PR -o puzzledata/puzzles_10x10.txt
pypy3 gen_puzzles.py -n 60 -w 10 -ht 10 -r 1 -s PR -sym -o puzzledata/puzzles_10x10_symmetry.txt
pypy3 gen_puzzles.py -n 60 -w 12 -ht 12 -r 1 -s PR -o puzzledata/puzzles_12x12.txt
pypy3 gen_puzzles.py -n 60 -w 15 -ht 15 -r 1 -s PR -o puzzledata/puzzles_15x15.txt
pypy3 gen_puzzles.py -n 60 -w 21 -ht 21 -r 1 -s PR -o puzzledata/puzzles_21x21.txt
pypy3 gen_puzzles.py -n 60 -w 25 -ht 25 -r 1 -s PR -o puzzledata/puzzles_25x25.txt

# BF solver puzzles
pypy3 gen_puzzles.py -n 60 -w 5 -ht 5 -r 1 -s BF -o puzzledata/puzzles_5x5_BF.txt
pypy3 gen_puzzles.py -n 60 -w 8 -ht 8 -r 1 -s BF -o puzzledata/puzzles_8x8_BF.txt
pypy3 gen_puzzles.py -n 60 -w 10 -ht 10 -r 1 -s BF -o puzzledata/puzzles_10x10_BF.txt
pypy3 gen_puzzles.py -n 60 -w 12 -ht 12 -r 1 -s BF -o puzzledata/puzzles_12x12_BF.txt
pypy3 gen_puzzles.py -n 60 -w 15 -ht 15 -r 1 -s BF -o puzzledata/puzzles_15x15_BF.txt

echo "Done!"
