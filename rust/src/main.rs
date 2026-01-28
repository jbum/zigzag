//! Slants (Gokigen Naname) puzzle solver CLI.
//!
//! Usage: slants_solver [OPTIONS] <INPUT_FILE>
//!
//! Reads puzzles from a testsuite file and attempts to solve them.

mod board;
mod rules;
mod solver_bf;
mod solver_pr;

use std::env;
use std::fs::File;
use std::io::{BufRead, BufReader};
use std::time::Instant;

use board::parse_puzzle_line;

fn print_usage() {
    eprintln!("Usage: slants_solver [OPTIONS] <INPUT_FILE>");
    eprintln!();
    eprintln!("Options:");
    eprintln!("  -s, --solver <PR|BF>  Solver to use (default: PR)");
    eprintln!("  -n <N>                Maximum number of puzzles to test");
    eprintln!("  -ofst <N>             Puzzle number to start at (1-based, default: 1)");
    eprintln!("  -f, --filter <STR>    Filter puzzles by partial name match");
    eprintln!("  -v, --verbose         Output testsuite-compatible lines with work scores");
    eprintln!("  -mt, --max_tier <N>   Maximum rule tier to use (1, 2, or 3, default: 10 = all)");
    eprintln!("  -h, --help            Show this help message");
}

fn main() {
    let args: Vec<String> = env::args().collect();

    if args.len() < 2 {
        print_usage();
        std::process::exit(1);
    }

    // Parse arguments
    let mut input_file: Option<String> = None;
    let mut solver = "PR".to_string();
    let mut max_n: Option<usize> = None;
    let mut offset = 1usize;
    let mut filter: Option<String> = None;
    let mut verbose = false;
    let mut max_tier = 10u8;

    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "-h" | "--help" => {
                print_usage();
                return;
            }
            "-s" | "--solver" => {
                i += 1;
                if i < args.len() {
                    solver = args[i].to_uppercase();
                }
            }
            "-n" => {
                i += 1;
                if i < args.len() {
                    max_n = args[i].parse().ok();
                }
            }
            "-ofst" => {
                i += 1;
                if i < args.len() {
                    offset = args[i].parse().unwrap_or(1);
                }
            }
            "-f" | "--filter" => {
                i += 1;
                if i < args.len() {
                    filter = Some(args[i].clone());
                }
            }
            "-v" | "--verbose" => {
                verbose = true;
            }
            "-mt" | "--max_tier" => {
                i += 1;
                if i < args.len() {
                    max_tier = args[i].parse().unwrap_or(10);
                }
            }
            arg if !arg.starts_with('-') => {
                input_file = Some(arg.to_string());
            }
            _ => {
                eprintln!("Unknown option: {}", args[i]);
                print_usage();
                std::process::exit(1);
            }
        }
        i += 1;
    }

    let input_file = match input_file {
        Some(f) => f,
        None => {
            eprintln!("Error: No input file specified");
            print_usage();
            std::process::exit(1);
        }
    };

    // Read puzzles
    let file = match File::open(&input_file) {
        Ok(f) => f,
        Err(e) => {
            eprintln!("Error opening file {}: {}", input_file, e);
            std::process::exit(1);
        }
    };

    let reader = BufReader::new(file);
    let mut puzzles = Vec::new();

    for line in reader.lines() {
        let line = match line {
            Ok(l) => l,
            Err(_) => continue,
        };
        if let Some(puzzle) = parse_puzzle_line(&line) {
            puzzles.push(puzzle);
        }
    }

    if puzzles.is_empty() {
        eprintln!("No puzzles found in {}", input_file);
        std::process::exit(1);
    }

    // Apply filter
    if let Some(ref f) = filter {
        puzzles.retain(|p| p.name.contains(f));
        if puzzles.is_empty() {
            eprintln!("No puzzles matching filter '{}'", f);
            std::process::exit(1);
        }
    }

    // Apply offset and limit
    let start_idx = offset.saturating_sub(1);
    if start_idx >= puzzles.len() {
        eprintln!("Offset {} is beyond the number of puzzles ({})", offset, puzzles.len());
        std::process::exit(1);
    }

    puzzles = puzzles[start_idx..].to_vec();

    if let Some(n) = max_n {
        puzzles.truncate(n);
    }

    // Solve puzzles
    let total_puzzles = puzzles.len();
    let mut solved_count = 0usize;
    let mut unsolved_count = 0usize;
    let mut mult_count = 0usize;
    let mut total_work_score = 0u32;
    let mut tier_counts = [0usize; 4]; // tiers 0, 1, 2, 3

    let start_time = Instant::now();

    for (_i, puzzle) in puzzles.iter().enumerate() {
        let result = match solver.as_str() {
            "BF" => solver_bf::solve(&puzzle.givens, puzzle.width, puzzle.height, max_tier),
            _ => solver_pr::solve(&puzzle.givens, puzzle.width, puzzle.height, max_tier),
        };

        let result = match result {
            Ok(r) => r,
            Err(e) => {
                eprintln!("Error solving {}: {}", puzzle.name, e);
                continue;
            }
        };

        let is_solved = result.status == "solved";
        let is_mult = result.status == "mult";
        let unsolved_squares = result.solution.chars().filter(|&c| c == '.').count();

        if is_solved {
            solved_count += 1;
            total_work_score += result.work_score;
            if result.max_tier_used <= 3 {
                tier_counts[result.max_tier_used as usize] += 1;
            }
        } else if is_mult {
            mult_count += 1;
        } else {
            unsolved_count += 1;
        }

        if verbose {
            let solution_str = if is_solved { &result.solution } else { "" };
            let mut comment_parts = Vec::new();
            if let Some(ref c) = puzzle.comment {
                if !c.is_empty() {
                    comment_parts.push(c.clone());
                }
            }
            comment_parts.push(format!("work_score={}", result.work_score));
            if !is_solved {
                comment_parts.push(format!("status={}", result.status));
                if unsolved_squares > 0 {
                    comment_parts.push(format!("unsolved={}", unsolved_squares));
                }
            }
            let comment = comment_parts.join(" ");

            println!("{}\t{}\t{}\t{}\t{}\t# {}",
                puzzle.name, puzzle.width, puzzle.height,
                puzzle.givens, solution_str, comment
            );
        }
    }

    let elapsed_time = start_time.elapsed().as_secs_f64();

    // Print summary
    let solved_pct = if total_puzzles > 0 {
        solved_count as f64 / total_puzzles as f64 * 100.0
    } else {
        0.0
    };

    let unsolved_pct = if total_puzzles > 0 {
        (unsolved_count + mult_count) as f64 / total_puzzles as f64 * 100.0
    } else {
        0.0
    };

    if !verbose {
        println!();
        println!("Input file: {}", input_file);
        println!("Solver: {}", solver);
        if max_tier < 10 {
            println!("Max tier: {}", max_tier);
        }
        println!("Puzzles tested: {}", total_puzzles);
        println!("Solved: {} ({:.1}%)", solved_count, solved_pct);
        if mult_count > 0 {
            println!("Multiple solutions: {}", mult_count);
        }
        println!("Unsolved: {} ({:.1}%)", unsolved_count, unsolved_pct);
        if solved_count > 0 {
            let tier_parts: Vec<String> = (1..=3)
                .map(|t| {
                    let count = tier_counts[t];
                    let pct = count as f64 / solved_count as f64 * 100.0;
                    format!("{}={} ({:.0}%)", t, count, pct)
                })
                .collect();
            println!("Tiers: {}", tier_parts.join(" "));
        }
        println!("Elapsed time: {:.3}s", elapsed_time);
        println!("Total work score: {}", total_work_score);
        if solved_count > 0 {
            println!("Average work score per solved puzzle: {:.1}",
                total_work_score as f64 / solved_count as f64);
        }
    } else {
        println!("# Summary: {}/{} ({:.1}%) solved, time={:.3}s, total_work_score={}",
            solved_count, total_puzzles, solved_pct, elapsed_time, total_work_score);
    }
}
