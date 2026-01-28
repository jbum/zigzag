package main

import (
	"bufio"
	"flag"
	"fmt"
	"os"
	"strconv"
	"strings"
	"time"
)

// Puzzle represents a parsed puzzle from the testsuite file.
type Puzzle struct {
	Name    string
	Width   int
	Height  int
	Givens  string
	Answer  string
	Comment string
}

// parsePuzzleLine parses a single line from a testsuite file.
func parsePuzzleLine(line string) *Puzzle {
	line = strings.TrimSpace(line)
	if line == "" || strings.HasPrefix(line, "#") || strings.HasPrefix(line, ";") {
		return nil
	}

	parts := strings.Split(line, "\t")
	if len(parts) < 4 {
		return nil
	}

	width, err := strconv.Atoi(parts[1])
	if err != nil {
		return nil
	}
	height, err := strconv.Atoi(parts[2])
	if err != nil {
		return nil
	}

	puzzle := &Puzzle{
		Name:   parts[0],
		Width:  width,
		Height: height,
		Givens: parts[3],
	}

	if len(parts) > 4 {
		puzzle.Answer = parts[4]
	}
	if len(parts) > 5 {
		comment := parts[5]
		if strings.HasPrefix(comment, "#") {
			comment = strings.TrimPrefix(comment, "#")
			comment = strings.TrimSpace(comment)
		}
		puzzle.Comment = comment
	}

	return puzzle
}

// loadPuzzles loads puzzles from a testsuite file.
func loadPuzzles(filepath string) ([]*Puzzle, error) {
	file, err := os.Open(filepath)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	var puzzles []*Puzzle
	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		puzzle := parsePuzzleLine(scanner.Text())
		if puzzle != nil {
			puzzles = append(puzzles, puzzle)
		}
	}

	if err := scanner.Err(); err != nil {
		return nil, err
	}

	return puzzles, nil
}

func main() {
	// Parse command line arguments
	verbose := flag.Bool("v", false, "Output testsuite-compatible lines with work scores")
	debug := flag.Bool("d", false, "Show debug output for each puzzle")
	filter := flag.String("f", "", "Filter puzzles by partial name match")
	numPuzzles := flag.Int("n", 0, "Maximum number of puzzles to test (0 = all)")
	offset := flag.Int("ofst", 1, "Puzzle number to start at (1-based)")
	solver := flag.String("s", "BF", "Solver to use: PR (production rules) or BF (brute force)")
	maxTier := flag.Int("mt", 10, "Maximum rule tier to use (1, 2, or 3). Default 10 uses all rules")
	outputUnsolved := flag.Bool("ou", false, "Output list of unsolved puzzles (sorted by size)")

	flag.Parse()

	if flag.NArg() < 1 {
		fmt.Fprintf(os.Stderr, "Usage: solve_puzzles [options] <input_file>\n")
		flag.PrintDefaults()
		os.Exit(1)
	}

	inputFile := flag.Arg(0)

	// Load puzzles
	puzzles, err := loadPuzzles(inputFile)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error loading puzzles: %v\n", err)
		os.Exit(1)
	}

	if len(puzzles) == 0 {
		fmt.Fprintf(os.Stderr, "No puzzles found in %s\n", inputFile)
		os.Exit(1)
	}

	// Apply filter
	if *filter != "" {
		var filtered []*Puzzle
		for _, p := range puzzles {
			if strings.Contains(p.Name, *filter) {
				filtered = append(filtered, p)
			}
		}
		puzzles = filtered
		if len(puzzles) == 0 {
			fmt.Fprintf(os.Stderr, "No puzzles matching filter '%s'\n", *filter)
			os.Exit(1)
		}
	}

	// Apply offset and limit
	startIdx := *offset - 1
	if startIdx < 0 {
		startIdx = 0
	}
	if startIdx >= len(puzzles) {
		fmt.Fprintf(os.Stderr, "Offset %d is beyond the number of puzzles (%d)\n", *offset, len(puzzles))
		os.Exit(1)
	}

	puzzles = puzzles[startIdx:]

	if *numPuzzles > 0 && *numPuzzles < len(puzzles) {
		puzzles = puzzles[:*numPuzzles]
	}

	// Select solve function
	var solveFn func(string, int, int, int) SolveResult
	if *solver == "PR" {
		solveFn = SolvePR
	} else {
		solveFn = SolveBF
	}

	// Solve puzzles
	totalPuzzles := len(puzzles)
	solvedCount := 0
	unsolvedCount := 0
	multCount := 0
	totalWorkScore := 0
	var unsolvedPuzzles []*Puzzle
	totalUnsolvedSquares := 0
	tierCounts := map[int]int{1: 0, 2: 0, 3: 0}

	startTime := time.Now()

	for i, puzzle := range puzzles {
		puzzleNum := startIdx + i + 1

		if *debug {
			fmt.Printf("\n%s\n", strings.Repeat("=", 60))
			fmt.Printf("Puzzle %d: %s (%dx%d)\n", puzzleNum, puzzle.Name, puzzle.Width, puzzle.Height)
			fmt.Printf("Givens: %s\n", puzzle.Givens)
			fmt.Printf("%s\n", strings.Repeat("=", 60))
		}

		result := solveFn(puzzle.Givens, puzzle.Width, puzzle.Height, *maxTier)

		// Count unsolved squares
		unsolvedSquares := strings.Count(result.SolutionString, ".")
		totalUnsolvedSquares += unsolvedSquares

		isSolved := result.Status == "solved"
		isMult := result.Status == "mult"

		if isSolved {
			solvedCount++
			totalWorkScore += result.WorkScore
			if _, ok := tierCounts[result.MaxTierUsed]; ok {
				tierCounts[result.MaxTierUsed]++
			}

			if *debug && puzzle.Answer != "" && result.SolutionString != puzzle.Answer {
				fmt.Printf("NOTE: Solution differs from expected answer\n")
				fmt.Printf("  Got:      %s\n", result.SolutionString)
				fmt.Printf("  Expected: %s\n", puzzle.Answer)
			}
		} else if isMult {
			multCount++
			unsolvedPuzzles = append(unsolvedPuzzles, puzzle)
		} else {
			unsolvedCount++
			unsolvedPuzzles = append(unsolvedPuzzles, puzzle)
		}

		if *debug {
			fmt.Printf("\nStatus: %s, Work score: %d\n", strings.ToUpper(result.Status), result.WorkScore)
			if unsolvedSquares > 0 {
				fmt.Printf("Unsolved cells: %d\n", unsolvedSquares)
			}
		}

		if *verbose {
			solutionStr := ""
			if isSolved {
				solutionStr = result.SolutionString
			}
			var commentParts []string
			if puzzle.Comment != "" {
				commentParts = append(commentParts, puzzle.Comment)
			}
			commentParts = append(commentParts, fmt.Sprintf("work_score=%d", result.WorkScore))
			if !isSolved {
				commentParts = append(commentParts, fmt.Sprintf("status=%s", result.Status))
				if unsolvedSquares > 0 {
					commentParts = append(commentParts, fmt.Sprintf("unsolved=%d", unsolvedSquares))
				}
			}
			comment := strings.Join(commentParts, " ")

			fmt.Printf("%s\t%d\t%d\t%s\t%s\t# %s\n",
				puzzle.Name, puzzle.Width, puzzle.Height, puzzle.Givens, solutionStr, comment)
		}
	}

	elapsedTime := time.Since(startTime)

	// Print summary
	solvedPct := float64(0)
	if totalPuzzles > 0 {
		solvedPct = float64(solvedCount) / float64(totalPuzzles) * 100
	}
	unsolvedPct := float64(0)
	if totalPuzzles > 0 {
		unsolvedPct = float64(unsolvedCount+multCount) / float64(totalPuzzles) * 100
	}

	if !*verbose {
		fmt.Printf("\nInput file: %s\n", inputFile)
		fmt.Printf("Solver: %s\n", *solver)
		if *maxTier < 10 {
			fmt.Printf("Max tier: %d\n", *maxTier)
		}
		fmt.Printf("Puzzles tested: %d\n", totalPuzzles)
		fmt.Printf("Solved: %d (%.1f%%)\n", solvedCount, solvedPct)
		if multCount > 0 {
			fmt.Printf("Multiple solutions: %d\n", multCount)
		}
		fmt.Printf("Unsolved: %d (%.1f%%)\n", unsolvedCount, unsolvedPct)
		if solvedCount > 0 {
			var tierParts []string
			for tier := 1; tier <= 3; tier++ {
				count := tierCounts[tier]
				pct := float64(count) / float64(solvedCount) * 100
				tierParts = append(tierParts, fmt.Sprintf("%d=%d (%.0f%%)", tier, count, pct))
			}
			fmt.Printf("Tiers: %s\n", strings.Join(tierParts, " "))
		}
		fmt.Printf("Elapsed time: %.3fs\n", elapsedTime.Seconds())
		fmt.Printf("Total work score: %d\n", totalWorkScore)
		if solvedCount > 0 {
			fmt.Printf("Average work score per solved puzzle: %.1f\n", float64(totalWorkScore)/float64(solvedCount))
		}
	} else {
		fmt.Printf("# Summary: %d/%d (%.1f%%) solved, time=%.3fs, total_work_score=%d\n",
			solvedCount, totalPuzzles, solvedPct, elapsedTime.Seconds(), totalWorkScore)
	}

	// Output unsolved puzzles
	if *outputUnsolved && len(unsolvedPuzzles) > 0 {
		fmt.Println()
		fmt.Println("Unsolved puzzles (sorted by size):")

		// Sort by area, then by name
		type puzzleArea struct {
			puzzle *Puzzle
			area   int
		}
		var sorted []puzzleArea
		for _, p := range unsolvedPuzzles {
			sorted = append(sorted, puzzleArea{p, p.Width * p.Height})
		}
		for i := 0; i < len(sorted)-1; i++ {
			for j := i + 1; j < len(sorted); j++ {
				if sorted[i].area > sorted[j].area ||
					(sorted[i].area == sorted[j].area && sorted[i].puzzle.Name > sorted[j].puzzle.Name) {
					sorted[i], sorted[j] = sorted[j], sorted[i]
				}
			}
		}

		for _, s := range sorted {
			fmt.Printf("  %s: %dx%d (area=%d)\n", s.puzzle.Name, s.puzzle.Width, s.puzzle.Height, s.area)
		}
	}
}
