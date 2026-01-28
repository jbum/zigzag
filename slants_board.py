r"""
Shared Board, Vertex, and Cell classes for Slants (Gokigen Naname) puzzle solvers.

Grid Layout:
- Cells are in a width x height grid
- Vertices are at corners: (width+1) x (height+1) vertices
- Each cell contains either UNKNOWN (0), SLASH (1), or BACKSLASH (2)
- Each vertex may have a clue (0-4) indicating how many diagonals touch it

Diagonal orientation:
- SLASH (/) connects bottom-left corner to top-right corner
- BACKSLASH (\) connects top-left corner to bottom-right corner

Vertex-Cell relationship:
- Vertex at (vx, vy) can be touched by up to 4 cells:
  - Cell (vx-1, vy-1): BACKSLASH touches this vertex (bottom-right corner)
  - Cell (vx, vy-1): SLASH touches this vertex (bottom-left corner)
  - Cell (vx-1, vy): SLASH touches this vertex (top-right corner)
  - Cell (vx, vy): BACKSLASH touches this vertex (top-left corner)
"""

# Cell values
UNKNOWN = 0
SLASH = 1      # /  - connects bottom-left to top-right
BACKSLASH = 2  # \  - connects top-left to bottom-right


class SolverDebugError(Exception):
    """Raised when the solver makes a move that contradicts the known solution."""
    pass


class Vertex:
    """Represents a vertex (corner point) in a Slants puzzle."""

    def __init__(self, vx, vy, clue=None):
        self.vx = vx  # vertex x coordinate
        self.vy = vy  # vertex y coordinate
        self.clue = clue  # None or 0-4

    def __repr__(self):
        if self.clue is not None:
            return str(self.clue)
        return '.'


class Cell:
    """Represents a single cell in a Slants puzzle."""

    def __init__(self, x, y):
        self.x = x  # column (0-indexed)
        self.y = y  # row (0-indexed)
        self.value = UNKNOWN
        self.known_debug_value = None  # For debugging: the known correct value

    def set_value(self, value):
        """Set the cell's value."""
        if self.known_debug_value is not None and value != self.known_debug_value:
            raise SolverDebugError(
                f"Cell ({self.x},{self.y}): set_value({value}) but known value is {self.known_debug_value}"
            )
        self.value = value

    def __repr__(self):
        if self.value == SLASH:
            return '/'
        elif self.value == BACKSLASH:
            return '\\'
        return '.'


class Board:
    """Represents a Slants puzzle board."""

    def __init__(self, width, height, givens_string, known_solution=None):
        """
        Initialize a Slants board.

        Args:
            width: Number of cell columns
            height: Number of cell rows
            givens_string: RLE-encoded vertex clues
            known_solution: Optional solution string for debugging
        """
        self.width = width
        self.height = height
        self.known_solution = known_solution

        # Initialize cells (width x height grid)
        self.cells = []
        for y in range(height):
            for x in range(width):
                cell = Cell(x, y)
                # Set known debug value if solution provided
                if known_solution:
                    idx = y * width + x
                    if idx < len(known_solution):
                        sol_char = known_solution[idx]
                        if sol_char == '/':
                            cell.known_debug_value = SLASH
                        elif sol_char == '\\':
                            cell.known_debug_value = BACKSLASH
                self.cells.append(cell)

        # Initialize vertices ((width+1) x (height+1) grid)
        self.vertices = []
        decoded_clues = self._decode_givens(givens_string)
        expected_vertices = (width + 1) * (height + 1)

        if len(decoded_clues) != expected_vertices:
            raise ValueError(
                f"Givens decode to {len(decoded_clues)} vertices, expected {expected_vertices}"
            )

        for i, clue in enumerate(decoded_clues):
            vx = i % (width + 1)
            vy = i // (width + 1)
            vertex = Vertex(vx, vy, clue)
            self.vertices.append(vertex)

        # Union-find structure for loop detection
        # Each cell's two endpoints are nodes; we track connectivity
        self._init_union_find()

        # Union-find structure for cell equivalence tracking
        # Cells that must have the same slash orientation are in the same equivalence class
        self._init_equivalence()

        # V-bitmap tracking for v-shape possibilities
        # Each cell has 4 bits indicating which v-shapes are still possible
        self._init_vbitmap()

        # Exits and border tracking for dead-end avoidance
        self._init_exits_border()

    def _init_equivalence(self):
        """Initialize equivalence tracking for cells."""
        num_cells = self.width * self.height
        self._equiv_parent = list(range(num_cells))
        self._equiv_rank = [0] * num_cells
        # slashval[i] = slash value (SLASH/BACKSLASH/0) for equivalence class with root i
        # 0 means unknown, SLASH=1 means /, BACKSLASH=2 means \
        self._slashval = [0] * num_cells

    def _init_vbitmap(self):
        """
        Initialize v-bitmap tracking for cells.

        Each cell has 4 bits indicating which v-shapes are possible:
        - Bit 0 (0x1): > shape with cell to right (this=/, right=\\)
        - Bit 1 (0x2): < shape with cell to right (this=\\, right=/)
        - Bit 2 (0x4): v shape with cell below (this=/, below=\\)
        - Bit 3 (0x8): ^ shape with cell below (this=\\, below=/)

        The v-shape is defined by two adjacent cells forming a V pointing
        at their shared edge's midpoint.
        """
        num_cells = self.width * self.height
        # Initially all v-shapes are possible (0xF = 1111 binary)
        self._vbitmap = [0xF] * num_cells

    def _init_exits_border(self):
        """
        Initialize exits and border tracking for dead-end avoidance.

        - exits[v] = number of potential new connections for vertex group v
        - border[v] = True if vertex group v contains a border vertex

        A vertex on the grid edge starts with exits = clue value (or 4 if no clue).
        A border vertex is one on the edge of the grid.
        """
        W = self.width + 1
        H = self.height + 1
        num_vertices = W * H

        self._exits = [0] * num_vertices
        self._border = [False] * num_vertices

        for vy in range(H):
            for vx in range(W):
                idx = vy * W + vx
                # Border if on edge of grid
                if vy == 0 or vy == H - 1 or vx == 0 or vx == W - 1:
                    self._border[idx] = True

                # Exits = clue value, or 4 if no clue
                vertex = self.get_vertex(vx, vy)
                if vertex.clue is not None:
                    self._exits[idx] = vertex.clue
                else:
                    self._exits[idx] = 4

    def _equiv_find(self, x):
        """Find root of equivalence class with path compression."""
        if self._equiv_parent[x] != x:
            self._equiv_parent[x] = self._equiv_find(self._equiv_parent[x])
        return self._equiv_parent[x]

    def _cell_index(self, cell):
        """Convert cell to index."""
        return cell.y * self.width + cell.x

    def _cell_from_index(self, idx):
        """Convert index to cell."""
        return self.cells[idx]

    def get_cell_equiv_root(self, cell):
        """Get the equivalence class root index for a cell."""
        idx = self._cell_index(cell)
        return self._equiv_find(idx)

    def mark_cells_equivalent(self, cell1, cell2):
        """
        Mark two cells as equivalent (must have same slash orientation).

        Returns True if this was a new equivalence (progress made).
        Raises SolverDebugError if equivalence conflicts with known solution.
        Returns False and does NOT merge if slashval conflict detected.
        """
        idx1 = self._cell_index(cell1)
        idx2 = self._cell_index(cell2)

        r1 = self._equiv_find(idx1)
        r2 = self._equiv_find(idx2)

        if r1 == r2:
            return False  # Already equivalent, no progress

        # Check for conflict with known solution
        if self.known_solution:
            # Get known values for both cells
            val1 = cell1.known_debug_value
            val2 = cell2.known_debug_value
            if val1 is not None and val2 is not None and val1 != val2:
                raise SolverDebugError(
                    f"Equivalence error: cells ({cell1.x},{cell1.y}) and ({cell2.x},{cell2.y}) "
                    f"marked equivalent but have different known values ({val1} vs {val2})"
                )

        # Check for slashval conflict (like Simon's solver does)
        sv1 = self._slashval[r1]
        sv2 = self._slashval[r2]
        if sv1 != 0 and sv2 != 0 and sv1 != sv2:
            # Conflict - this equivalence is impossible
            return False

        # Propagate slashval
        merged_sv = sv1 if sv1 != 0 else sv2

        # Union by rank
        if self._equiv_rank[r1] < self._equiv_rank[r2]:
            r1, r2 = r2, r1
        self._equiv_parent[r2] = r1
        if self._equiv_rank[r1] == self._equiv_rank[r2]:
            self._equiv_rank[r1] += 1

        # Set merged slashval on new root
        self._slashval[r1] = merged_sv

        return True  # New equivalence established

    def are_cells_equivalent(self, cell1, cell2):
        """Check if two cells are in the same equivalence class."""
        idx1 = self._cell_index(cell1)
        idx2 = self._cell_index(cell2)
        return self._equiv_find(idx1) == self._equiv_find(idx2)

    def get_equivalent_cells(self, cell):
        """Get all cells in the same equivalence class as the given cell."""
        target_root = self._equiv_find(self._cell_index(cell))
        result = []
        for c in self.cells:
            if self._equiv_find(self._cell_index(c)) == target_root:
                result.append(c)
        return result

    def get_equivalence_class_value(self, cell):
        """
        Get the known value for a cell's equivalence class, if any cell in the class has a value.
        Returns UNKNOWN if no cell in the class has been filled.
        This is now O(1) using slashval.
        """
        idx = self._cell_index(cell)
        root = self._equiv_find(idx)
        return self._slashval[root]

    def set_equivalence_class_value(self, cell, value):
        """
        Set the slash value for a cell's equivalence class.
        Used when a cell is filled to propagate to its equivalence class.
        """
        idx = self._cell_index(cell)
        root = self._equiv_find(idx)
        self._slashval[root] = value

    # V-bitmap methods
    def vbitmap_get(self, cell):
        """Get the v-bitmap for a cell."""
        idx = self._cell_index(cell)
        return self._vbitmap[idx]

    def vbitmap_clear(self, cell, bits):
        """
        Clear specified bits from a cell's v-bitmap.
        Returns True if any bits were actually cleared (progress made).
        """
        idx = self._cell_index(cell)
        old = self._vbitmap[idx]
        new = old & ~bits
        if new != old:
            self._vbitmap[idx] = new
            return True
        return False

    # Exits/border methods
    def get_vertex_root(self, vx, vy):
        """Get the root of the vertex group for vertex at (vx, vy)."""
        idx = self._vertex_index(vx, vy)
        return self._find(idx)

    def get_vertex_group_exits(self, vx, vy):
        """Get the number of exits for the vertex group containing (vx, vy)."""
        root = self.get_vertex_root(vx, vy)
        return self._exits[root]

    def get_vertex_group_border(self, vx, vy):
        """Check if the vertex group containing (vx, vy) includes a border vertex."""
        root = self.get_vertex_root(vx, vy)
        return self._border[root]

    def _decr_exits(self, vx, vy):
        """
        Decrement exits count for a vertex (called when an edge no longer provides an exit).
        Only decrements for non-clued vertices, matching Simon's decr_exits behavior.
        """
        vertex = self.get_vertex(vx, vy)
        if vertex.clue is not None:
            return  # Clued vertices have fixed exits, don't decrement
        idx = self._vertex_index(vx, vy)
        root = self._find(idx)
        self._exits[root] -= 1

    def _decode_givens(self, givens_string):
        """
        Decode RLE-encoded givens string.

        Lowercase letters represent runs of unlabeled vertices (a=1, b=2, ..., z=26).
        Digits 0-4 represent clues.
        """
        result = []
        for char in givens_string:
            if char.isdigit():
                result.append(int(char))
            elif char.islower():
                # a=1, b=2, ..., z=26
                run_length = ord(char) - ord('a') + 1
                result.extend([None] * run_length)
        return result

    def encode_givens(self):
        """Encode current vertex clues to RLE string."""
        result = []
        unlabeled_count = 0

        for vertex in self.vertices:
            if vertex.clue is None:
                unlabeled_count += 1
            else:
                # Flush unlabeled run first
                while unlabeled_count > 0:
                    run = min(unlabeled_count, 26)
                    result.append(chr(ord('a') + run - 1))
                    unlabeled_count -= run
                result.append(str(vertex.clue))

        # Flush remaining unlabeled
        while unlabeled_count > 0:
            run = min(unlabeled_count, 26)
            result.append(chr(ord('a') + run - 1))
            unlabeled_count -= run

        return ''.join(result)

    def _init_union_find(self):
        """Initialize union-find for loop detection."""
        # Each cell has 4 corners, but we only care about connectivity of endpoints
        # For a slash: bottom-left and top-right are connected
        # For a backslash: top-left and bottom-right are connected
        # We track vertex connectivity through cell diagonals
        num_vertices = (self.width + 1) * (self.height + 1)
        self._parent = list(range(num_vertices))
        self._rank = [0] * num_vertices

    def _find(self, x):
        """Find root with path compression."""
        if self._parent[x] != x:
            self._parent[x] = self._find(self._parent[x])
        return self._parent[x]

    def _union(self, x, y):
        """Union by rank. Returns False if x and y were already connected (would form loop)."""
        rx, ry = self._find(x), self._find(y)
        if rx == ry:
            return False  # Already connected - would form a loop

        # Merge exits and border info before union
        # Subtract 2 because each group used one exit to form this connection
        merged_exits = self._exits[rx] + self._exits[ry] - 2
        merged_border = self._border[rx] or self._border[ry]

        if self._rank[rx] < self._rank[ry]:
            rx, ry = ry, rx
        self._parent[ry] = rx
        if self._rank[rx] == self._rank[ry]:
            self._rank[rx] += 1

        # Set merged values on new root
        self._exits[rx] = merged_exits
        self._border[rx] = merged_border

        return True

    def _vertex_index(self, vx, vy):
        """Convert vertex coordinates to index."""
        return vy * (self.width + 1) + vx

    def get_cell(self, x, y):
        """Get cell at position (x, y). Returns None if out of bounds."""
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.cells[y * self.width + x]
        return None

    def get_vertex(self, vx, vy):
        """Get vertex at position (vx, vy). Returns None if out of bounds."""
        if 0 <= vx <= self.width and 0 <= vy <= self.height:
            return self.vertices[vy * (self.width + 1) + vx]
        return None

    def get_cell_corners(self, cell):
        """Get the 4 corner vertices of a cell as (top_left, top_right, bottom_left, bottom_right)."""
        x, y = cell.x, cell.y
        return (
            self.get_vertex(x, y),       # top-left
            self.get_vertex(x + 1, y),   # top-right
            self.get_vertex(x, y + 1),   # bottom-left
            self.get_vertex(x + 1, y + 1)  # bottom-right
        )

    def get_adjacent_cells_for_vertex(self, vertex):
        """
        Get cells adjacent to a vertex with their relationship.

        Returns list of (cell, slash_touches, backslash_touches) tuples where:
        - slash_touches: True if a SLASH in this cell would touch the vertex
        - backslash_touches: True if a BACKSLASH in this cell would touch the vertex
        """
        vx, vy = vertex.vx, vertex.vy
        adjacent = []

        # Top-left cell (vertex is its bottom-right corner)
        cell = self.get_cell(vx - 1, vy - 1)
        if cell:
            adjacent.append((cell, False, True))  # Backslash touches bottom-right

        # Top-right cell (vertex is its bottom-left corner)
        cell = self.get_cell(vx, vy - 1)
        if cell:
            adjacent.append((cell, True, False))  # Slash touches bottom-left

        # Bottom-left cell (vertex is its top-right corner)
        cell = self.get_cell(vx - 1, vy)
        if cell:
            adjacent.append((cell, True, False))  # Slash touches top-right

        # Bottom-right cell (vertex is its top-left corner)
        cell = self.get_cell(vx, vy)
        if cell:
            adjacent.append((cell, False, True))  # Backslash touches top-left

        return adjacent

    def count_touches(self, vertex):
        """
        Count how many diagonals currently touch a vertex.

        Returns (current_count, unknown_count) where:
        - current_count: number of placed diagonals touching the vertex
        - unknown_count: number of adjacent cells still unknown
        """
        current = 0
        unknown = 0

        for cell, slash_touches, backslash_touches in self.get_adjacent_cells_for_vertex(vertex):
            if cell.value == UNKNOWN:
                unknown += 1
            elif cell.value == SLASH and slash_touches:
                current += 1
            elif cell.value == BACKSLASH and backslash_touches:
                current += 1

        return current, unknown

    def would_form_loop(self, cell, value):
        """
        Check if placing a value in a cell would form a loop.

        Uses union-find to track connectivity of vertices through diagonals.
        """
        x, y = cell.x, cell.y

        if value == SLASH:
            # Connects bottom-left (x, y+1) to top-right (x+1, y)
            v1 = self._vertex_index(x, y + 1)
            v2 = self._vertex_index(x + 1, y)
        else:  # BACKSLASH
            # Connects top-left (x, y) to bottom-right (x+1, y+1)
            v1 = self._vertex_index(x, y)
            v2 = self._vertex_index(x + 1, y + 1)

        # Check if already connected (would form loop)
        return self._find(v1) == self._find(v2)

    def place_value(self, cell, value):
        """
        Place a value in a cell and update union-find.

        Returns True if successful, raises error if would form loop.
        """
        if cell.value != UNKNOWN:
            return False

        x, y = cell.x, cell.y

        if value == SLASH:
            # Connects bottom-left (x, y+1) to top-right (x+1, y)
            v1 = self._vertex_index(x, y + 1)
            v2 = self._vertex_index(x + 1, y)
            # The non-connected vertices lose an exit
            non_v1 = (x, y)        # top-left
            non_v2 = (x + 1, y + 1)  # bottom-right
        else:  # BACKSLASH
            # Connects top-left (x, y) to bottom-right (x+1, y+1)
            v1 = self._vertex_index(x, y)
            v2 = self._vertex_index(x + 1, y + 1)
            # The non-connected vertices lose an exit
            non_v1 = (x + 1, y)    # top-right
            non_v2 = (x, y + 1)    # bottom-left

        # Union the vertices
        if not self._union(v1, v2):
            raise ValueError(f"Placing {value} at ({x},{y}) would form a loop")

        # Decrement exits for non-connected vertices
        self._decr_exits(*non_v1)
        self._decr_exits(*non_v2)

        cell.set_value(value)

        # Update slashval for this cell's equivalence class
        self.set_equivalence_class_value(cell, value)

        return True

    def get_clued_vertices(self):
        """Return all vertices that have clues."""
        return [v for v in self.vertices if v.clue is not None]

    def get_unknown_cells(self):
        """Return all cells without a determined value."""
        return [c for c in self.cells if c.value == UNKNOWN]

    def is_solved(self):
        """Check if all cells have values."""
        return all(cell.value != UNKNOWN for cell in self.cells)

    def is_valid(self):
        """
        Check if the current board state is valid.

        Checks that no vertex has more touches than its clue allows.
        """
        for vertex in self.vertices:
            if vertex.clue is not None:
                current, _ = self.count_touches(vertex)
                if current > vertex.clue:
                    return False
        return True

    def is_valid_solution(self):
        """
        Check if the board represents a valid complete solution.

        Checks:
        1. All cells have values
        2. All clued vertices have exactly the right number of touches
        3. No loops (guaranteed by union-find during construction)
        """
        if not self.is_solved():
            return False

        for vertex in self.vertices:
            if vertex.clue is not None:
                current, _ = self.count_touches(vertex)
                if current != vertex.clue:
                    return False

        return True

    def to_solution_string(self):
        """Convert board to a solution string of slash and backslash characters."""
        result = []
        for cell in self.cells:
            if cell.value == SLASH:
                result.append('/')
            elif cell.value == BACKSLASH:
                result.append('\\')
            else:
                result.append('.')
        return ''.join(result)

    def save_state(self):
        """Return a snapshot of the board state for backtracking."""
        return (
            [c.value for c in self.cells],
            self._parent.copy(),
            self._rank.copy(),
            self._equiv_parent.copy(),
            self._equiv_rank.copy(),
            self._slashval.copy(),
            self._vbitmap.copy(),
            self._exits.copy(),
            self._border.copy()
        )

    def restore_state(self, state):
        """Restore board from a saved state snapshot."""
        (cell_values, parent, rank, equiv_parent, equiv_rank,
         slashval, vbitmap, exits, border) = state
        for cell, value in zip(self.cells, cell_values):
            cell.value = value
        self._parent = parent.copy()
        self._rank = rank.copy()
        self._equiv_parent = equiv_parent.copy()
        self._equiv_rank = equiv_rank.copy()
        self._slashval = slashval.copy()
        self._vbitmap = vbitmap.copy()
        self._exits = exits.copy()
        self._border = border.copy()

    def disable_debug_checking(self):
        """Disable debug checking for backtracking."""
        for cell in self.cells:
            cell.known_debug_value = None
        self.known_solution = None

    def copy(self):
        """Create a deep copy of the board."""
        new_board = Board.__new__(Board)
        new_board.width = self.width
        new_board.height = self.height
        new_board.known_solution = self.known_solution

        # Copy cells
        new_board.cells = []
        for cell in self.cells:
            new_cell = Cell(cell.x, cell.y)
            new_cell.value = cell.value
            new_cell.known_debug_value = cell.known_debug_value
            new_board.cells.append(new_cell)

        # Copy vertices
        new_board.vertices = []
        for vertex in self.vertices:
            new_vertex = Vertex(vertex.vx, vertex.vy, vertex.clue)
            new_board.vertices.append(new_vertex)

        # Copy union-find
        new_board._parent = self._parent.copy()
        new_board._rank = self._rank.copy()

        # Copy equivalence tracking
        new_board._equiv_parent = self._equiv_parent.copy()
        new_board._equiv_rank = self._equiv_rank.copy()
        new_board._slashval = self._slashval.copy()

        # Copy vbitmap
        new_board._vbitmap = self._vbitmap.copy()

        # Copy exits/border
        new_board._exits = self._exits.copy()
        new_board._border = self._border.copy()

        return new_board

    def __repr__(self):
        """Display the board in a visual format."""
        lines = []

        # Top border with vertex clues
        top_line = ""
        for vx in range(self.width + 1):
            vertex = self.get_vertex(vx, 0)
            clue_str = str(vertex.clue) if vertex.clue is not None else '.'
            top_line += clue_str
            if vx < self.width:
                top_line += "-"
        lines.append(top_line)

        for y in range(self.height):
            # Cell row
            cell_line = "|"
            for x in range(self.width):
                cell = self.get_cell(x, y)
                cell_line += str(cell) + "|"
            lines.append(cell_line)

            # Vertex row
            vertex_line = ""
            for vx in range(self.width + 1):
                vertex = self.get_vertex(vx, y + 1)
                clue_str = str(vertex.clue) if vertex.clue is not None else '.'
                vertex_line += clue_str
                if vx < self.width:
                    vertex_line += "-"
            lines.append(vertex_line)

        return '\n'.join(lines)


def parse_puzzle_line(line):
    """
    Parse a puzzle line from a testsuite file.

    Returns dict with: name, width, height, givens, answer, comment
    Or None if line should be ignored.
    """
    line = line.strip()
    if not line or line.startswith('#') or line.startswith(';'):
        return None

    parts = line.split('\t')
    if len(parts) < 4:
        return None

    result = {
        'name': parts[0],
        'width': int(parts[1]),
        'height': int(parts[2]),
        'givens': parts[3],
        'answer': parts[4] if len(parts) > 4 else '',
        'comment': parts[5] if len(parts) > 5 else ''
    }

    # Strip leading # from comment if present
    if result['comment'].startswith('#'):
        result['comment'] = result['comment'][1:].strip()

    return result


def load_puzzles(filepath):
    """Load puzzles from a testsuite file."""
    puzzles = []
    with open(filepath, 'r') as f:
        for line in f:
            puzzle = parse_puzzle_line(line)
            if puzzle:
                puzzles.append(puzzle)
    return puzzles


if __name__ == "__main__":
    # Test with a simple 3x3 puzzle
    # 3x3 grid = 9 cells, 4x4 = 16 vertices
    # Layout:
    #   0-1-2-3   (vx)
    #   | | | |
    #   4-5-6-7
    #   | | | |
    #   8-9-A-B
    #   | | | |
    #   C-D-E-F

    print("Testing slants_board.py")
    print("=" * 40)

    # Simple test: all corners are 0 (no diagonals touch corners), center vertices 2
    # 0's at corners, 2's in center ring
    # Vertices: 0,0,0,0 / 0,2,2,0 / 0,2,2,0 / 0,0,0,0
    # Encoding: 0, 0, 0, 0, 0, 2, 2, 0, 0, 2, 2, 0, 0, 0, 0, 0
    # RLE: 000002200220000 but needs letters for runs
    # Better: hand-craft it

    width, height = 3, 3
    # 16 vertices, all unlabeled for simplicity
    givens = "p"  # p = 16 unlabeled vertices

    print(f"Testing with {width}x{height} grid")
    board = Board(width, height, givens)
    print(f"Board dimensions: {board.width}x{board.height}")
    print(f"Number of cells: {len(board.cells)}")
    print(f"Number of vertices: {len(board.vertices)}")
    print()
    print("Initial board:")
    print(board)
    print()

    # Test encoding round-trip
    encoded = board.encode_givens()
    print(f"Original givens: {givens}")
    print(f"Re-encoded:      {encoded}")
    print(f"Match: {givens == encoded}")

    # Test with clues
    print("\n" + "=" * 40)
    print("Testing with clues")
    # 8x8 puzzle from Simon Tatham's site (from SCRAPING.md)
    # https://www.chiark.greenend.org.uk/~sgtatham/puzzles/js/slant.html#8x8:c120a0b21h3a2114f3a2b2a4b2110a1a1b1c2132d1b1a33a1a1c0b
    width2, height2 = 8, 8
    givens2 = "c120a0b21h3a2114f3a2b2a4b2110a1a1b1c2132d1b1a33a1a1c0b"

    board2 = Board(width2, height2, givens2)
    print(f"Board dimensions: {board2.width}x{board2.height}")
    print(f"Number of cells: {len(board2.cells)}")
    print(f"Number of vertices: {len(board2.vertices)}")
    print()
    print("Board with clues:")
    print(board2)
    print()

    # Count clued vertices
    clued = board2.get_clued_vertices()
    print(f"Clued vertices: {len(clued)}")

    # Test vertex-cell relationships
    print("\n" + "=" * 40)
    print("Testing vertex-cell relationships")
    v = board2.get_vertex(1, 1)
    print(f"Vertex (1,1) clue: {v.clue}")
    adjacent = board2.get_adjacent_cells_for_vertex(v)
    print(f"Adjacent cells: {len(adjacent)}")
    for cell, slash_t, back_t in adjacent:
        print(f"  Cell ({cell.x},{cell.y}): slash_touches={slash_t}, backslash_touches={back_t}")

    # Test loop detection
    print("\n" + "=" * 40)
    print("Testing loop detection")
    test_board = Board(2, 2, "i")  # 2x2 grid, 9 vertices, all unlabeled
    print(f"2x2 board created")

    # Place diagonals that would form a loop if we complete the square
    cell00 = test_board.get_cell(0, 0)
    cell10 = test_board.get_cell(1, 0)
    cell01 = test_board.get_cell(0, 1)
    cell11 = test_board.get_cell(1, 1)

    # Create a path: place slashes and backslashes
    test_board.place_value(cell00, BACKSLASH)  # \ connects (0,0) to (1,1)
    test_board.place_value(cell10, SLASH)       # / connects (1,1) to (2,0)
    test_board.place_value(cell01, SLASH)       # / connects (0,2) to (1,1)

    print("After placing 3 diagonals:")
    print(test_board)

    # Now check if placing the last one would form a loop
    will_loop = test_board.would_form_loop(cell11, BACKSLASH)
    print(f"Would placing \\ at (1,1) form a loop? {will_loop}")
    will_loop2 = test_board.would_form_loop(cell11, SLASH)
    print(f"Would placing / at (1,1) form a loop? {will_loop2}")
