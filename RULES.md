# Rules for Slants Solver

Rules are organized by tier and applied in order from easiest/cheapest to hardest.

## Tier 1 - Easy Rules (Human-solvable, required for basic puzzles)

| Rule | Score | Description |
|------|-------|-------------|
| clue_finish_b | 1 | If a clue has sufficient meets (touches), fill its avoiders. |
| clue_finish_a | 2 | If a clue has sufficient non-meets (avoiders), fill in its meets. |
| no_loops | 2 | If placing a slant would create a loop, place the counter slant. |

## Tier 2 - Medium Rules (Human-solvable, for intermediate puzzles)

| Rule | Score | Description |
|------|-------|-------------|
| edge_clue_constraints | 2 | Edge/corner vertices have fewer adjacent cells, making clues more constraining. *(Heuristic: redundant but improves solve time)* |
| border_two_v_shape | 3 | A 2 on the border forces a V-shape pattern in adjacent cells. |
| loop_avoidance_2 | 5 | If finishing a 2 with two slants would force a loop, finish it another way. |
| v_pattern_with_three | 6 | V-shaped patterns near a 3 constrain remaining touches to the opposite side. *(Heuristic: redundant but improves solve time)* |
| adjacent_ones | 8 | Two adjacent 1s share cells that can only touch one of them. |
| adjacent_threes | 8 | Two adjacent 3s force specific diagonal orientations. |

## Tier 3 - Hard Rules (Trial-and-error, may not be human-solvable)

| Rule | Score | Description |
|------|-------|-------------|
| trial_clue_violation | 10 | Try each diagonal; if one immediately violates a clue, use the other. |
| one_step_lookahead | 15 | Try each diagonal; if one creates an impossible situation one move ahead, use the other. |

## Removed Rules

The following rules were found to be redundant and removed:

- **corner_zero**: Covered by clue_finish_b (clue 0 means 0 touches needed, so all cells avoid)
- **corner_four**: Covered by clue_finish_a (clue 4 means all 4 cells must touch)
- **single_path_extension**: Redundant with other rules; removing improves performance by ~7-14%
- **forced_solution_avoidance**: Redundant with other rules; removing improves performance by ~4-16%
- **diagonal_ones**: Redundant with other rules; removing improves performance by ~3-8%

Combined removal of single_path_extension, forced_solution_avoidance, and diagonal_ones:
- PR solver: 15-32% faster with same success rate
- BF solver: 16-22% faster with same success rate

## Tier Usage

- **Easy puzzles**: Use tier 1 rules only (-mt 1)
- **Normal puzzles**: Use tier 1 and 2 rules (-mt 2)
- **Hard puzzles**: Use all tiers (default)
- **Puzzle generation**: Use -mt 2 to ensure human-solvable puzzles
