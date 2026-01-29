//! Board, Vertex, and Cell types for Slants (Gokigen Naname) puzzles.
//!
//! Grid Layout:
//! - Cells are in a width x height grid
//! - Vertices are at corners: (width+1) x (height+1) vertices
//! - Each cell contains either UNKNOWN (0), SLASH (1), or BACKSLASH (2)
//! - Each vertex may have a clue (0-4) indicating how many diagonals touch it

/// Cell value constants
pub const UNKNOWN: u8 = 0;
pub const SLASH: u8 = 1;     // /  - connects bottom-left to top-right
pub const BACKSLASH: u8 = 2; // \  - connects top-left to bottom-right

/// Represents a single cell in a Slants puzzle.
#[derive(Clone)]
pub struct Cell {
    pub x: usize,
    pub y: usize,
    pub value: u8,
}

impl Cell {
    pub fn new(x: usize, y: usize) -> Self {
        Cell { x, y, value: UNKNOWN }
    }
}

/// Represents a vertex (corner point) in a Slants puzzle.
#[derive(Clone)]
pub struct Vertex {
    pub vx: usize,
    pub vy: usize,
    pub clue: Option<u8>,
}

impl Vertex {
    pub fn new(vx: usize, vy: usize, clue: Option<u8>) -> Self {
        Vertex { vx, vy, clue }
    }
}

/// Board state that can be saved and restored for backtracking.
#[derive(Clone)]
pub struct BoardState {
    pub cell_values: Vec<u8>,
    pub parent: Vec<usize>,
    pub rank: Vec<usize>,
    pub equiv_parent: Vec<usize>,
    pub equiv_rank: Vec<usize>,
    pub slashval: Vec<u8>,
    pub vbitmap: Vec<u8>,
    pub exits: Vec<i32>,
    pub border: Vec<bool>,
}

/// Represents a Slants puzzle board.
pub struct Board {
    pub width: usize,
    pub height: usize,
    pub cells: Vec<Cell>,
    pub vertices: Vec<Vertex>,
    // Union-find for loop detection
    parent: Vec<usize>,
    rank: Vec<usize>,
    // Equivalence tracking
    equiv_parent: Vec<usize>,
    equiv_rank: Vec<usize>,
    slashval: Vec<u8>,
    // V-bitmap tracking
    vbitmap: Vec<u8>,
    // Exits and border tracking
    exits: Vec<i32>,
    border: Vec<bool>,
}

impl Board {
    /// Create a new board from dimensions and givens string.
    pub fn new(width: usize, height: usize, givens_string: &str) -> Result<Self, String> {
        // Initialize cells
        let mut cells = Vec::with_capacity(width * height);
        for y in 0..height {
            for x in 0..width {
                cells.push(Cell::new(x, y));
            }
        }

        // Decode givens
        let decoded_clues = decode_givens(givens_string);
        let expected_vertices = (width + 1) * (height + 1);

        if decoded_clues.len() != expected_vertices {
            return Err(format!(
                "Givens decode to {} vertices, expected {}",
                decoded_clues.len(),
                expected_vertices
            ));
        }

        // Initialize vertices
        let mut vertices = Vec::with_capacity(expected_vertices);
        for (i, clue) in decoded_clues.iter().enumerate() {
            let vx = i % (width + 1);
            let vy = i / (width + 1);
            vertices.push(Vertex::new(vx, vy, *clue));
        }

        // Initialize union-find for loop detection
        let num_vertices = (width + 1) * (height + 1);
        let parent: Vec<usize> = (0..num_vertices).collect();
        let rank = vec![0; num_vertices];

        // Initialize equivalence tracking
        let num_cells = width * height;
        let equiv_parent: Vec<usize> = (0..num_cells).collect();
        let equiv_rank = vec![0; num_cells];
        let slashval = vec![0; num_cells];

        // Initialize v-bitmap (all shapes initially possible = 0xF)
        let vbitmap = vec![0xF; num_cells];

        // Initialize exits and border
        let mut exits = vec![0i32; num_vertices];
        let mut border = vec![false; num_vertices];

        let vw = width + 1;
        let vh = height + 1;
        for vy in 0..vh {
            for vx in 0..vw {
                let idx = vy * vw + vx;
                // Border if on edge
                if vy == 0 || vy == vh - 1 || vx == 0 || vx == vw - 1 {
                    border[idx] = true;
                }
                // Exits = clue value or 4 if no clue
                if let Some(c) = decoded_clues[idx] {
                    exits[idx] = c as i32;
                } else {
                    exits[idx] = 4;
                }
            }
        }

        Ok(Board {
            width,
            height,
            cells,
            vertices,
            parent,
            rank,
            equiv_parent,
            equiv_rank,
            slashval,
            vbitmap,
            exits,
            border,
        })
    }

    /// Save current board state for backtracking.
    pub fn save_state(&self) -> BoardState {
        BoardState {
            cell_values: self.cells.iter().map(|c| c.value).collect(),
            parent: self.parent.clone(),
            rank: self.rank.clone(),
            equiv_parent: self.equiv_parent.clone(),
            equiv_rank: self.equiv_rank.clone(),
            slashval: self.slashval.clone(),
            vbitmap: self.vbitmap.clone(),
            exits: self.exits.clone(),
            border: self.border.clone(),
        }
    }

    /// Restore board state from a saved snapshot.
    pub fn restore_state(&mut self, state: &BoardState) {
        for (cell, &value) in self.cells.iter_mut().zip(state.cell_values.iter()) {
            cell.value = value;
        }
        self.parent = state.parent.clone();
        self.rank = state.rank.clone();
        self.equiv_parent = state.equiv_parent.clone();
        self.equiv_rank = state.equiv_rank.clone();
        self.slashval = state.slashval.clone();
        self.vbitmap = state.vbitmap.clone();
        self.exits = state.exits.clone();
        self.border = state.border.clone();
    }

    // Union-find operations for loop detection

    fn find(&mut self, x: usize) -> usize {
        if self.parent[x] != x {
            self.parent[x] = self.find(self.parent[x]);
        }
        self.parent[x]
    }

    fn union(&mut self, x: usize, y: usize) -> bool {
        let rx = self.find(x);
        let ry = self.find(y);
        if rx == ry {
            return false; // Already connected - would form loop
        }

        // Merge exits and border
        let merged_exits = self.exits[rx] + self.exits[ry] - 2;
        let merged_border = self.border[rx] || self.border[ry];

        let (rx, ry) = if self.rank[rx] < self.rank[ry] {
            (ry, rx)
        } else {
            (rx, ry)
        };

        self.parent[ry] = rx;
        if self.rank[rx] == self.rank[ry] {
            self.rank[rx] += 1;
        }

        self.exits[rx] = merged_exits;
        self.border[rx] = merged_border;

        true
    }

    fn vertex_index(&self, vx: usize, vy: usize) -> usize {
        vy * (self.width + 1) + vx
    }

    fn cell_index(&self, cell_x: usize, cell_y: usize) -> usize {
        cell_y * self.width + cell_x
    }

    // Equivalence tracking operations

    fn equiv_find(&mut self, x: usize) -> usize {
        if self.equiv_parent[x] != x {
            self.equiv_parent[x] = self.equiv_find(self.equiv_parent[x]);
        }
        self.equiv_parent[x]
    }

    /// Get the equivalence class root for a cell.
    pub fn get_cell_equiv_root(&mut self, cell_x: usize, cell_y: usize) -> usize {
        let idx = self.cell_index(cell_x, cell_y);
        self.equiv_find(idx)
    }

    /// Mark two cells as equivalent (must have same slash orientation).
    pub fn mark_cells_equivalent(&mut self, x1: usize, y1: usize, x2: usize, y2: usize) -> bool {
        let idx1 = self.cell_index(x1, y1);
        let idx2 = self.cell_index(x2, y2);

        let r1 = self.equiv_find(idx1);
        let r2 = self.equiv_find(idx2);

        if r1 == r2 {
            return false; // Already equivalent
        }

        // Check for slashval conflict
        let sv1 = self.slashval[r1];
        let sv2 = self.slashval[r2];
        if sv1 != 0 && sv2 != 0 && sv1 != sv2 {
            return false; // Conflict
        }

        let merged_sv = if sv1 != 0 { sv1 } else { sv2 };

        // Union by rank
        let (r1, r2) = if self.equiv_rank[r1] < self.equiv_rank[r2] {
            (r2, r1)
        } else {
            (r1, r2)
        };

        self.equiv_parent[r2] = r1;
        if self.equiv_rank[r1] == self.equiv_rank[r2] {
            self.equiv_rank[r1] += 1;
        }

        self.slashval[r1] = merged_sv;
        true
    }

    /// Get the known value for a cell's equivalence class.
    pub fn get_equivalence_class_value(&mut self, cell_x: usize, cell_y: usize) -> u8 {
        let idx = self.cell_index(cell_x, cell_y);
        let root = self.equiv_find(idx);
        self.slashval[root]
    }

    /// Get all cells in the same equivalence class as the given cell.
    pub fn get_equivalent_cells(&mut self, cell_x: usize, cell_y: usize) -> Vec<(usize, usize)> {
        let target_root = self.equiv_find(self.cell_index(cell_x, cell_y));
        let mut result = Vec::new();
        for y in 0..self.height {
            for x in 0..self.width {
                let idx = self.cell_index(x, y);
                if self.equiv_find(idx) == target_root {
                    result.push((x, y));
                }
            }
        }
        result
    }

    /// Set the slash value for a cell's equivalence class.
    pub fn set_equivalence_class_value(&mut self, cell_x: usize, cell_y: usize, value: u8) {
        let idx = self.cell_index(cell_x, cell_y);
        let root = self.equiv_find(idx);
        self.slashval[root] = value;
    }

    // V-bitmap operations

    /// Get the v-bitmap for a cell.
    pub fn vbitmap_get(&self, cell_x: usize, cell_y: usize) -> u8 {
        let idx = self.cell_index(cell_x, cell_y);
        self.vbitmap[idx]
    }

    /// Clear specified bits from a cell's v-bitmap.
    pub fn vbitmap_clear(&mut self, cell_x: usize, cell_y: usize, bits: u8) -> bool {
        let idx = self.cell_index(cell_x, cell_y);
        let old = self.vbitmap[idx];
        let new = old & !bits;
        if new != old {
            self.vbitmap[idx] = new;
            true
        } else {
            false
        }
    }

    // Vertex group operations

    /// Get the root of the vertex group.
    pub fn get_vertex_root(&mut self, vx: usize, vy: usize) -> usize {
        let idx = self.vertex_index(vx, vy);
        self.find(idx)
    }

    /// Get exits for vertex group.
    pub fn get_vertex_group_exits(&mut self, vx: usize, vy: usize) -> i32 {
        let root = self.get_vertex_root(vx, vy);
        self.exits[root]
    }

    /// Check if vertex group includes a border vertex.
    pub fn get_vertex_group_border(&mut self, vx: usize, vy: usize) -> bool {
        let root = self.get_vertex_root(vx, vy);
        self.border[root]
    }

    fn decr_exits(&mut self, vx: usize, vy: usize) {
        let vertex_idx = self.vertex_index(vx, vy);
        if self.vertices[vertex_idx].clue.is_some() {
            return; // Clued vertices don't decrement
        }
        let root = self.find(vertex_idx);
        self.exits[root] -= 1;
    }

    // Cell and vertex access

    /// Get cell at position. Returns None if out of bounds.
    pub fn get_cell(&self, x: usize, y: usize) -> Option<&Cell> {
        if x < self.width && y < self.height {
            Some(&self.cells[y * self.width + x])
        } else {
            None
        }
    }

    /// Get cell value at position.
    pub fn get_cell_value(&self, x: usize, y: usize) -> u8 {
        self.cells[y * self.width + x].value
    }

    /// Get vertex at position. Returns None if out of bounds.
    pub fn get_vertex(&self, vx: usize, vy: usize) -> Option<&Vertex> {
        if vx <= self.width && vy <= self.height {
            Some(&self.vertices[vy * (self.width + 1) + vx])
        } else {
            None
        }
    }

    /// Get vertex clue at position.
    pub fn get_vertex_clue(&self, vx: usize, vy: usize) -> Option<u8> {
        self.vertices[vy * (self.width + 1) + vx].clue
    }

    /// Count touches and unknowns for a vertex.
    /// Returns (current_touches, unknown_count).
    pub fn count_touches(&self, vx: usize, vy: usize) -> (u8, u8) {
        let mut current = 0u8;
        let mut unknown = 0u8;

        // Check adjacent cells
        // Top-left cell (vertex is its bottom-right corner) - backslash touches
        if vx > 0 && vy > 0 {
            let val = self.get_cell_value(vx - 1, vy - 1);
            if val == UNKNOWN {
                unknown += 1;
            } else if val == BACKSLASH {
                current += 1;
            }
        }

        // Top-right cell (vertex is its bottom-left corner) - slash touches
        if vx < self.width && vy > 0 {
            let val = self.get_cell_value(vx, vy - 1);
            if val == UNKNOWN {
                unknown += 1;
            } else if val == SLASH {
                current += 1;
            }
        }

        // Bottom-left cell (vertex is its top-right corner) - slash touches
        if vx > 0 && vy < self.height {
            let val = self.get_cell_value(vx - 1, vy);
            if val == UNKNOWN {
                unknown += 1;
            } else if val == SLASH {
                current += 1;
            }
        }

        // Bottom-right cell (vertex is its top-left corner) - backslash touches
        if vx < self.width && vy < self.height {
            let val = self.get_cell_value(vx, vy);
            if val == UNKNOWN {
                unknown += 1;
            } else if val == BACKSLASH {
                current += 1;
            }
        }

        (current, unknown)
    }

    /// Check if placing a value would form a loop.
    pub fn would_form_loop(&mut self, cell_x: usize, cell_y: usize, value: u8) -> bool {
        let (v1, v2) = if value == SLASH {
            // Connects bottom-left to top-right
            (
                self.vertex_index(cell_x, cell_y + 1),
                self.vertex_index(cell_x + 1, cell_y),
            )
        } else {
            // Connects top-left to bottom-right
            (
                self.vertex_index(cell_x, cell_y),
                self.vertex_index(cell_x + 1, cell_y + 1),
            )
        };

        self.find(v1) == self.find(v2)
    }

    /// Place a value in a cell and update union-find.
    pub fn place_value(&mut self, cell_x: usize, cell_y: usize, value: u8) -> Result<bool, String> {
        let cell_idx = self.cell_index(cell_x, cell_y);
        if self.cells[cell_idx].value != UNKNOWN {
            return Ok(false);
        }

        let (v1, v2, non_v1, non_v2) = if value == SLASH {
            // Connects bottom-left to top-right
            (
                self.vertex_index(cell_x, cell_y + 1),
                self.vertex_index(cell_x + 1, cell_y),
                (cell_x, cell_y),           // top-left
                (cell_x + 1, cell_y + 1),   // bottom-right
            )
        } else {
            // Connects top-left to bottom-right
            (
                self.vertex_index(cell_x, cell_y),
                self.vertex_index(cell_x + 1, cell_y + 1),
                (cell_x + 1, cell_y),       // top-right
                (cell_x, cell_y + 1),       // bottom-left
            )
        };

        if !self.union(v1, v2) {
            return Err(format!(
                "Placing {} at ({},{}) would form a loop",
                if value == SLASH { "/" } else { "\\" },
                cell_x,
                cell_y
            ));
        }

        // Decrement exits for non-connected vertices
        self.decr_exits(non_v1.0, non_v1.1);
        self.decr_exits(non_v2.0, non_v2.1);

        self.cells[cell_idx].value = value;

        // Update slashval for equivalence class
        self.set_equivalence_class_value(cell_x, cell_y, value);

        Ok(true)
    }

    /// Get all clued vertices.
    pub fn get_clued_vertices(&self) -> Vec<(usize, usize, u8)> {
        self.vertices
            .iter()
            .filter_map(|v| v.clue.map(|c| (v.vx, v.vy, c)))
            .collect()
    }

    /// Get all unknown cells.
    pub fn get_unknown_cells(&self) -> Vec<(usize, usize)> {
        self.cells
            .iter()
            .filter(|c| c.value == UNKNOWN)
            .map(|c| (c.x, c.y))
            .collect()
    }

    /// Check if all cells have values.
    pub fn is_solved(&self) -> bool {
        self.cells.iter().all(|c| c.value != UNKNOWN)
    }

    /// Check if current state is valid (no clue exceeded).
    pub fn is_valid(&self) -> bool {
        for v in &self.vertices {
            if let Some(clue) = v.clue {
                let (current, _) = self.count_touches(v.vx, v.vy);
                if current > clue {
                    return false;
                }
            }
        }
        true
    }

    /// Check if board is a valid complete solution.
    pub fn is_valid_solution(&self) -> bool {
        if !self.is_solved() {
            return false;
        }
        for v in &self.vertices {
            if let Some(clue) = v.clue {
                let (current, _) = self.count_touches(v.vx, v.vy);
                if current != clue {
                    return false;
                }
            }
        }
        true
    }

    /// Check if all placed cells match the known solution.
    /// Returns false if any placed cell contradicts the solution.
    pub fn check_against_solution(&self, known_solution: &str) -> bool {
        let sol_bytes = known_solution.as_bytes();
        for (i, cell) in self.cells.iter().enumerate() {
            if cell.value == UNKNOWN {
                continue;
            }
            if i >= sol_bytes.len() {
                return false;
            }
            let expected = match sol_bytes[i] {
                b'/' => SLASH,
                b'\\' => BACKSLASH,
                _ => continue,
            };
            if cell.value != expected {
                return false;
            }
        }
        true
    }

    /// Convert board to solution string.
    pub fn to_solution_string(&self) -> String {
        self.cells
            .iter()
            .map(|c| match c.value {
                SLASH => '/',
                BACKSLASH => '\\',
                _ => '.',
            })
            .collect()
    }
}

/// Decode RLE-encoded givens string.
fn decode_givens(givens_string: &str) -> Vec<Option<u8>> {
    let mut result = Vec::new();
    for c in givens_string.chars() {
        if c.is_ascii_digit() {
            result.push(Some(c.to_digit(10).unwrap() as u8));
        } else if c.is_ascii_lowercase() {
            let run_length = (c as u8 - b'a' + 1) as usize;
            result.extend(std::iter::repeat(None).take(run_length));
        }
    }
    result
}

/// Parse a puzzle line from testsuite file.
pub fn parse_puzzle_line(line: &str) -> Option<Puzzle> {
    let line = line.trim();
    if line.is_empty() || line.starts_with('#') || line.starts_with(';') {
        return None;
    }

    let parts: Vec<&str> = line.split('\t').collect();
    if parts.len() < 4 {
        return None;
    }

    Some(Puzzle {
        name: parts[0].to_string(),
        width: parts[1].parse().ok()?,
        height: parts[2].parse().ok()?,
        givens: parts[3].to_string(),
        answer: if parts.len() > 4 { Some(parts[4].to_string()) } else { None },
        comment: if parts.len() > 5 { Some(parts[5].to_string()) } else { None },
    })
}

/// Puzzle data from testsuite.
#[derive(Clone)]
pub struct Puzzle {
    pub name: String,
    pub width: usize,
    pub height: usize,
    pub givens: String,
    pub answer: Option<String>,
    pub comment: Option<String>,
}

/// Result of solving a puzzle.
pub struct SolveResult {
    pub status: String,          // "solved", "unsolved", or "mult"
    pub solution: String,        // Solution string
    pub work_score: u32,         // Total work score
    pub max_tier_used: u8,       // Maximum tier used
}
