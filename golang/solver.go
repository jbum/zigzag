package main

import (
	"sort"
)

// SolveResult contains the result of solving a puzzle.
type SolveResult struct {
	Status         string // "solved", "unsolved", or "mult"
	SolutionString string
	WorkScore      int
	MaxTierUsed    int
}

// applyRulesUntilStuck applies rules repeatedly until no more progress.
func applyRulesUntilStuck(board *Board, rules []Rule) (int, int) {
	totalWorkScore := 0
	maxTierUsed := 0
	maxIterations := 1000

	for iteration := 0; iteration < maxIterations; iteration++ {
		if board.IsSolved() {
			break
		}

		if !board.IsValid() {
			break
		}

		madeProgress := false
		for _, rule := range rules {
			if rule.Func(board) {
				totalWorkScore += rule.Score
				if rule.Tier > maxTierUsed {
					maxTierUsed = rule.Tier
				}
				madeProgress = true
				break
			}
		}

		if !madeProgress {
			break
		}
	}

	return totalWorkScore, maxTierUsed
}

// pickBestCell picks the best cell for branching based on constraints.
func pickBestCell(board *Board) *Cell {
	unknownCells := board.GetUnknownCells()
	if len(unknownCells) == 0 {
		return nil
	}

	type cellScore struct {
		cell  *Cell
		score int
	}

	var scores []cellScore
	for _, cell := range unknownCells {
		score := 0
		tl, tr, bl, br := board.GetCellCorners(cell)

		for _, corner := range []*Vertex{tl, tr, bl, br} {
			if corner == nil || !corner.HasClue {
				continue
			}

			current, unknown := board.CountTouches(corner)
			clue := corner.Clue

			remainingNeeded := clue - current
			remainingSlots := unknown

			if remainingNeeded == remainingSlots {
				score += 100
			} else if remainingNeeded == 0 {
				score += 100
			} else if remainingSlots > 0 {
				score += 50 / remainingSlots
			}
		}

		scores = append(scores, cellScore{cell, score})
	}

	sort.Slice(scores, func(i, j int) bool {
		return scores[i].score > scores[j].score
	})

	return scores[0].cell
}

// getValidValues returns valid values for a cell.
func getValidValues(board *Board, cell *Cell) []int {
	type valuePriority struct {
		value    int
		priority int
	}

	var valid []valuePriority

	for _, value := range []int{SLASH, BACKSLASH} {
		if board.WouldFormLoop(cell, value) {
			continue
		}

		x, y := cell.X, cell.Y
		tl := board.GetVertex(x, y)
		tr := board.GetVertex(x+1, y)
		bl := board.GetVertex(x, y+1)
		br := board.GetVertex(x+1, y+1)

		var touches []*Vertex
		if value == SLASH {
			touches = []*Vertex{tr, bl}
		} else {
			touches = []*Vertex{tl, br}
		}

		isValid := true
		priority := 0

		for _, corner := range touches {
			if corner != nil && corner.HasClue {
				current, _ := board.CountTouches(corner)
				if current >= corner.Clue {
					isValid = false
					break
				}
				priority += 10
			}
		}

		if isValid {
			valid = append(valid, valuePriority{value, priority})
		}
	}

	sort.Slice(valid, func(i, j int) bool {
		return valid[i].priority > valid[j].priority
	})

	result := make([]int, len(valid))
	for i, v := range valid {
		result[i] = v.value
	}
	return result
}

// stackEntry represents an entry on the backtracking stack.
type stackEntry struct {
	state          *BoardState
	eliminatedValue int
}

// SolveBF solves a puzzle using brute-force backtracking.
func SolveBF(givensString string, width, height int, maxTier int) SolveResult {
	board, err := NewBoard(width, height, givensString)
	if err != nil {
		return SolveResult{Status: "unsolved", SolutionString: "", WorkScore: 0, MaxTierUsed: 0}
	}

	// Filter rules by tier
	var filteredRules []Rule
	for _, rule := range Rules {
		if rule.Tier <= maxTier {
			filteredRules = append(filteredRules, rule)
		}
	}

	var solutions []string
	stack := []stackEntry{{board.SaveState(), -1}}
	totalWorkScore := 0
	maxTierUsed := 0
	usedBranching := false
	pushPopScore := 0

	for len(stack) > 0 && len(solutions) < 2 {
		entry := stack[len(stack)-1]
		stack = stack[:len(stack)-1]
		board.RestoreState(entry.state)
		pushPopScore++

		// Apply rules
		workScore, tierUsed := applyRulesUntilStuck(board, filteredRules)
		totalWorkScore += workScore
		if tierUsed > maxTierUsed {
			maxTierUsed = tierUsed
		}

		// Check validity
		if !board.IsValid() {
			continue
		}

		// Check if solved
		if board.IsSolved() {
			if board.IsValidSolution() {
				solutions = append(solutions, board.ToSolutionString())
			}
			continue
		}

		// Choose cell for branching
		cell := pickBestCell(board)
		if cell == nil {
			continue
		}

		// Get valid values
		validValues := getValidValues(board, cell)
		if len(validValues) == 0 {
			continue
		}

		// Push states for each valid value
		savedState := board.SaveState()
		for i := len(validValues) - 1; i >= 0; i-- {
			value := validValues[i]
			board.RestoreState(savedState)
			err := board.PlaceValue(cell, value)
			if err == nil {
				stack = append(stack, stackEntry{board.SaveState(), value})
				pushPopScore++
				usedBranching = true
			}
		}
		board.RestoreState(savedState)
	}

	// Determine status
	var status string
	if len(solutions) >= 2 {
		status = "mult"
	} else if len(solutions) == 1 {
		status = "solved"
	} else {
		status = "unsolved"
	}

	// Get solution string
	var solutionString string
	if len(solutions) == 1 {
		solutionString = solutions[0]
	} else {
		solutionString = board.ToSolutionString()
	}

	// Add push/pop score
	totalWorkScore += pushPopScore * 2

	// If we used branching, promote to tier 3
	if usedBranching {
		maxTierUsed = 3
	}

	return SolveResult{
		Status:         status,
		SolutionString: solutionString,
		WorkScore:      totalWorkScore,
		MaxTierUsed:    maxTierUsed,
	}
}

// SolvePR solves a puzzle using production rules only (no backtracking).
func SolvePR(givensString string, width, height int, maxTier int) SolveResult {
	board, err := NewBoard(width, height, givensString)
	if err != nil {
		return SolveResult{Status: "unsolved", SolutionString: "", WorkScore: 0, MaxTierUsed: 0}
	}

	// Filter rules by tier
	var filteredRules []Rule
	for _, rule := range Rules {
		if rule.Tier <= maxTier {
			filteredRules = append(filteredRules, rule)
		}
	}

	totalWorkScore := 0
	maxTierUsed := 0
	maxIterations := 1000

	for iteration := 0; iteration < maxIterations; iteration++ {
		if board.IsSolved() {
			break
		}

		madeProgress := false
		for _, rule := range filteredRules {
			if rule.Func(board) {
				totalWorkScore += rule.Score
				if rule.Tier > maxTierUsed {
					maxTierUsed = rule.Tier
				}
				madeProgress = true
				break
			}
		}

		if !madeProgress {
			break
		}
	}

	var status string
	if board.IsSolved() && board.IsValidSolution() {
		status = "solved"
	} else {
		status = "unsolved"
	}

	return SolveResult{
		Status:         status,
		SolutionString: board.ToSolutionString(),
		WorkScore:      totalWorkScore,
		MaxTierUsed:    maxTierUsed,
	}
}
