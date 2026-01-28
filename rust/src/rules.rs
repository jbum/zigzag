//! Production rules for Slants (Gokigen Naname) puzzle solver.
//!
//! Each rule function takes a Board and returns true if it made progress.

use crate::board::{Board, UNKNOWN, SLASH, BACKSLASH};

/// Rule info: (name, work_score, tier)
pub struct RuleInfo {
    pub name: &'static str,
    pub score: u32,
    pub tier: u8,
}

/// Get the list of rules used by PR solver.
pub fn get_pr_rules() -> Vec<(RuleInfo, fn(&mut Board) -> bool)> {
    vec![
        (RuleInfo { name: "clue_finish_b", score: 1, tier: 1 }, rule_clue_finish_b),
        (RuleInfo { name: "clue_finish_a", score: 2, tier: 1 }, rule_clue_finish_a),
        (RuleInfo { name: "no_loops", score: 2, tier: 1 }, rule_no_loops),
        (RuleInfo { name: "edge_clue_constraints", score: 2, tier: 2 }, rule_edge_clue_constraints),
        (RuleInfo { name: "border_two_v_shape", score: 3, tier: 2 }, rule_border_two_v_shape),
        (RuleInfo { name: "loop_avoidance_2", score: 5, tier: 2 }, rule_loop_avoidance_2),
        (RuleInfo { name: "v_pattern_with_three", score: 6, tier: 2 }, rule_v_pattern_with_three),
        (RuleInfo { name: "adjacent_ones", score: 8, tier: 2 }, rule_adjacent_ones),
        (RuleInfo { name: "adjacent_threes", score: 8, tier: 2 }, rule_adjacent_threes),
        (RuleInfo { name: "dead_end_avoidance", score: 9, tier: 2 }, rule_dead_end_avoidance),
        (RuleInfo { name: "equivalence_classes", score: 9, tier: 2 }, rule_equivalence_classes),
        (RuleInfo { name: "vbitmap_propagation", score: 9, tier: 2 }, rule_vbitmap_propagation),
        (RuleInfo { name: "simon_unified", score: 9, tier: 2 }, rule_simon_unified),
        (RuleInfo { name: "trial_clue_violation", score: 10, tier: 3 }, rule_trial_clue_violation),
        (RuleInfo { name: "one_step_lookahead", score: 15, tier: 3 }, rule_one_step_lookahead),
    ]
}

/// Get the list of rules used by BF solver (excludes tier 3 rules).
pub fn get_bf_rules() -> Vec<(RuleInfo, fn(&mut Board) -> bool)> {
    vec![
        (RuleInfo { name: "clue_finish_b", score: 1, tier: 1 }, rule_clue_finish_b),
        (RuleInfo { name: "clue_finish_a", score: 2, tier: 1 }, rule_clue_finish_a),
        (RuleInfo { name: "no_loops", score: 2, tier: 1 }, rule_no_loops),
        (RuleInfo { name: "edge_clue_constraints", score: 2, tier: 2 }, rule_edge_clue_constraints),
        (RuleInfo { name: "border_two_v_shape", score: 3, tier: 2 }, rule_border_two_v_shape),
        (RuleInfo { name: "loop_avoidance_2", score: 5, tier: 1 }, rule_loop_avoidance_2),
        (RuleInfo { name: "v_pattern_with_three", score: 6, tier: 2 }, rule_v_pattern_with_three),
        (RuleInfo { name: "adjacent_ones", score: 8, tier: 2 }, rule_adjacent_ones),
        (RuleInfo { name: "adjacent_threes", score: 8, tier: 2 }, rule_adjacent_threes),
        (RuleInfo { name: "dead_end_avoidance", score: 9, tier: 2 }, rule_dead_end_avoidance),
        (RuleInfo { name: "equivalence_classes", score: 9, tier: 2 }, rule_equivalence_classes),
        (RuleInfo { name: "vbitmap_propagation", score: 9, tier: 2 }, rule_vbitmap_propagation),
        (RuleInfo { name: "simon_unified", score: 9, tier: 2 }, rule_simon_unified),
    ]
}

/// If a clue has enough touches, fill remaining with avoiders.
pub fn rule_clue_finish_b(board: &mut Board) -> bool {
    let mut made_progress = false;
    let clued = board.get_clued_vertices();

    for (vx, vy, clue) in clued {
        let (current_touches, _) = board.count_touches(vx, vy);

        if current_touches != clue {
            continue;
        }

        // All remaining must avoid
        let unknown_cells = get_adjacent_unknown_cells(board, vx, vy);
        for (cx, cy, slash_touches, _) in unknown_cells {
            // Place the non-touching diagonal
            let value = if slash_touches { BACKSLASH } else { SLASH };
            if !board.would_form_loop(cx, cy, value) {
                if board.place_value(cx, cy, value).is_ok() {
                    made_progress = true;
                }
            }
        }
    }

    made_progress
}

/// If a clue needs all remaining unknowns to touch, fill them in.
pub fn rule_clue_finish_a(board: &mut Board) -> bool {
    let mut made_progress = false;
    let clued = board.get_clued_vertices();

    for (vx, vy, clue) in clued {
        let (current_touches, _) = board.count_touches(vx, vy);
        let needed = clue.saturating_sub(current_touches);

        if needed == 0 {
            continue;
        }

        let unknown_cells = get_adjacent_unknown_cells(board, vx, vy);

        // If all unknowns must touch to reach the clue
        if needed as usize == unknown_cells.len() && !unknown_cells.is_empty() {
            for (cx, cy, slash_touches, _) in unknown_cells {
                let value = if slash_touches { SLASH } else { BACKSLASH };
                if !board.would_form_loop(cx, cy, value) {
                    if board.place_value(cx, cy, value).is_ok() {
                        made_progress = true;
                    }
                }
            }
        }
    }

    made_progress
}

/// If one diagonal would form a loop, place the other.
pub fn rule_no_loops(board: &mut Board) -> bool {
    let mut made_progress = false;
    let unknown = board.get_unknown_cells();

    for (cx, cy) in unknown {
        let slash_loops = board.would_form_loop(cx, cy, SLASH);
        let backslash_loops = board.would_form_loop(cx, cy, BACKSLASH);

        if slash_loops && !backslash_loops {
            if board.place_value(cx, cy, BACKSLASH).is_ok() {
                made_progress = true;
            }
        } else if backslash_loops && !slash_loops {
            if board.place_value(cx, cy, SLASH).is_ok() {
                made_progress = true;
            }
        }
    }

    made_progress
}

/// Edge/corner vertices with max clue must have all adjacent touch.
pub fn rule_edge_clue_constraints(board: &mut Board) -> bool {
    let mut made_progress = false;
    let clued = board.get_clued_vertices();

    for (vx, vy, clue) in clued {
        let adjacent = get_adjacent_unknown_cells(board, vx, vy);
        let max_possible = count_adjacent_cells(board, vx, vy);

        if clue as usize == max_possible {
            for (cx, cy, slash_touches, _) in adjacent {
                let value = if slash_touches { SLASH } else { BACKSLASH };
                if !board.would_form_loop(cx, cy, value) {
                    if board.place_value(cx, cy, value).is_ok() {
                        made_progress = true;
                    }
                }
            }
        }
    }

    made_progress
}

/// A 2 on the border creates a V-shape pattern.
pub fn rule_border_two_v_shape(board: &mut Board) -> bool {
    let mut made_progress = false;
    let clued = board.get_clued_vertices();

    for (vx, vy, clue) in clued {
        if clue != 2 {
            continue;
        }

        let adjacent = get_adjacent_unknown_cells(board, vx, vy);
        let max_possible = count_adjacent_cells(board, vx, vy);

        // Check if on edge (exactly 2 adjacent cells)
        if max_possible != 2 {
            continue;
        }

        // Both must touch
        let (current, unknown) = board.count_touches(vx, vy);
        if current as usize + unknown as usize == 2 && unknown > 0 {
            for (cx, cy, slash_touches, _) in adjacent {
                let value = if slash_touches { SLASH } else { BACKSLASH };
                if !board.would_form_loop(cx, cy, value) {
                    if board.place_value(cx, cy, value).is_ok() {
                        made_progress = true;
                    }
                }
            }
        }
    }

    made_progress
}

/// Loop avoidance for clue 2 with 2 unknowns.
pub fn rule_loop_avoidance_2(_board: &mut Board) -> bool {
    // This rule checks if completing a 2 with both touches would form a loop
    // If so, we need different logic - but for now this is a placeholder
    false
}

/// V-shaped pattern detection with 3 clue.
pub fn rule_v_pattern_with_three(board: &mut Board) -> bool {
    let mut made_progress = false;
    let h = board.height;
    let w = board.width;

    for y in 0..h {
        for x in 0..(w.saturating_sub(1)) {
            let val_left = board.get_cell_value(x, y);
            let val_right = board.get_cell_value(x + 1, y);

            // Check for \/ pattern (V pointing down)
            if val_left == BACKSLASH && val_right == SLASH {
                // V points down, meeting at vertex (x+1, y+1)
                // Check for 3 above at (x+1, y)
                if let Some(3) = board.get_vertex_clue(x + 1, y) {
                    let (current, unknown) = board.count_touches(x + 1, y);
                    if current == 2 && unknown > 0 {
                        // Fill remaining from above
                        for (cx, cy, slash_t, _) in get_adjacent_unknown_cells(board, x + 1, y) {
                            if cy < y {
                                let value = if slash_t { SLASH } else { BACKSLASH };
                                if !board.would_form_loop(cx, cy, value) {
                                    if board.place_value(cx, cy, value).is_ok() {
                                        made_progress = true;
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // Check for /\ pattern (V pointing up)
            if val_left == SLASH && val_right == BACKSLASH {
                // V points up, meeting at vertex (x+1, y)
                // Check for 3 below at (x+1, y+1)
                if let Some(3) = board.get_vertex_clue(x + 1, y + 1) {
                    let (current, unknown) = board.count_touches(x + 1, y + 1);
                    if current == 2 && unknown > 0 {
                        // Fill remaining from below
                        for (cx, cy, slash_t, _) in get_adjacent_unknown_cells(board, x + 1, y + 1) {
                            if cy > y {
                                let value = if slash_t { SLASH } else { BACKSLASH };
                                if !board.would_form_loop(cx, cy, value) {
                                    if board.place_value(cx, cy, value).is_ok() {
                                        made_progress = true;
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    made_progress
}

/// Adjacent 1-1 pattern constraints.
pub fn rule_adjacent_ones(board: &mut Board) -> bool {
    let mut made_progress = false;
    let clued = board.get_clued_vertices();

    for (vx, vy, clue) in &clued {
        if *clue != 1 {
            continue;
        }

        let (current, _) = board.count_touches(*vx, *vy);
        if current != 1 {
            continue;
        }

        // This 1 is satisfied - check adjacent 1s
        for (dx, dy) in &[(1i32, 0i32), (-1, 0), (0, 1), (0, -1)] {
            let nvx = (*vx as i32 + dx) as usize;
            let nvy = (*vy as i32 + dy) as usize;

            if nvx > board.width || nvy > board.height {
                continue;
            }

            if let Some(1) = board.get_vertex_clue(nvx, nvy) {
                // Find shared cells and mark them to avoid this vertex
                for (cx, cy, slash_t, _) in get_adjacent_unknown_cells(board, *vx, *vy) {
                    // Check if this cell is also adjacent to neighbor
                    let neighbor_adj = get_adjacent_cells_coords(board, nvx, nvy);
                    if neighbor_adj.iter().any(|(nx, ny, _, _)| *nx == cx && *ny == cy) {
                        let value = if slash_t { BACKSLASH } else { SLASH };
                        if !board.would_form_loop(cx, cy, value) {
                            if board.place_value(cx, cy, value).is_ok() {
                                made_progress = true;
                            }
                        }
                    }
                }
            }
        }
    }

    made_progress
}

/// Adjacent 3-3 pattern constraints.
pub fn rule_adjacent_threes(_board: &mut Board) -> bool {
    // Similar logic to adjacent_ones but for 3s
    false
}

/// Dead-end avoidance using exits/border tracking.
pub fn rule_dead_end_avoidance(board: &mut Board) -> bool {
    let mut made_progress = false;
    let unknown = board.get_unknown_cells();

    for (cx, cy) in unknown {
        let mut slash_forbidden = false;
        let mut back_forbidden = false;

        // Check BACKSLASH: connects (cx, cy) to (cx+1, cy+1)
        let tl_exits = board.get_vertex_group_exits(cx, cy);
        let br_exits = board.get_vertex_group_exits(cx + 1, cy + 1);
        let tl_border = board.get_vertex_group_border(cx, cy);
        let br_border = board.get_vertex_group_border(cx + 1, cy + 1);

        if !tl_border && !br_border && tl_exits <= 1 && br_exits <= 1 {
            back_forbidden = true;
        }

        // Check SLASH: connects (cx+1, cy) to (cx, cy+1)
        let tr_exits = board.get_vertex_group_exits(cx + 1, cy);
        let bl_exits = board.get_vertex_group_exits(cx, cy + 1);
        let tr_border = board.get_vertex_group_border(cx + 1, cy);
        let bl_border = board.get_vertex_group_border(cx, cy + 1);

        if !tr_border && !bl_border && tr_exits <= 1 && bl_exits <= 1 {
            slash_forbidden = true;
        }

        if back_forbidden && !slash_forbidden {
            if !board.would_form_loop(cx, cy, SLASH) {
                if board.place_value(cx, cy, SLASH).is_ok() {
                    made_progress = true;
                }
            }
        } else if slash_forbidden && !back_forbidden {
            if !board.would_form_loop(cx, cy, BACKSLASH) {
                if board.place_value(cx, cy, BACKSLASH).is_ok() {
                    made_progress = true;
                }
            }
        }
    }

    made_progress
}

/// Equivalence class tracking and propagation.
pub fn rule_equivalence_classes(board: &mut Board) -> bool {
    let mut made_progress = false;
    let clued = board.get_clued_vertices();

    // First: establish equivalences from clues
    for (vx, vy, clue) in &clued {
        let (current_touches, _) = board.count_touches(*vx, *vy);
        let needed = clue.saturating_sub(current_touches);

        if needed != 1 {
            continue;
        }

        let unknown_cells = get_adjacent_unknown_cells(board, *vx, *vy);
        if unknown_cells.len() != 2 {
            continue;
        }

        let (x1, y1, _, _) = unknown_cells[0];
        let (x2, y2, _, _) = unknown_cells[1];

        // Check if adjacent
        let dx = (x1 as i32 - x2 as i32).unsigned_abs() as usize;
        let dy = (y1 as i32 - y2 as i32).unsigned_abs() as usize;
        let are_adjacent = (dx == 1 && dy == 0) || (dx == 0 && dy == 1);

        if are_adjacent {
            if board.mark_cells_equivalent(x1, y1, x2, y2) {
                made_progress = true;
            }
        }
    }

    // Second: propagate known values
    let unknown = board.get_unknown_cells();
    for (cx, cy) in unknown {
        let equiv_value = board.get_equivalence_class_value(cx, cy);
        if equiv_value != UNKNOWN {
            if !board.would_form_loop(cx, cy, equiv_value) {
                if board.place_value(cx, cy, equiv_value).is_ok() {
                    made_progress = true;
                }
            } else {
                // Would form a loop - try the other value
                let other_value = if equiv_value == SLASH { BACKSLASH } else { SLASH };
                if !board.would_form_loop(cx, cy, other_value) {
                    if board.place_value(cx, cy, other_value).is_ok() {
                        made_progress = true;
                    }
                }
            }
        }
    }

    // Third: check if one diagonal would force a loop in an equivalent cell
    let unknown = board.get_unknown_cells();
    for (cx, cy) in unknown {
        let equiv_cells: Vec<(usize, usize)> = board.get_equivalent_cells(cx, cy)
            .into_iter()
            .filter(|&(ex, ey)| (ex != cx || ey != cy) && board.get_cell_value(ex, ey) == UNKNOWN)
            .collect();

        if equiv_cells.is_empty() {
            continue;
        }

        // Check if SLASH would force any equivalent cell into a loop
        let slash_forbidden = equiv_cells.iter().any(|&(ex, ey)| board.would_form_loop(ex, ey, SLASH));
        let back_forbidden = equiv_cells.iter().any(|&(ex, ey)| board.would_form_loop(ex, ey, BACKSLASH));

        if slash_forbidden && !back_forbidden {
            if !board.would_form_loop(cx, cy, BACKSLASH) {
                if board.place_value(cx, cy, BACKSLASH).is_ok() {
                    made_progress = true;
                }
            }
        } else if back_forbidden && !slash_forbidden {
            if !board.would_form_loop(cx, cy, SLASH) {
                if board.place_value(cx, cy, SLASH).is_ok() {
                    made_progress = true;
                }
            }
        }
    }

    made_progress
}

/// V-bitmap propagation.
/// Creates a local vbitmap and iterates until convergence.
pub fn rule_vbitmap_propagation(board: &mut Board) -> bool {
    let mut made_progress = false;
    let h = board.height;
    let w = board.width;

    // Initialize local vbitmap - all shapes initially possible
    let mut vbitmap: Vec<Vec<u8>> = vec![vec![0xF; w]; h];

    // Iterate until convergence
    let mut changed = true;
    while changed {
        changed = false;

        // Apply constraints from known cell values
        for y in 0..h {
            for x in 0..w {
                let s = board.get_cell_value(x, y);
                if s == UNKNOWN {
                    continue;
                }

                let old = vbitmap[y][x];
                if s == SLASH {
                    vbitmap[y][x] &= !0x5; // Can't do \/ or >
                    if x > 0 && (vbitmap[y][x - 1] & 0x2) != 0 {
                        vbitmap[y][x - 1] &= !0x2;
                        changed = true;
                    }
                    if y > 0 && (vbitmap[y - 1][x] & 0x8) != 0 {
                        vbitmap[y - 1][x] &= !0x8;
                        changed = true;
                    }
                } else {
                    vbitmap[y][x] &= !0xA; // Can't do /\ or <
                    if x > 0 && (vbitmap[y][x - 1] & 0x1) != 0 {
                        vbitmap[y][x - 1] &= !0x1;
                        changed = true;
                    }
                    if y > 0 && (vbitmap[y - 1][x] & 0x4) != 0 {
                        vbitmap[y - 1][x] &= !0x4;
                        changed = true;
                    }
                }
                if vbitmap[y][x] != old {
                    changed = true;
                }
            }
        }

        // Apply constraints from clue values (interior vertices only)
        for vy in 1..h {
            for vx in 1..w {
                let clue = match board.get_vertex_clue(vx, vy) {
                    Some(c) => c,
                    None => continue,
                };

                if clue == 1 {
                    // 1 clue: no v-shape pointing AT it
                    let old1 = vbitmap[vy - 1][vx - 1];
                    let old2 = vbitmap[vy][vx - 1];
                    let old3 = vbitmap[vy - 1][vx];
                    vbitmap[vy - 1][vx - 1] &= !0x5;
                    vbitmap[vy][vx - 1] &= !0x2;
                    vbitmap[vy - 1][vx] &= !0x8;
                    if vbitmap[vy - 1][vx - 1] != old1 || vbitmap[vy][vx - 1] != old2 || vbitmap[vy - 1][vx] != old3 {
                        changed = true;
                    }
                } else if clue == 3 {
                    // 3 clue: no v-shape pointing AWAY from it
                    let old1 = vbitmap[vy - 1][vx - 1];
                    let old2 = vbitmap[vy][vx - 1];
                    let old3 = vbitmap[vy - 1][vx];
                    vbitmap[vy - 1][vx - 1] &= !0xA;
                    vbitmap[vy][vx - 1] &= !0x1;
                    vbitmap[vy - 1][vx] &= !0x4;
                    if vbitmap[vy - 1][vx - 1] != old1 || vbitmap[vy][vx - 1] != old2 || vbitmap[vy - 1][vx] != old3 {
                        changed = true;
                    }
                } else if clue == 2 {
                    // 2 clue: propagate restrictions across
                    let old_tl = vbitmap[vy - 1][vx - 1];
                    let old_bl = vbitmap[vy][vx - 1];
                    let old_tr = vbitmap[vy - 1][vx];

                    // Horizontal: between top pair and bottom pair
                    let top = vbitmap[vy - 1][vx - 1] & 0x3;
                    let bot = vbitmap[vy][vx - 1] & 0x3;
                    vbitmap[vy - 1][vx - 1] &= !(0x3 ^ bot);
                    vbitmap[vy][vx - 1] &= !(0x3 ^ top);

                    // Vertical: between left pair and right pair
                    let left = vbitmap[vy - 1][vx - 1] & 0xC;
                    let right = vbitmap[vy - 1][vx] & 0xC;
                    vbitmap[vy - 1][vx - 1] &= !(0xC ^ right);
                    vbitmap[vy - 1][vx] &= !(0xC ^ left);

                    if vbitmap[vy - 1][vx - 1] != old_tl || vbitmap[vy][vx - 1] != old_bl || vbitmap[vy - 1][vx] != old_tr {
                        changed = true;
                    }
                }
            }
        }

        // When both v-shapes are ruled out between adjacent cells, mark them as equivalent
        for y in 0..h {
            for x in 0..w {
                // Check horizontal neighbor
                if x + 1 < w && (vbitmap[y][x] & 0x3) == 0 {
                    if board.mark_cells_equivalent(x, y, x + 1, y) {
                        made_progress = true;
                        changed = true;
                    }
                }

                // Check vertical neighbor
                if y + 1 < h && (vbitmap[y][x] & 0xC) == 0 {
                    if board.mark_cells_equivalent(x, y, x, y + 1) {
                        made_progress = true;
                        changed = true;
                    }
                }
            }
        }
    }

    made_progress
}

/// Unified rule mimicking Simon Tatham's solver.
/// This implements clue completion with adjacent equivalent pair tracking,
/// loop avoidance, dead-end avoidance, and equivalence-based filling.
pub fn rule_simon_unified(board: &mut Board) -> bool {
    let mut made_progress = false;
    let h = board.height;
    let w = board.width;
    let vh = h + 1;
    let vw = w + 1;

    let mut done_something = true;
    while done_something {
        done_something = false;

        // =================================================================
        // PHASE 1: Clue completion with adjacent equivalent pair tracking
        // =================================================================
        for vy in 0..vh {
            for vx in 0..vw {
                let clue = match board.get_vertex_clue(vx, vy) {
                    Some(c) => c,
                    None => continue,
                };

                // Build list of neighbors with their slash relationship
                // (cell_x, cell_y, slash_type that touches this vertex)
                let mut neighbours: Vec<(usize, usize, u8)> = Vec::new();
                if vx > 0 && vy > 0 {
                    neighbours.push((vx - 1, vy - 1, BACKSLASH)); // \ touches BR corner
                }
                if vx > 0 && vy < h {
                    neighbours.push((vx - 1, vy, SLASH)); // / touches TR corner
                }
                if vx < w && vy < h {
                    neighbours.push((vx, vy, BACKSLASH)); // \ touches TL corner
                }
                if vx < w && vy > 0 {
                    neighbours.push((vx, vy - 1, SLASH)); // / touches BL corner
                }

                if neighbours.is_empty() {
                    continue;
                }

                let nneighbours = neighbours.len();

                // Count undecided (nu) and lines still needed (nl)
                // Also track adjacent equivalent pairs
                let mut nu: i32 = 0;
                let mut nl: i32 = clue as i32;

                // Get equiv class of last cell (wrapping around)
                let (last_cx, last_cy, _) = neighbours[nneighbours - 1];
                let mut last_eq: i32 = if board.get_cell_value(last_cx, last_cy) == UNKNOWN {
                    board.get_cell_equiv_root(last_cx, last_cy) as i32
                } else {
                    -1
                };

                // Track equivalent pair
                let mut meq: i32 = -1;
                let mut mj1: Option<(usize, usize)> = None;
                let mut mj2: Option<(usize, usize)> = None;

                let mut last_cell = (last_cx, last_cy);

                for i in 0..nneighbours {
                    let (cx, cy, slash_type) = neighbours[i];
                    let cell_value = board.get_cell_value(cx, cy);

                    if cell_value == UNKNOWN {
                        nu += 1;
                        if meq < 0 {
                            let eq = board.get_cell_equiv_root(cx, cy) as i32;
                            if eq == last_eq && last_cell != (cx, cy) {
                                // Found adjacent equivalent pair!
                                meq = eq;
                                mj1 = Some(last_cell);
                                mj2 = Some((cx, cy));
                                nl -= 1; // Count as one line
                                nu -= 2; // Remove both from undecided
                            } else {
                                last_eq = eq;
                            }
                        }
                    } else {
                        last_eq = -1;
                        if cell_value == slash_type {
                            nl -= 1; // This cell provides a line
                        }
                    }
                    last_cell = (cx, cy);
                }

                // Check if impossible
                if nl < 0 || nl > nu {
                    continue;
                }

                // If we can fill remaining cells
                if nu > 0 && (nl == 0 || nl == nu) {
                    for &(cx, cy, slash_type) in &neighbours {
                        // Skip cells in equivalent pair
                        if Some((cx, cy)) == mj1 || Some((cx, cy)) == mj2 {
                            continue;
                        }
                        if board.get_cell_value(cx, cy) == UNKNOWN {
                            let value = if nl > 0 {
                                slash_type
                            } else {
                                if slash_type == SLASH { BACKSLASH } else { SLASH }
                            };

                            if !board.would_form_loop(cx, cy, value) {
                                if board.place_value(cx, cy, value).is_ok() {
                                    done_something = true;
                                    made_progress = true;
                                }
                            }
                        }
                    }
                }
                // If exactly 2 undecided and need 1 line, and they're adjacent,
                // mark them as equivalent
                else if nu == 2 && nl == 1 {
                    let mut last_idx: i32 = -1;
                    for i in 0..nneighbours {
                        let (cx, cy, _) = neighbours[i];
                        if board.get_cell_value(cx, cy) == UNKNOWN
                            && Some((cx, cy)) != mj1 && Some((cx, cy)) != mj2
                        {
                            if last_idx < 0 {
                                last_idx = i as i32;
                            } else if last_idx == (i as i32) - 1
                                || (last_idx == 0 && i == nneighbours - 1)
                            {
                                // Adjacent! Mark them equivalent
                                let (c1x, c1y, _) = neighbours[last_idx as usize];
                                let (c2x, c2y, _) = neighbours[i];
                                if board.mark_cells_equivalent(c1x, c1y, c2x, c2y) {
                                    done_something = true;
                                    made_progress = true;
                                }
                                break;
                            }
                        }
                    }
                }
            }
        }

        if done_something {
            continue;
        }

        // =================================================================
        // PHASE 2: Loop avoidance, dead-end avoidance, equivalence filling
        // =================================================================
        for y in 0..h {
            for x in 0..w {
                if board.get_cell_value(x, y) != UNKNOWN {
                    continue;
                }

                let mut fs = false; // Force slash
                let mut bs = false; // Force backslash

                // Check equivalence class value
                let v = board.get_equivalence_class_value(x, y);
                if v == SLASH {
                    fs = true;
                } else if v == BACKSLASH {
                    bs = true;
                }

                // Check if backslash would form loop
                let c1 = board.get_vertex_root(x, y);
                let c2 = board.get_vertex_root(x + 1, y + 1);
                if c1 == c2 {
                    fs = true;
                }

                // Dead-end avoidance for backslash
                if !fs {
                    if !board.get_vertex_group_border(x, y)
                        && !board.get_vertex_group_border(x + 1, y + 1)
                        && board.get_vertex_group_exits(x, y) <= 1
                        && board.get_vertex_group_exits(x + 1, y + 1) <= 1
                    {
                        fs = true;
                    }
                }

                // Check if slash would form loop
                let c1 = board.get_vertex_root(x + 1, y);
                let c2 = board.get_vertex_root(x, y + 1);
                if c1 == c2 {
                    bs = true;
                }

                // Dead-end avoidance for slash
                if !bs {
                    if !board.get_vertex_group_border(x + 1, y)
                        && !board.get_vertex_group_border(x, y + 1)
                        && board.get_vertex_group_exits(x + 1, y) <= 1
                        && board.get_vertex_group_exits(x, y + 1) <= 1
                    {
                        bs = true;
                    }
                }

                if fs && bs {
                    continue; // Contradiction
                }

                if fs {
                    if board.place_value(x, y, SLASH).is_ok() {
                        done_something = true;
                        made_progress = true;
                    }
                } else if bs {
                    if board.place_value(x, y, BACKSLASH).is_ok() {
                        done_something = true;
                        made_progress = true;
                    }
                }
            }
        }
    }

    made_progress
}

/// Trial clue violation - try each diagonal and check for immediate violations.
pub fn rule_trial_clue_violation(board: &mut Board) -> bool {
    let mut made_progress = false;
    let unknown = board.get_unknown_cells();

    for (cx, cy) in unknown {
        let mut slash_valid = !board.would_form_loop(cx, cy, SLASH);
        let mut back_valid = !board.would_form_loop(cx, cy, BACKSLASH);

        // Check clue violations for slash
        if slash_valid {
            // SLASH touches bottom-left and top-right corners
            for &(corner_x, corner_y, touches) in &[
                (cx, cy + 1, true),      // bottom-left
                (cx + 1, cy, true),      // top-right
                (cx, cy, false),         // top-left (avoids)
                (cx + 1, cy + 1, false), // bottom-right (avoids)
            ] {
                if let Some(clue) = board.get_vertex_clue(corner_x, corner_y) {
                    let (current, unknown_count) = board.count_touches(corner_x, corner_y);
                    if touches {
                        if current + 1 > clue {
                            slash_valid = false;
                            break;
                        }
                    } else {
                        if current + unknown_count.saturating_sub(1) < clue {
                            slash_valid = false;
                            break;
                        }
                    }
                }
            }
        }

        // Check clue violations for backslash
        if back_valid {
            // BACKSLASH touches top-left and bottom-right corners
            for &(corner_x, corner_y, touches) in &[
                (cx, cy, true),          // top-left
                (cx + 1, cy + 1, true),  // bottom-right
                (cx, cy + 1, false),     // bottom-left (avoids)
                (cx + 1, cy, false),     // top-right (avoids)
            ] {
                if let Some(clue) = board.get_vertex_clue(corner_x, corner_y) {
                    let (current, unknown_count) = board.count_touches(corner_x, corner_y);
                    if touches {
                        if current + 1 > clue {
                            back_valid = false;
                            break;
                        }
                    } else {
                        if current + unknown_count.saturating_sub(1) < clue {
                            back_valid = false;
                            break;
                        }
                    }
                }
            }
        }

        if slash_valid && !back_valid {
            if board.place_value(cx, cy, SLASH).is_ok() {
                made_progress = true;
            }
        } else if back_valid && !slash_valid {
            if board.place_value(cx, cy, BACKSLASH).is_ok() {
                made_progress = true;
            }
        }
    }

    made_progress
}

/// One step lookahead - check if placing a diagonal causes an adjacent cell to have no options.
pub fn rule_one_step_lookahead(board: &mut Board) -> bool {
    let mut made_progress = false;
    let unknown = board.get_unknown_cells();

    for (cx, cy) in &unknown {
        let cx = *cx;
        let cy = *cy;

        // Try SLASH
        let mut slash_causes_contradiction = board.would_form_loop(cx, cy, SLASH);

        if !slash_causes_contradiction {
            let state = board.save_state();
            if board.place_value(cx, cy, SLASH).is_ok() {
                // Check if any adjacent unknown now has no valid options
                for (ax, ay) in board.get_unknown_cells() {
                    let s_ok = !board.would_form_loop(ax, ay, SLASH);
                    let b_ok = !board.would_form_loop(ax, ay, BACKSLASH);
                    if !s_ok && !b_ok {
                        slash_causes_contradiction = true;
                        break;
                    }
                }
            }
            board.restore_state(&state);
        }

        // Try BACKSLASH
        let mut back_causes_contradiction = board.would_form_loop(cx, cy, BACKSLASH);

        if !back_causes_contradiction {
            let state = board.save_state();
            if board.place_value(cx, cy, BACKSLASH).is_ok() {
                for (ax, ay) in board.get_unknown_cells() {
                    let s_ok = !board.would_form_loop(ax, ay, SLASH);
                    let b_ok = !board.would_form_loop(ax, ay, BACKSLASH);
                    if !s_ok && !b_ok {
                        back_causes_contradiction = true;
                        break;
                    }
                }
            }
            board.restore_state(&state);
        }

        if slash_causes_contradiction && !back_causes_contradiction {
            if board.place_value(cx, cy, BACKSLASH).is_ok() {
                made_progress = true;
            }
        } else if back_causes_contradiction && !slash_causes_contradiction {
            if board.place_value(cx, cy, SLASH).is_ok() {
                made_progress = true;
            }
        }
    }

    made_progress
}

// Helper functions

/// Get adjacent unknown cells for a vertex with their touch relationships.
/// Returns Vec<(cell_x, cell_y, slash_touches, backslash_touches)>
fn get_adjacent_unknown_cells(board: &Board, vx: usize, vy: usize) -> Vec<(usize, usize, bool, bool)> {
    let mut result = Vec::new();

    // Top-left cell (vertex is its bottom-right corner) - backslash touches
    if vx > 0 && vy > 0 && board.get_cell_value(vx - 1, vy - 1) == UNKNOWN {
        result.push((vx - 1, vy - 1, false, true));
    }

    // Top-right cell (vertex is its bottom-left corner) - slash touches
    if vx < board.width && vy > 0 && board.get_cell_value(vx, vy - 1) == UNKNOWN {
        result.push((vx, vy - 1, true, false));
    }

    // Bottom-left cell (vertex is its top-right corner) - slash touches
    if vx > 0 && vy < board.height && board.get_cell_value(vx - 1, vy) == UNKNOWN {
        result.push((vx - 1, vy, true, false));
    }

    // Bottom-right cell (vertex is its top-left corner) - backslash touches
    if vx < board.width && vy < board.height && board.get_cell_value(vx, vy) == UNKNOWN {
        result.push((vx, vy, false, true));
    }

    result
}

/// Get all adjacent cells for a vertex (including solved ones).
fn get_adjacent_cells_coords(board: &Board, vx: usize, vy: usize) -> Vec<(usize, usize, bool, bool)> {
    let mut result = Vec::new();

    if vx > 0 && vy > 0 {
        result.push((vx - 1, vy - 1, false, true));
    }
    if vx < board.width && vy > 0 {
        result.push((vx, vy - 1, true, false));
    }
    if vx > 0 && vy < board.height {
        result.push((vx - 1, vy, true, false));
    }
    if vx < board.width && vy < board.height {
        result.push((vx, vy, false, true));
    }

    result
}

/// Count total adjacent cells for a vertex.
fn count_adjacent_cells(board: &Board, vx: usize, vy: usize) -> usize {
    let mut count = 0;
    if vx > 0 && vy > 0 { count += 1; }
    if vx < board.width && vy > 0 { count += 1; }
    if vx > 0 && vy < board.height { count += 1; }
    if vx < board.width && vy < board.height { count += 1; }
    count
}
