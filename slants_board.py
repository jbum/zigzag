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
        if self._rank[rx] < self._rank[ry]:
            rx, ry = ry, rx
        self._parent[ry] = rx
        if self._rank[rx] == self._rank[ry]:
            self._rank[rx] += 1
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
            v1 = self._vertex_index(x, y + 1)
            v2 = self._vertex_index(x + 1, y)
        else:  # BACKSLASH
            v1 = self._vertex_index(x, y)
            v2 = self._vertex_index(x + 1, y + 1)

        # Union the vertices
        if not self._union(v1, v2):
            raise ValueError(f"Placing {value} at ({x},{y}) would form a loop")

        cell.set_value(value)
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
            self._rank.copy()
        )

    def restore_state(self, state):
        """Restore board from a saved state snapshot."""
        cell_values, parent, rank = state
        for cell, value in zip(self.cells, cell_values):
            cell.value = value
        self._parent = parent.copy()
        self._rank = rank.copy()

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
