//! Production Rule Solver for Slants (Gokigen Naname) puzzles.

use crate::board::{Board, SolveResult};
use crate::rules::get_pr_rules;

/// Solve a puzzle using production rules.
pub fn solve(
    givens_string: &str,
    width: usize,
    height: usize,
    max_tier: u8,
) -> Result<SolveResult, String> {
    let mut board = Board::new(width, height, givens_string)?;
    let rules = get_pr_rules();

    let max_iterations = 1000;
    let mut iteration = 0;
    let mut total_work_score = 0u32;
    let mut max_tier_used = 0u8;

    while iteration < max_iterations {
        iteration += 1;

        // Check if solved
        if board.is_solved() {
            let status = if board.is_valid_solution() {
                "solved"
            } else {
                "unsolved"
            };

            return Ok(SolveResult {
                status: status.to_string(),
                solution: board.to_solution_string(),
                work_score: total_work_score,
                max_tier_used,
            });
        }

        // Try each rule in order
        let mut made_progress = false;
        for (info, rule_func) in &rules {
            if info.tier > max_tier {
                continue;
            }

            if rule_func(&mut board) {
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

    Ok(SolveResult {
        status: "unsolved".to_string(),
        solution: board.to_solution_string(),
        work_score: total_work_score,
        max_tier_used,
    })
}
