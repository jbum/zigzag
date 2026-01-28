//! Brute Force Solver for Slants (Gokigen Naname) puzzles.
//! Uses production rules plus stack-based backtracking.

use crate::board::{Board, BoardState, SolveResult, SLASH, BACKSLASH};
use crate::rules::{get_bf_rules, RuleInfo};

/// Apply rules until no more progress can be made.
fn apply_rules_until_stuck(
    board: &mut Board,
    rules: &[(RuleInfo, fn(&mut Board) -> bool)],
    max_tier: u8,
) -> (u32, u8) {
    let mut total_work_score = 0u32;
    let mut max_tier_used = 0u8;
    let max_iterations = 1000;
    let mut iteration = 0;

    while iteration < max_iterations {
        iteration += 1;

        if board.is_solved() || !board.is_valid() {
            break;
        }

        let mut made_progress = false;
        for (info, rule_func) in rules {
            if info.tier > max_tier {
                continue;
            }

            if rule_func(board) {
                total_work_score += info.score;
                max_tier_used = max_tier_used.max(info.tier);
                made_progress = true;
                break;
            }
        }

        if !made_progress {
            break;
        }
    }

    (total_work_score, max_tier_used)
}

/// Pick the best cell for branching.
fn pick_best_cell(board: &Board) -> Option<(usize, usize)> {
    let unknown_cells = board.get_unknown_cells();
    if unknown_cells.is_empty() {
        return None;
    }

    // Score cells by how constrained they are
    let mut best_cell = unknown_cells[0];
    let mut best_score = 0i32;

    for (cx, cy) in unknown_cells {
        let mut score = 0i32;

        // Check all 4 corners
        for &(vx, vy) in &[
            (cx, cy),
            (cx + 1, cy),
            (cx, cy + 1),
            (cx + 1, cy + 1),
        ] {
            if let Some(clue) = board.get_vertex_clue(vx, vy) {
                let (current, unknown) = board.count_touches(vx, vy);
                let remaining_needed = clue.saturating_sub(current);

                if remaining_needed == unknown {
                    score += 100;
                } else if remaining_needed == 0 {
                    score += 100;
                } else if unknown > 0 {
                    score += 50 / (unknown as i32);
                }
            }
        }

        if score > best_score {
            best_score = score;
            best_cell = (cx, cy);
        }
    }

    Some(best_cell)
}

/// Get valid values for a cell.
fn get_valid_values(board: &mut Board, cx: usize, cy: usize) -> Vec<u8> {
    let mut valid = Vec::new();

    for value in [SLASH, BACKSLASH] {
        if board.would_form_loop(cx, cy, value) {
            continue;
        }

        // Check if this would violate any vertex clue
        let (touches, _avoids) = if value == SLASH {
            // SLASH touches bottom-left and top-right
            ([(cx, cy + 1), (cx + 1, cy)], [(cx, cy), (cx + 1, cy + 1)])
        } else {
            // BACKSLASH touches top-left and bottom-right
            ([(cx, cy), (cx + 1, cy + 1)], [(cx, cy + 1), (cx + 1, cy)])
        };

        let mut is_valid = true;

        for (vx, vy) in touches {
            if let Some(clue) = board.get_vertex_clue(vx, vy) {
                let (current, _) = board.count_touches(vx, vy);
                if current >= clue {
                    is_valid = false;
                    break;
                }
            }
        }

        if is_valid {
            valid.push(value);
        }
    }

    valid
}

/// Solve a puzzle using brute-force backtracking.
pub fn solve(
    givens_string: &str,
    width: usize,
    height: usize,
    max_tier: u8,
) -> Result<SolveResult, String> {
    let mut board = Board::new(width, height, givens_string)?;
    let rules = get_bf_rules();

    let mut solutions: Vec<String> = Vec::new();
    let mut stack: Vec<(BoardState, Option<u8>)> = vec![(board.save_state(), None)];
    let mut total_work_score = 0u32;
    let mut max_tier_used = 0u8;
    let mut used_branching = false;
    let mut push_pop_score = 0u32;

    while !stack.is_empty() && solutions.len() < 2 {
        let (state, _eliminated_value) = stack.pop().unwrap();
        board.restore_state(&state);
        push_pop_score += 1;

        // Apply rules
        let (work_score, tier_used) = apply_rules_until_stuck(&mut board, &rules, max_tier);
        total_work_score += work_score;
        max_tier_used = max_tier_used.max(tier_used);

        // Check validity
        if !board.is_valid() {
            continue;
        }

        // Check if solved
        if board.is_solved() {
            if board.is_valid_solution() {
                solutions.push(board.to_solution_string());
                continue;
            } else {
                continue;
            }
        }

        // Choose cell for branching
        let (cx, cy) = match pick_best_cell(&board) {
            Some(cell) => cell,
            None => continue,
        };

        // Get valid values
        let valid_values = get_valid_values(&mut board, cx, cy);
        if valid_values.is_empty() {
            continue;
        }

        // Push states for each valid value
        let saved_state = board.save_state();
        for value in valid_values.iter().rev() {
            board.restore_state(&saved_state);
            if board.place_value(cx, cy, *value).is_ok() {
                stack.push((board.save_state(), Some(*value)));
                push_pop_score += 1;
                used_branching = true;
            }
        }
        board.restore_state(&saved_state);
    }

    // Determine status
    let status = if solutions.len() >= 2 {
        "mult".to_string()
    } else if solutions.len() == 1 {
        "solved".to_string()
    } else {
        "unsolved".to_string()
    };

    let solution = if solutions.len() == 1 {
        solutions[0].clone()
    } else {
        board.to_solution_string()
    };

    total_work_score += push_pop_score * 2;

    if used_branching {
        max_tier_used = 3;
    }

    Ok(SolveResult {
        status,
        solution,
        work_score: total_work_score,
        max_tier_used,
    })
}
