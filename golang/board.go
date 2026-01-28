// Package main implements a Slants (Gokigen Naname) puzzle solver in Go.
package main

import (
	"fmt"
	"strings"
)

// Cell values
const (
	UNKNOWN   = 0
	SLASH     = 1 // /  - connects bottom-left to top-right
	BACKSLASH = 2 // \  - connects top-left to bottom-right
)

// Vertex represents a vertex (corner point) in a Slants puzzle.
type Vertex struct {
	VX      int
	VY      int
	Clue    int  // -1 means no clue, 0-4 are valid clues
	HasClue bool // Whether this vertex has a clue
}

// Cell represents a single cell in a Slants puzzle.
type Cell struct {
	X     int
	Y     int
	Value int // UNKNOWN, SLASH, or BACKSLASH
}

// Board represents a Slants puzzle board.
type Board struct {
	Width    int
	Height   int
	Cells    []*Cell
	Vertices []*Vertex

	// Union-find for loop detection (vertex connectivity)
	parent []int
	rank   []int

	// Equivalence class tracking for cells
	equivParent []int
	equivRank   []int
	slashval    []int // Slash value for equivalence class root

	// V-bitmap tracking
	vbitmap []int

	// Exits and border tracking for dead-end avoidance
	exits  []int
	border []bool
}

// NewBoard creates a new Slants board.
func NewBoard(width, height int, givensString string) (*Board, error) {
	b := &Board{
		Width:  width,
		Height: height,
	}

	// Initialize cells
	b.Cells = make([]*Cell, width*height)
	for y := 0; y < height; y++ {
		for x := 0; x < width; x++ {
			b.Cells[y*width+x] = &Cell{X: x, Y: y, Value: UNKNOWN}
		}
	}

	// Decode givens and initialize vertices
	decodedClues := b.decodeGivens(givensString)
	expectedVertices := (width + 1) * (height + 1)

	if len(decodedClues) != expectedVertices {
		return nil, fmt.Errorf("givens decode to %d vertices, expected %d", len(decodedClues), expectedVertices)
	}

	b.Vertices = make([]*Vertex, expectedVertices)
	for i, clue := range decodedClues {
		vx := i % (width + 1)
		vy := i / (width + 1)
		b.Vertices[i] = &Vertex{
			VX:      vx,
			VY:      vy,
			Clue:    clue,
			HasClue: clue >= 0,
		}
	}

	// Initialize union-find for loop detection
	b.initUnionFind()

	// Initialize equivalence tracking
	b.initEquivalence()

	// Initialize v-bitmap
	b.initVBitmap()

	// Initialize exits/border
	b.initExitsBorder()

	return b, nil
}

func (b *Board) decodeGivens(givensString string) []int {
	var result []int
	for _, char := range givensString {
		if char >= '0' && char <= '4' {
			result = append(result, int(char-'0'))
		} else if char >= 'a' && char <= 'z' {
			runLength := int(char - 'a' + 1)
			for i := 0; i < runLength; i++ {
				result = append(result, -1) // -1 means no clue
			}
		}
	}
	return result
}

func (b *Board) initUnionFind() {
	numVertices := (b.Width + 1) * (b.Height + 1)
	b.parent = make([]int, numVertices)
	b.rank = make([]int, numVertices)
	for i := 0; i < numVertices; i++ {
		b.parent[i] = i
		b.rank[i] = 0
	}
}

func (b *Board) initEquivalence() {
	numCells := b.Width * b.Height
	b.equivParent = make([]int, numCells)
	b.equivRank = make([]int, numCells)
	b.slashval = make([]int, numCells)
	for i := 0; i < numCells; i++ {
		b.equivParent[i] = i
		b.equivRank[i] = 0
		b.slashval[i] = 0
	}
}

func (b *Board) initVBitmap() {
	numCells := b.Width * b.Height
	b.vbitmap = make([]int, numCells)
	for i := 0; i < numCells; i++ {
		b.vbitmap[i] = 0xF // All v-shapes initially possible
	}
}

func (b *Board) initExitsBorder() {
	W := b.Width + 1
	H := b.Height + 1
	numVertices := W * H

	b.exits = make([]int, numVertices)
	b.border = make([]bool, numVertices)

	for vy := 0; vy < H; vy++ {
		for vx := 0; vx < W; vx++ {
			idx := vy*W + vx
			// Border if on edge
			if vy == 0 || vy == H-1 || vx == 0 || vx == W-1 {
				b.border[idx] = true
			}
			// Exits = clue value, or 4 if no clue
			vertex := b.GetVertex(vx, vy)
			if vertex.HasClue {
				b.exits[idx] = vertex.Clue
			} else {
				b.exits[idx] = 4
			}
		}
	}
}

func (b *Board) find(x int) int {
	if b.parent[x] != x {
		b.parent[x] = b.find(b.parent[x])
	}
	return b.parent[x]
}

func (b *Board) union(x, y int) bool {
	rx, ry := b.find(x), b.find(y)
	if rx == ry {
		return false // Already connected - would form a loop
	}

	// Merge exits and border info
	mergedExits := b.exits[rx] + b.exits[ry] - 2
	mergedBorder := b.border[rx] || b.border[ry]

	if b.rank[rx] < b.rank[ry] {
		rx, ry = ry, rx
	}
	b.parent[ry] = rx
	if b.rank[rx] == b.rank[ry] {
		b.rank[rx]++
	}

	b.exits[rx] = mergedExits
	b.border[rx] = mergedBorder

	return true
}

func (b *Board) vertexIndex(vx, vy int) int {
	return vy*(b.Width+1) + vx
}

func (b *Board) cellIndex(cell *Cell) int {
	return cell.Y*b.Width + cell.X
}

func (b *Board) equivFind(x int) int {
	if b.equivParent[x] != x {
		b.equivParent[x] = b.equivFind(b.equivParent[x])
	}
	return b.equivParent[x]
}

// GetCell returns the cell at position (x, y), or nil if out of bounds.
func (b *Board) GetCell(x, y int) *Cell {
	if x >= 0 && x < b.Width && y >= 0 && y < b.Height {
		return b.Cells[y*b.Width+x]
	}
	return nil
}

// GetVertex returns the vertex at position (vx, vy), or nil if out of bounds.
func (b *Board) GetVertex(vx, vy int) *Vertex {
	if vx >= 0 && vx <= b.Width && vy >= 0 && vy <= b.Height {
		return b.Vertices[vy*(b.Width+1)+vx]
	}
	return nil
}

// GetCluedVertices returns all vertices with clues.
func (b *Board) GetCluedVertices() []*Vertex {
	var result []*Vertex
	for _, v := range b.Vertices {
		if v.HasClue {
			result = append(result, v)
		}
	}
	return result
}

// GetUnknownCells returns all cells without a determined value.
func (b *Board) GetUnknownCells() []*Cell {
	var result []*Cell
	for _, c := range b.Cells {
		if c.Value == UNKNOWN {
			result = append(result, c)
		}
	}
	return result
}

// AdjacentCellInfo contains information about a cell adjacent to a vertex.
type AdjacentCellInfo struct {
	Cell            *Cell
	SlashTouches    bool
	BackslashTouches bool
}

// GetAdjacentCellsForVertex returns cells adjacent to a vertex with touch info.
func (b *Board) GetAdjacentCellsForVertex(vertex *Vertex) []AdjacentCellInfo {
	vx, vy := vertex.VX, vertex.VY
	var adjacent []AdjacentCellInfo

	// Top-left cell (vertex is its bottom-right corner)
	if cell := b.GetCell(vx-1, vy-1); cell != nil {
		adjacent = append(adjacent, AdjacentCellInfo{cell, false, true})
	}
	// Top-right cell (vertex is its bottom-left corner)
	if cell := b.GetCell(vx, vy-1); cell != nil {
		adjacent = append(adjacent, AdjacentCellInfo{cell, true, false})
	}
	// Bottom-left cell (vertex is its top-right corner)
	if cell := b.GetCell(vx-1, vy); cell != nil {
		adjacent = append(adjacent, AdjacentCellInfo{cell, true, false})
	}
	// Bottom-right cell (vertex is its top-left corner)
	if cell := b.GetCell(vx, vy); cell != nil {
		adjacent = append(adjacent, AdjacentCellInfo{cell, false, true})
	}

	return adjacent
}

// CountTouches counts how many diagonals currently touch a vertex.
// Returns (currentCount, unknownCount).
func (b *Board) CountTouches(vertex *Vertex) (int, int) {
	current := 0
	unknown := 0

	for _, adj := range b.GetAdjacentCellsForVertex(vertex) {
		if adj.Cell.Value == UNKNOWN {
			unknown++
		} else if adj.Cell.Value == SLASH && adj.SlashTouches {
			current++
		} else if adj.Cell.Value == BACKSLASH && adj.BackslashTouches {
			current++
		}
	}

	return current, unknown
}

// WouldFormLoop checks if placing a value in a cell would form a loop.
func (b *Board) WouldFormLoop(cell *Cell, value int) bool {
	x, y := cell.X, cell.Y
	var v1, v2 int

	if value == SLASH {
		// Connects bottom-left (x, y+1) to top-right (x+1, y)
		v1 = b.vertexIndex(x, y+1)
		v2 = b.vertexIndex(x+1, y)
	} else { // BACKSLASH
		// Connects top-left (x, y) to bottom-right (x+1, y+1)
		v1 = b.vertexIndex(x, y)
		v2 = b.vertexIndex(x+1, y+1)
	}

	return b.find(v1) == b.find(v2)
}

// PlaceValue places a value in a cell and updates union-find.
func (b *Board) PlaceValue(cell *Cell, value int) error {
	if cell.Value != UNKNOWN {
		return nil
	}

	x, y := cell.X, cell.Y
	var v1, v2 int
	var nonV1X, nonV1Y, nonV2X, nonV2Y int

	if value == SLASH {
		v1 = b.vertexIndex(x, y+1)
		v2 = b.vertexIndex(x+1, y)
		nonV1X, nonV1Y = x, y       // top-left
		nonV2X, nonV2Y = x+1, y+1   // bottom-right
	} else { // BACKSLASH
		v1 = b.vertexIndex(x, y)
		v2 = b.vertexIndex(x+1, y+1)
		nonV1X, nonV1Y = x+1, y     // top-right
		nonV2X, nonV2Y = x, y+1     // bottom-left
	}

	if !b.union(v1, v2) {
		return fmt.Errorf("placing value at (%d,%d) would form a loop", x, y)
	}

	// Decrement exits for non-connected vertices
	b.decrExits(nonV1X, nonV1Y)
	b.decrExits(nonV2X, nonV2Y)

	cell.Value = value

	// Update slashval for this cell's equivalence class
	idx := b.cellIndex(cell)
	root := b.equivFind(idx)
	b.slashval[root] = value

	return nil
}

func (b *Board) decrExits(vx, vy int) {
	vertex := b.GetVertex(vx, vy)
	if vertex.HasClue {
		return // Clued vertices have fixed exits
	}
	idx := b.vertexIndex(vx, vy)
	root := b.find(idx)
	b.exits[root]--
}

// IsSolved checks if all cells have values.
func (b *Board) IsSolved() bool {
	for _, cell := range b.Cells {
		if cell.Value == UNKNOWN {
			return false
		}
	}
	return true
}

// IsValid checks if the current board state is valid.
func (b *Board) IsValid() bool {
	for _, vertex := range b.Vertices {
		if vertex.HasClue {
			current, _ := b.CountTouches(vertex)
			if current > vertex.Clue {
				return false
			}
		}
	}
	return true
}

// IsValidSolution checks if the board represents a valid complete solution.
func (b *Board) IsValidSolution() bool {
	if !b.IsSolved() {
		return false
	}
	for _, vertex := range b.Vertices {
		if vertex.HasClue {
			current, _ := b.CountTouches(vertex)
			if current != vertex.Clue {
				return false
			}
		}
	}
	return true
}

// ToSolutionString converts board to a solution string.
func (b *Board) ToSolutionString() string {
	var result strings.Builder
	for _, cell := range b.Cells {
		switch cell.Value {
		case SLASH:
			result.WriteByte('/')
		case BACKSLASH:
			result.WriteByte('\\')
		default:
			result.WriteByte('.')
		}
	}
	return result.String()
}

// BoardState holds a snapshot of the board state for backtracking.
type BoardState struct {
	cellValues  []int
	parent      []int
	rank        []int
	equivParent []int
	equivRank   []int
	slashval    []int
	vbitmap     []int
	exits       []int
	border      []bool
}

// SaveState returns a snapshot of the board state.
func (b *Board) SaveState() *BoardState {
	state := &BoardState{
		cellValues:  make([]int, len(b.Cells)),
		parent:      make([]int, len(b.parent)),
		rank:        make([]int, len(b.rank)),
		equivParent: make([]int, len(b.equivParent)),
		equivRank:   make([]int, len(b.equivRank)),
		slashval:    make([]int, len(b.slashval)),
		vbitmap:     make([]int, len(b.vbitmap)),
		exits:       make([]int, len(b.exits)),
		border:      make([]bool, len(b.border)),
	}

	for i, cell := range b.Cells {
		state.cellValues[i] = cell.Value
	}
	copy(state.parent, b.parent)
	copy(state.rank, b.rank)
	copy(state.equivParent, b.equivParent)
	copy(state.equivRank, b.equivRank)
	copy(state.slashval, b.slashval)
	copy(state.vbitmap, b.vbitmap)
	copy(state.exits, b.exits)
	copy(state.border, b.border)

	return state
}

// RestoreState restores board from a saved state.
func (b *Board) RestoreState(state *BoardState) {
	for i, cell := range b.Cells {
		cell.Value = state.cellValues[i]
	}
	copy(b.parent, state.parent)
	copy(b.rank, state.rank)
	copy(b.equivParent, state.equivParent)
	copy(b.equivRank, state.equivRank)
	copy(b.slashval, state.slashval)
	copy(b.vbitmap, state.vbitmap)
	copy(b.exits, state.exits)
	copy(b.border, state.border)
}

// GetCellCorners returns the 4 corner vertices of a cell.
func (b *Board) GetCellCorners(cell *Cell) (*Vertex, *Vertex, *Vertex, *Vertex) {
	x, y := cell.X, cell.Y
	return b.GetVertex(x, y), b.GetVertex(x+1, y), b.GetVertex(x, y+1), b.GetVertex(x+1, y+1)
}

// Equivalence class methods

// GetCellEquivRoot gets the equivalence class root index for a cell.
func (b *Board) GetCellEquivRoot(cell *Cell) int {
	idx := b.cellIndex(cell)
	return b.equivFind(idx)
}

// MarkCellsEquivalent marks two cells as equivalent.
func (b *Board) MarkCellsEquivalent(cell1, cell2 *Cell) bool {
	idx1 := b.cellIndex(cell1)
	idx2 := b.cellIndex(cell2)

	r1 := b.equivFind(idx1)
	r2 := b.equivFind(idx2)

	if r1 == r2 {
		return false // Already equivalent
	}

	// Check for slashval conflict
	sv1 := b.slashval[r1]
	sv2 := b.slashval[r2]
	if sv1 != 0 && sv2 != 0 && sv1 != sv2 {
		return false // Conflict
	}

	mergedSV := sv1
	if mergedSV == 0 {
		mergedSV = sv2
	}

	// Union by rank
	if b.equivRank[r1] < b.equivRank[r2] {
		r1, r2 = r2, r1
	}
	b.equivParent[r2] = r1
	if b.equivRank[r1] == b.equivRank[r2] {
		b.equivRank[r1]++
	}

	b.slashval[r1] = mergedSV

	return true
}

// GetEquivalenceClassValue gets the known value for a cell's equivalence class.
func (b *Board) GetEquivalenceClassValue(cell *Cell) int {
	idx := b.cellIndex(cell)
	root := b.equivFind(idx)
	return b.slashval[root]
}

// V-bitmap methods

// VBitmapGet gets the v-bitmap for a cell.
func (b *Board) VBitmapGet(cell *Cell) int {
	idx := b.cellIndex(cell)
	return b.vbitmap[idx]
}

// VBitmapClear clears specified bits from a cell's v-bitmap.
func (b *Board) VBitmapClear(cell *Cell, bits int) bool {
	idx := b.cellIndex(cell)
	old := b.vbitmap[idx]
	newVal := old &^ bits
	if newVal != old {
		b.vbitmap[idx] = newVal
		return true
	}
	return false
}

// Exits/border methods

// GetVertexRoot gets the root of the vertex group.
func (b *Board) GetVertexRoot(vx, vy int) int {
	idx := b.vertexIndex(vx, vy)
	return b.find(idx)
}

// GetVertexGroupExits gets the number of exits for a vertex group.
func (b *Board) GetVertexGroupExits(vx, vy int) int {
	root := b.GetVertexRoot(vx, vy)
	return b.exits[root]
}

// GetVertexGroupBorder checks if a vertex group includes a border vertex.
func (b *Board) GetVertexGroupBorder(vx, vy int) bool {
	root := b.GetVertexRoot(vx, vy)
	return b.border[root]
}

// String returns a visual representation of the board.
func (b *Board) String() string {
	var lines []string

	// Top border with vertex clues
	var topLine strings.Builder
	for vx := 0; vx <= b.Width; vx++ {
		vertex := b.GetVertex(vx, 0)
		if vertex.HasClue {
			topLine.WriteString(fmt.Sprintf("%d", vertex.Clue))
		} else {
			topLine.WriteByte('.')
		}
		if vx < b.Width {
			topLine.WriteByte('-')
		}
	}
	lines = append(lines, topLine.String())

	for y := 0; y < b.Height; y++ {
		// Cell row
		var cellLine strings.Builder
		cellLine.WriteByte('|')
		for x := 0; x < b.Width; x++ {
			cell := b.GetCell(x, y)
			switch cell.Value {
			case SLASH:
				cellLine.WriteByte('/')
			case BACKSLASH:
				cellLine.WriteByte('\\')
			default:
				cellLine.WriteByte('.')
			}
			cellLine.WriteByte('|')
		}
		lines = append(lines, cellLine.String())

		// Vertex row
		var vertexLine strings.Builder
		for vx := 0; vx <= b.Width; vx++ {
			vertex := b.GetVertex(vx, y+1)
			if vertex.HasClue {
				vertexLine.WriteString(fmt.Sprintf("%d", vertex.Clue))
			} else {
				vertexLine.WriteByte('.')
			}
			if vx < b.Width {
				vertexLine.WriteByte('-')
			}
		}
		lines = append(lines, vertexLine.String())
	}

	return strings.Join(lines, "\n")
}
