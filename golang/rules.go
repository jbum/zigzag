package main

// Rule represents a production rule for solving Slants puzzles.
type Rule struct {
	Name  string
	Score int
	Tier  int
	Func  func(*Board) bool
}

// Rules is the list of rules used by the solver.
var Rules = []Rule{
	{"clue_finish_b", 1, 1, ruleClueFinishB},
	{"clue_finish_a", 2, 1, ruleClueFinishA},
	{"no_loops", 2, 1, ruleNoLoops},
	{"edge_clue_constraints", 2, 2, ruleEdgeClueConstraints},
	{"border_two_v_shape", 3, 2, ruleBorderTwoVShape},
	{"loop_avoidance_2", 5, 1, ruleLoopAvoidance2},
	{"v_pattern_with_three", 6, 2, ruleVPatternWithThree},
	{"adjacent_ones", 8, 2, ruleAdjacentOnes},
	{"adjacent_threes", 8, 2, ruleAdjacentThrees},
	{"dead_end_avoidance", 9, 2, ruleDeadEndAvoidance},
	{"equivalence_classes", 9, 2, ruleEquivalenceClasses},
	{"vbitmap_propagation", 9, 2, ruleVBitmapPropagation},
	{"simon_unified", 9, 2, ruleSimonUnified},
}

// ruleClueFinishA: If a clue needs all remaining unknowns to touch, fill them.
func ruleClueFinishA(board *Board) bool {
	madeProgress := false

	for _, vertex := range board.GetCluedVertices() {
		adjacent := board.GetAdjacentCellsForVertex(vertex)
		clue := vertex.Clue

		currentTouches := 0
		var unknownCells []AdjacentCellInfo

		for _, adj := range adjacent {
			if adj.Cell.Value == UNKNOWN {
				unknownCells = append(unknownCells, adj)
			} else if adj.Cell.Value == SLASH && adj.SlashTouches {
				currentTouches++
			} else if adj.Cell.Value == BACKSLASH && adj.BackslashTouches {
				currentTouches++
			}
		}

		neededTouches := clue - currentTouches

		// If all unknowns must touch to reach the clue
		if neededTouches > 0 && neededTouches == len(unknownCells) {
			for _, adj := range unknownCells {
				if adj.SlashTouches {
					if !board.WouldFormLoop(adj.Cell, SLASH) {
						board.PlaceValue(adj.Cell, SLASH)
						madeProgress = true
					}
				} else {
					if !board.WouldFormLoop(adj.Cell, BACKSLASH) {
						board.PlaceValue(adj.Cell, BACKSLASH)
						madeProgress = true
					}
				}
			}
		}
	}

	return madeProgress
}

// ruleClueFinishB: If a clue already has enough touches, fill avoiders.
func ruleClueFinishB(board *Board) bool {
	madeProgress := false

	for _, vertex := range board.GetCluedVertices() {
		adjacent := board.GetAdjacentCellsForVertex(vertex)
		clue := vertex.Clue

		currentTouches := 0
		var unknownCells []AdjacentCellInfo

		for _, adj := range adjacent {
			if adj.Cell.Value == UNKNOWN {
				unknownCells = append(unknownCells, adj)
			} else if adj.Cell.Value == SLASH && adj.SlashTouches {
				currentTouches++
			} else if adj.Cell.Value == BACKSLASH && adj.BackslashTouches {
				currentTouches++
			}
		}

		// If we already have enough touches, remaining must avoid
		if currentTouches == clue && len(unknownCells) > 0 {
			for _, adj := range unknownCells {
				if adj.SlashTouches {
					// Slash would touch, so place backslash to avoid
					if !board.WouldFormLoop(adj.Cell, BACKSLASH) {
						board.PlaceValue(adj.Cell, BACKSLASH)
						madeProgress = true
					}
				} else {
					// Backslash would touch, so place slash to avoid
					if !board.WouldFormLoop(adj.Cell, SLASH) {
						board.PlaceValue(adj.Cell, SLASH)
						madeProgress = true
					}
				}
			}
		}
	}

	return madeProgress
}

// ruleNoLoops: If placing one diagonal creates a loop, place the other.
func ruleNoLoops(board *Board) bool {
	madeProgress := false

	for _, cell := range board.GetUnknownCells() {
		slashLoops := board.WouldFormLoop(cell, SLASH)
		backslashLoops := board.WouldFormLoop(cell, BACKSLASH)

		if slashLoops && !backslashLoops {
			board.PlaceValue(cell, BACKSLASH)
			madeProgress = true
		} else if backslashLoops && !slashLoops {
			board.PlaceValue(cell, SLASH)
			madeProgress = true
		}
	}

	return madeProgress
}

// ruleEdgeClueConstraints: Edge/corner vertices have stricter constraints.
func ruleEdgeClueConstraints(board *Board) bool {
	madeProgress := false

	for _, vertex := range board.GetCluedVertices() {
		adjacent := board.GetAdjacentCellsForVertex(vertex)
		maxPossible := len(adjacent)
		clue := vertex.Clue

		if clue > maxPossible {
			continue
		}

		// If clue equals max possible, all must touch
		if clue == maxPossible {
			for _, adj := range adjacent {
				if adj.Cell.Value != UNKNOWN {
					continue
				}
				if adj.SlashTouches {
					if !board.WouldFormLoop(adj.Cell, SLASH) {
						board.PlaceValue(adj.Cell, SLASH)
						madeProgress = true
					}
				} else {
					if !board.WouldFormLoop(adj.Cell, BACKSLASH) {
						board.PlaceValue(adj.Cell, BACKSLASH)
						madeProgress = true
					}
				}
			}
		}
	}

	return madeProgress
}

// ruleBorderTwoVShape: A 2 on the border with only 2 adjacent cells forces V-shape.
func ruleBorderTwoVShape(board *Board) bool {
	madeProgress := false

	for _, vertex := range board.GetCluedVertices() {
		if vertex.Clue != 2 {
			continue
		}

		adjacent := board.GetAdjacentCellsForVertex(vertex)
		if len(adjacent) != 2 {
			continue
		}

		current, unknown := board.CountTouches(vertex)
		if current+unknown == 2 && unknown > 0 {
			for _, adj := range adjacent {
				if adj.Cell.Value != UNKNOWN {
					continue
				}
				if adj.SlashTouches {
					if !board.WouldFormLoop(adj.Cell, SLASH) {
						board.PlaceValue(adj.Cell, SLASH)
						madeProgress = true
					}
				} else {
					if !board.WouldFormLoop(adj.Cell, BACKSLASH) {
						board.PlaceValue(adj.Cell, BACKSLASH)
						madeProgress = true
					}
				}
			}
		}
	}

	return madeProgress
}

// ruleLoopAvoidance2: Detect when finishing a 2 would force a loop.
func ruleLoopAvoidance2(board *Board) bool {
	madeProgress := false

	for _, vertex := range board.GetCluedVertices() {
		if vertex.Clue != 2 {
			continue
		}

		adjacent := board.GetAdjacentCellsForVertex(vertex)
		currentTouches := 0
		var unknownCells []AdjacentCellInfo

		for _, adj := range adjacent {
			if adj.Cell.Value == UNKNOWN {
				unknownCells = append(unknownCells, adj)
			} else if adj.Cell.Value == SLASH && adj.SlashTouches {
				currentTouches++
			} else if adj.Cell.Value == BACKSLASH && adj.BackslashTouches {
				currentTouches++
			}
		}

		if currentTouches != 0 || len(unknownCells) != 2 {
			continue
		}

		// Both unknowns must touch
		cell1, slash1 := unknownCells[0].Cell, unknownCells[0].SlashTouches
		cell2, slash2 := unknownCells[1].Cell, unknownCells[1].SlashTouches

		val1 := BACKSLASH
		if slash1 {
			val1 = SLASH
		}
		val2 := BACKSLASH
		if slash2 {
			val2 = SLASH
		}

		// Save state and try
		state := board.SaveState()

		if board.WouldFormLoop(cell1, val1) {
			board.RestoreState(state)
			continue
		}

		board.PlaceValue(cell1, val1)

		if board.WouldFormLoop(cell2, val2) {
			// Would form loop - contradiction
			board.RestoreState(state)
			continue
		}

		board.RestoreState(state)
	}

	return madeProgress
}

// ruleVPatternWithThree: V pattern with 3 clue detection.
func ruleVPatternWithThree(board *Board) bool {
	madeProgress := false

	for y := 0; y < board.Height; y++ {
		for x := 0; x < board.Width-1; x++ {
			cellLeft := board.GetCell(x, y)
			cellRight := board.GetCell(x+1, y)

			if cellLeft == nil || cellRight == nil {
				continue
			}

			// Check for \/ pattern (V pointing down)
			if cellLeft.Value == BACKSLASH && cellRight.Value == SLASH {
				vertexAbove := board.GetVertex(x+1, y)
				if vertexAbove != nil && vertexAbove.HasClue && vertexAbove.Clue == 3 {
					current, unknown := board.CountTouches(vertexAbove)
					if current == 2 && unknown > 0 {
						for _, adj := range board.GetAdjacentCellsForVertex(vertexAbove) {
							if adj.Cell.Value != UNKNOWN || adj.Cell.Y >= y {
								continue
							}
							if adj.SlashTouches {
								if !board.WouldFormLoop(adj.Cell, SLASH) {
									board.PlaceValue(adj.Cell, SLASH)
									madeProgress = true
								}
							} else {
								if !board.WouldFormLoop(adj.Cell, BACKSLASH) {
									board.PlaceValue(adj.Cell, BACKSLASH)
									madeProgress = true
								}
							}
						}
					}
				}
			}

			// Check for /\ pattern (V pointing up)
			if cellLeft.Value == SLASH && cellRight.Value == BACKSLASH {
				vertexBelow := board.GetVertex(x+1, y+1)
				if vertexBelow != nil && vertexBelow.HasClue && vertexBelow.Clue == 3 {
					current, unknown := board.CountTouches(vertexBelow)
					if current == 2 && unknown > 0 {
						for _, adj := range board.GetAdjacentCellsForVertex(vertexBelow) {
							if adj.Cell.Value != UNKNOWN || adj.Cell.Y <= y {
								continue
							}
							if adj.SlashTouches {
								if !board.WouldFormLoop(adj.Cell, SLASH) {
									board.PlaceValue(adj.Cell, SLASH)
									madeProgress = true
								}
							} else {
								if !board.WouldFormLoop(adj.Cell, BACKSLASH) {
									board.PlaceValue(adj.Cell, BACKSLASH)
									madeProgress = true
								}
							}
						}
					}
				}
			}
		}
	}

	return madeProgress
}

// ruleAdjacentOnes: Adjacent 1-1 pattern constraints.
func ruleAdjacentOnes(board *Board) bool {
	madeProgress := false

	for _, vertex := range board.GetCluedVertices() {
		if vertex.Clue != 1 {
			continue
		}

		vx, vy := vertex.VX, vertex.VY
		current, _ := board.CountTouches(vertex)

		if current == 1 {
			// Check adjacent 1s and mark shared cells as avoiders
			directions := [][2]int{{1, 0}, {-1, 0}, {0, 1}, {0, -1}}
			for _, dir := range directions {
				neighbor := board.GetVertex(vx+dir[0], vy+dir[1])
				if neighbor == nil || !neighbor.HasClue || neighbor.Clue != 1 {
					continue
				}

				neighborAdj := board.GetAdjacentCellsForVertex(neighbor)
				neighborCells := make(map[*Cell]bool)
				for _, n := range neighborAdj {
					neighborCells[n.Cell] = true
				}

				for _, adj := range board.GetAdjacentCellsForVertex(vertex) {
					if adj.Cell.Value != UNKNOWN {
						continue
					}
					if neighborCells[adj.Cell] {
						// Shared cell - must avoid this vertex
						if adj.SlashTouches {
							if !board.WouldFormLoop(adj.Cell, BACKSLASH) {
								board.PlaceValue(adj.Cell, BACKSLASH)
								madeProgress = true
							}
						} else {
							if !board.WouldFormLoop(adj.Cell, SLASH) {
								board.PlaceValue(adj.Cell, SLASH)
								madeProgress = true
							}
						}
					}
				}
			}
		}
	}

	return madeProgress
}

// ruleAdjacentThrees: Adjacent 3-3 pattern constraints.
func ruleAdjacentThrees(board *Board) bool {
	madeProgress := false

	for _, vertex := range board.GetCluedVertices() {
		if vertex.Clue != 3 {
			continue
		}

		vx, vy := vertex.VX, vertex.VY
		current, _ := board.CountTouches(vertex)

		directions := [][2]int{{1, 0}, {-1, 0}, {0, 1}, {0, -1}}
		for _, dir := range directions {
			neighbor := board.GetVertex(vx+dir[0], vy+dir[1])
			if neighbor == nil || !neighbor.HasClue || neighbor.Clue != 3 {
				continue
			}

			myAdj := board.GetAdjacentCellsForVertex(vertex)
			neighborAdj := board.GetAdjacentCellsForVertex(neighbor)
			neighborCells := make(map[*Cell]bool)
			for _, n := range neighborAdj {
				neighborCells[n.Cell] = true
			}

			var sharedCells, unsharedCells []AdjacentCellInfo
			for _, adj := range myAdj {
				if neighborCells[adj.Cell] {
					sharedCells = append(sharedCells, adj)
				} else {
					unsharedCells = append(unsharedCells, adj)
				}
			}

			var unsharedUnknown []AdjacentCellInfo
			for _, adj := range unsharedCells {
				if adj.Cell.Value == UNKNOWN {
					unsharedUnknown = append(unsharedUnknown, adj)
				}
			}

			if current+len(unsharedUnknown)+len(sharedCells) == 3 && len(unsharedUnknown) > 0 {
				for _, adj := range unsharedUnknown {
					if adj.SlashTouches {
						if !board.WouldFormLoop(adj.Cell, SLASH) {
							board.PlaceValue(adj.Cell, SLASH)
							madeProgress = true
						}
					} else {
						if !board.WouldFormLoop(adj.Cell, BACKSLASH) {
							board.PlaceValue(adj.Cell, BACKSLASH)
							madeProgress = true
						}
					}
				}
			}
		}
	}

	return madeProgress
}

// ruleDeadEndAvoidance: Prevent creating isolated regions.
func ruleDeadEndAvoidance(board *Board) bool {
	madeProgress := false

	for _, cell := range board.GetUnknownCells() {
		x, y := cell.X, cell.Y

		fSlash := false
		fBack := false

		// Check backslash: connects (x,y) to (x+1,y+1)
		tlExits := board.GetVertexGroupExits(x, y)
		brExits := board.GetVertexGroupExits(x+1, y+1)
		tlBorder := board.GetVertexGroupBorder(x, y)
		brBorder := board.GetVertexGroupBorder(x+1, y+1)

		if !tlBorder && !brBorder && tlExits <= 1 && brExits <= 1 {
			fSlash = true
		}

		// Check slash: connects (x+1,y) to (x,y+1)
		trExits := board.GetVertexGroupExits(x+1, y)
		blExits := board.GetVertexGroupExits(x, y+1)
		trBorder := board.GetVertexGroupBorder(x+1, y)
		blBorder := board.GetVertexGroupBorder(x, y+1)

		if !trBorder && !blBorder && trExits <= 1 && blExits <= 1 {
			fBack = true
		}

		// fSlash means "backslash is forbidden, force slash"
		// fBack means "slash is forbidden, force backslash"
		if fSlash && !fBack {
			if !board.WouldFormLoop(cell, SLASH) {
				board.PlaceValue(cell, SLASH)
				madeProgress = true
			}
		} else if fBack && !fSlash {
			if !board.WouldFormLoop(cell, BACKSLASH) {
				board.PlaceValue(cell, BACKSLASH)
				madeProgress = true
			}
		}
	}

	return madeProgress
}

// ruleEquivalenceClasses: Track and propagate cell equivalences.
func ruleEquivalenceClasses(board *Board) bool {
	madeProgress := false

	// First pass: establish equivalences from clues
	for _, vertex := range board.GetCluedVertices() {
		adjacent := board.GetAdjacentCellsForVertex(vertex)
		currentTouches := 0
		var unknownCells []AdjacentCellInfo

		for _, adj := range adjacent {
			if adj.Cell.Value == UNKNOWN {
				unknownCells = append(unknownCells, adj)
			} else if adj.Cell.Value == SLASH && adj.SlashTouches {
				currentTouches++
			} else if adj.Cell.Value == BACKSLASH && adj.BackslashTouches {
				currentTouches++
			}
		}

		needed := vertex.Clue - currentTouches

		if needed == 1 && len(unknownCells) == 2 {
			cell1 := unknownCells[0].Cell
			cell2 := unknownCells[1].Cell

			dx := cell1.X - cell2.X
			dy := cell1.Y - cell2.Y
			if dx < 0 {
				dx = -dx
			}
			if dy < 0 {
				dy = -dy
			}
			cellsAreAdjacent := (dx == 1 && dy == 0) || (dx == 0 && dy == 1)

			if cellsAreAdjacent {
				if board.MarkCellsEquivalent(cell1, cell2) {
					madeProgress = true
				}
			}
		}
	}

	// Second pass: propagate known values
	for _, cell := range board.GetUnknownCells() {
		equivValue := board.GetEquivalenceClassValue(cell)

		if equivValue != UNKNOWN {
			if !board.WouldFormLoop(cell, equivValue) {
				board.PlaceValue(cell, equivValue)
				madeProgress = true
			} else {
				otherValue := BACKSLASH
				if equivValue == BACKSLASH {
					otherValue = SLASH
				}
				if !board.WouldFormLoop(cell, otherValue) {
					board.PlaceValue(cell, otherValue)
					madeProgress = true
				}
			}
		}
	}

	return madeProgress
}

// ruleVBitmapPropagation: Track and propagate v-shape possibilities.
func ruleVBitmapPropagation(board *Board) bool {
	madeProgress := false
	w, h := board.Width, board.Height

	// Local vbitmap for this iteration
	vbitmap := make([][]int, h)
	for y := 0; y < h; y++ {
		vbitmap[y] = make([]int, w)
		for x := 0; x < w; x++ {
			vbitmap[y][x] = 0xF
		}
	}

	changed := true
	for changed {
		changed = false

		// Apply constraints from known cell values
		for y := 0; y < h; y++ {
			for x := 0; x < w; x++ {
				cell := board.GetCell(x, y)
				if cell.Value == UNKNOWN {
					continue
				}
				s := cell.Value
				old := vbitmap[y][x]
				if s == SLASH {
					vbitmap[y][x] &= ^0x5
					if x > 0 && (vbitmap[y][x-1]&0x2) != 0 {
						vbitmap[y][x-1] &= ^0x2
						changed = true
					}
					if y > 0 && (vbitmap[y-1][x]&0x8) != 0 {
						vbitmap[y-1][x] &= ^0x8
						changed = true
					}
				} else {
					vbitmap[y][x] &= ^0xA
					if x > 0 && (vbitmap[y][x-1]&0x1) != 0 {
						vbitmap[y][x-1] &= ^0x1
						changed = true
					}
					if y > 0 && (vbitmap[y-1][x]&0x4) != 0 {
						vbitmap[y-1][x] &= ^0x4
						changed = true
					}
				}
				if vbitmap[y][x] != old {
					changed = true
				}
			}
		}

		// Apply constraints from clues
		for vy := 1; vy < h; vy++ {
			for vx := 1; vx < w; vx++ {
				vertex := board.GetVertex(vx, vy)
				if vertex == nil || !vertex.HasClue {
					continue
				}
				c := vertex.Clue

				if c == 1 {
					old1 := vbitmap[vy-1][vx-1]
					old2 := vbitmap[vy][vx-1]
					old3 := vbitmap[vy-1][vx]
					vbitmap[vy-1][vx-1] &= ^0x5
					if vy < h {
						vbitmap[vy][vx-1] &= ^0x2
					}
					if vx < w {
						vbitmap[vy-1][vx] &= ^0x8
					}
					if vbitmap[vy-1][vx-1] != old1 || vbitmap[vy][vx-1] != old2 || vbitmap[vy-1][vx] != old3 {
						changed = true
					}
				} else if c == 3 {
					old1 := vbitmap[vy-1][vx-1]
					old2 := vbitmap[vy][vx-1]
					old3 := vbitmap[vy-1][vx]
					vbitmap[vy-1][vx-1] &= ^0xA
					if vy < h {
						vbitmap[vy][vx-1] &= ^0x1
					}
					if vx < w {
						vbitmap[vy-1][vx] &= ^0x4
					}
					if vbitmap[vy-1][vx-1] != old1 || vbitmap[vy][vx-1] != old2 || vbitmap[vy-1][vx] != old3 {
						changed = true
					}
				} else if c == 2 {
					oldTL := vbitmap[vy-1][vx-1]
					oldBL := vbitmap[vy][vx-1]
					oldTR := vbitmap[vy-1][vx]

					if vy < h {
						top := vbitmap[vy-1][vx-1] & 0x3
						bot := vbitmap[vy][vx-1] & 0x3
						vbitmap[vy-1][vx-1] &= ^(0x3 ^ bot)
						vbitmap[vy][vx-1] &= ^(0x3 ^ top)
					}

					if vx < w {
						left := vbitmap[vy-1][vx-1] & 0xC
						right := vbitmap[vy-1][vx] & 0xC
						vbitmap[vy-1][vx-1] &= ^(0xC ^ right)
						vbitmap[vy-1][vx] &= ^(0xC ^ left)
					}

					if vbitmap[vy-1][vx-1] != oldTL || vbitmap[vy][vx-1] != oldBL || vbitmap[vy-1][vx] != oldTR {
						changed = true
					}
				}
			}
		}

		// Mark equivalent cells
		for y := 0; y < h; y++ {
			for x := 0; x < w; x++ {
				cell := board.GetCell(x, y)

				if x+1 < w {
					rightCell := board.GetCell(x+1, y)
					if (vbitmap[y][x] & 0x3) == 0 {
						if board.MarkCellsEquivalent(cell, rightCell) {
							madeProgress = true
							changed = true
						}
					}
				}

				if y+1 < h {
					belowCell := board.GetCell(x, y+1)
					if (vbitmap[y][x] & 0xC) == 0 {
						if board.MarkCellsEquivalent(cell, belowCell) {
							madeProgress = true
							changed = true
						}
					}
				}
			}
		}
	}

	return madeProgress
}

// ruleSimonUnified: Unified rule mimicking Simon Tatham's solver.
func ruleSimonUnified(board *Board) bool {
	w, h := board.Width, board.Height
	W, H := w+1, h+1
	madeProgress := false
	doneSomething := true

	for doneSomething {
		doneSomething = false

		// Phase 1: Clue completion with equivalence tracking
		for vy := 0; vy < H; vy++ {
			for vx := 0; vx < W; vx++ {
				vertex := board.GetVertex(vx, vy)
				if vertex == nil || !vertex.HasClue {
					continue
				}

				c := vertex.Clue

				// Build list of neighbors
				type neighborInfo struct {
					cell      *Cell
					slashType int
				}
				var neighbours []neighborInfo

				if vx > 0 && vy > 0 {
					cell := board.GetCell(vx-1, vy-1)
					neighbours = append(neighbours, neighborInfo{cell, BACKSLASH})
				}
				if vx > 0 && vy < h {
					cell := board.GetCell(vx-1, vy)
					neighbours = append(neighbours, neighborInfo{cell, SLASH})
				}
				if vx < w && vy < h {
					cell := board.GetCell(vx, vy)
					neighbours = append(neighbours, neighborInfo{cell, BACKSLASH})
				}
				if vx < w && vy > 0 {
					cell := board.GetCell(vx, vy-1)
					neighbours = append(neighbours, neighborInfo{cell, SLASH})
				}

				if len(neighbours) == 0 {
					continue
				}

				nneighbours := len(neighbours)
				nu := 0
				nl := c

				lastCell := neighbours[nneighbours-1].cell
				lastEq := -1
				if lastCell.Value == UNKNOWN {
					lastEq = board.GetCellEquivRoot(lastCell)
				}

				meq := -1
				var mj1, mj2 *Cell

				for i := 0; i < nneighbours; i++ {
					cell := neighbours[i].cell
					slashType := neighbours[i].slashType
					if cell.Value == UNKNOWN {
						nu++
						if meq < 0 {
							eq := board.GetCellEquivRoot(cell)
							if eq == lastEq && lastCell != cell {
								meq = eq
								mj1 = lastCell
								mj2 = cell
								nl--
								nu -= 2
							} else {
								lastEq = eq
							}
						}
					} else {
						lastEq = -1
						if cell.Value == slashType {
							nl--
						}
					}
					lastCell = cell
				}

				if nl < 0 || nl > nu {
					continue
				}

				if nu > 0 && (nl == 0 || nl == nu) {
					for _, n := range neighbours {
						if n.cell == mj1 || n.cell == mj2 {
							continue
						}
						if n.cell.Value == UNKNOWN {
							var value int
							if nl > 0 {
								value = n.slashType
							} else {
								if n.slashType == SLASH {
									value = BACKSLASH
								} else {
									value = SLASH
								}
							}

							if !board.WouldFormLoop(n.cell, value) {
								board.PlaceValue(n.cell, value)
								doneSomething = true
								madeProgress = true
							}
						}
					}
				} else if nu == 2 && nl == 1 {
					lastIdx := -1
					for i := 0; i < nneighbours; i++ {
						cell := neighbours[i].cell
						if cell.Value == UNKNOWN && cell != mj1 && cell != mj2 {
							if lastIdx < 0 {
								lastIdx = i
							} else if lastIdx == i-1 || (lastIdx == 0 && i == nneighbours-1) {
								cell1 := neighbours[lastIdx].cell
								cell2 := neighbours[i].cell
								if board.MarkCellsEquivalent(cell1, cell2) {
									doneSomething = true
									madeProgress = true
								}
								break
							}
						}
					}
				}
			}
		}

		if doneSomething {
			continue
		}

		// Phase 2: Loop avoidance, dead-end avoidance, equivalence filling
		for y := 0; y < h; y++ {
			for x := 0; x < w; x++ {
				cell := board.GetCell(x, y)
				if cell.Value != UNKNOWN {
					continue
				}

				fs := false
				bs := false

				v := board.GetEquivalenceClassValue(cell)
				if v == SLASH {
					fs = true
				} else if v == BACKSLASH {
					bs = true
				}

				// Check backslash loop
				c1 := board.GetVertexRoot(x, y)
				c2 := board.GetVertexRoot(x+1, y+1)
				if c1 == c2 {
					fs = true
				}

				// Dead-end avoidance for backslash
				if !fs {
					if !board.GetVertexGroupBorder(x, y) &&
						!board.GetVertexGroupBorder(x+1, y+1) &&
						board.GetVertexGroupExits(x, y) <= 1 &&
						board.GetVertexGroupExits(x+1, y+1) <= 1 {
						fs = true
					}
				}

				// Check slash loop
				c1 = board.GetVertexRoot(x+1, y)
				c2 = board.GetVertexRoot(x, y+1)
				if c1 == c2 {
					bs = true
				}

				// Dead-end avoidance for slash
				if !bs {
					if !board.GetVertexGroupBorder(x+1, y) &&
						!board.GetVertexGroupBorder(x, y+1) &&
						board.GetVertexGroupExits(x+1, y) <= 1 &&
						board.GetVertexGroupExits(x, y+1) <= 1 {
						bs = true
					}
				}

				if fs && bs {
					continue
				}

				if fs {
					board.PlaceValue(cell, SLASH)
					doneSomething = true
					madeProgress = true
				} else if bs {
					board.PlaceValue(cell, BACKSLASH)
					doneSomething = true
					madeProgress = true
				}
			}
		}

		if doneSomething {
			continue
		}

		// Phase 3: V-bitmap propagation
		for y := 0; y < h; y++ {
			for x := 0; x < w; x++ {
				cell := board.GetCell(x, y)
				s := cell.Value

				if s != UNKNOWN {
					if x > 0 {
						leftCell := board.GetCell(x-1, y)
						bits := 0x1
						if s == SLASH {
							bits = 0x2
						}
						if board.VBitmapClear(leftCell, bits) {
							doneSomething = true
							madeProgress = true
						}
					}

					if x+1 < w {
						bits := 0x2
						if s == SLASH {
							bits = 0x1
						}
						if board.VBitmapClear(cell, bits) {
							doneSomething = true
							madeProgress = true
						}
					}

					if y > 0 {
						aboveCell := board.GetCell(x, y-1)
						bits := 0x4
						if s == SLASH {
							bits = 0x8
						}
						if board.VBitmapClear(aboveCell, bits) {
							doneSomething = true
							madeProgress = true
						}
					}

					if y+1 < h {
						bits := 0x8
						if s == SLASH {
							bits = 0x4
						}
						if board.VBitmapClear(cell, bits) {
							doneSomething = true
							madeProgress = true
						}
					}
				}

				if x+1 < w && (board.VBitmapGet(cell)&0x3) == 0 {
					rightCell := board.GetCell(x+1, y)
					if board.MarkCellsEquivalent(cell, rightCell) {
						doneSomething = true
						madeProgress = true
					}
				}

				if y+1 < h && (board.VBitmapGet(cell)&0xC) == 0 {
					belowCell := board.GetCell(x, y+1)
					if board.MarkCellsEquivalent(cell, belowCell) {
						doneSomething = true
						madeProgress = true
					}
				}
			}
		}

		// V-bitmap constraints from interior clues
		for vy := 1; vy < H-1; vy++ {
			for vx := 1; vx < W-1; vx++ {
				vertex := board.GetVertex(vx, vy)
				if vertex == nil || !vertex.HasClue {
					continue
				}

				c := vertex.Clue
				tl := board.GetCell(vx-1, vy-1)
				bl := board.GetCell(vx-1, vy)
				tr := board.GetCell(vx, vy-1)

				if c == 1 {
					if board.VBitmapClear(tl, 0x5) {
						doneSomething = true
						madeProgress = true
					}
					if board.VBitmapClear(bl, 0x2) {
						doneSomething = true
						madeProgress = true
					}
					if board.VBitmapClear(tr, 0x8) {
						doneSomething = true
						madeProgress = true
					}
				} else if c == 3 {
					if board.VBitmapClear(tl, 0xA) {
						doneSomething = true
						madeProgress = true
					}
					if board.VBitmapClear(bl, 0x1) {
						doneSomething = true
						madeProgress = true
					}
					if board.VBitmapClear(tr, 0x4) {
						doneSomething = true
						madeProgress = true
					}
				} else if c == 2 {
					tlH := board.VBitmapGet(tl) & 0x3
					blH := board.VBitmapGet(bl) & 0x3
					if board.VBitmapClear(tl, 0x3^blH) {
						doneSomething = true
						madeProgress = true
					}
					if board.VBitmapClear(bl, 0x3^tlH) {
						doneSomething = true
						madeProgress = true
					}

					tlV := board.VBitmapGet(tl) & 0xC
					trV := board.VBitmapGet(tr) & 0xC
					if board.VBitmapClear(tl, 0xC^trV) {
						doneSomething = true
						madeProgress = true
					}
					if board.VBitmapClear(tr, 0xC^tlV) {
						doneSomething = true
						madeProgress = true
					}
				}
			}
		}
	}

	return madeProgress
}
