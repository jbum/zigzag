#include "solver.h"
#include "board.h"
#include "rules.h"
#include <vector>
#include <algorithm>
#include <memory>

// applyRulesUntilStuck applies rules repeatedly until no more progress
std::pair<int, int> applyRulesUntilStuck(Board* board, const std::vector<Rule>& rules) {
    int totalWorkScore = 0;
    int maxTierUsed = 0;
    int maxIterations = 1000;

    for (int iteration = 0; iteration < maxIterations; iteration++) {
        if (board->isSolved()) {
            break;
        }

        if (!board->isValid()) {
            break;
        }

        bool madeProgress = false;
        for (const auto& rule : rules) {
            if (rule.func(board)) {
                totalWorkScore += rule.score;
                if (rule.tier > maxTierUsed) {
                    maxTierUsed = rule.tier;
                }
                madeProgress = true;
                break;
            }
        }

        if (!madeProgress) {
            break;
        }
    }

    return {totalWorkScore, maxTierUsed};
}

// pickBestCell picks the best cell for branching based on constraints
Cell* pickBestCell(Board* board) {
    auto unknownCells = board->getUnknownCells();
    if (unknownCells.empty()) {
        return nullptr;
    }

    struct CellScore {
        Cell* cell;
        int score;
    };

    std::vector<CellScore> scores;
    for (Cell* cell : unknownCells) {
        int score = 0;
        Vertex *tl, *tr, *bl, *br;
        board->getCellCorners(cell, &tl, &tr, &bl, &br);

        Vertex* corners[] = {tl, tr, bl, br};
        for (Vertex* corner : corners) {
            if (!corner || !corner->hasClue) {
                continue;
            }

            auto [current, unknown] = board->countTouches(corner);
            int clue = corner->clue;

            int remainingNeeded = clue - current;
            int remainingSlots = unknown;

            if (remainingNeeded == remainingSlots) {
                score += 100;
            } else if (remainingNeeded == 0) {
                score += 100;
            } else if (remainingSlots > 0) {
                score += 50 / remainingSlots;
            }
        }

        scores.push_back({cell, score});
    }

    std::sort(scores.begin(), scores.end(), [](const CellScore& a, const CellScore& b) {
        return a.score > b.score;
    });

    return scores[0].cell;
}

// getValidValues returns valid values for a cell
std::vector<int> getValidValues(Board* board, Cell* cell) {
    struct ValuePriority {
        int value;
        int priority;
    };

    std::vector<ValuePriority> valid;

    for (int value : {SLASH, BACKSLASH}) {
        if (board->wouldFormLoop(cell, value)) {
            continue;
        }

        int x = cell->x;
        int y = cell->y;
        Vertex* tl = board->getVertex(x, y);
        Vertex* tr = board->getVertex(x + 1, y);
        Vertex* bl = board->getVertex(x, y + 1);
        Vertex* br = board->getVertex(x + 1, y + 1);

        std::vector<Vertex*> touches;
        if (value == SLASH) {
            touches = {tr, bl};
        } else {
            touches = {tl, br};
        }

        bool isValid = true;
        int priority = 0;

        for (Vertex* corner : touches) {
            if (corner && corner->hasClue) {
                auto [current, _] = board->countTouches(corner);
                if (current >= corner->clue) {
                    isValid = false;
                    break;
                }
                priority += 10;
            }
        }

        if (isValid) {
            valid.push_back({value, priority});
        }
    }

    std::sort(valid.begin(), valid.end(), [](const ValuePriority& a, const ValuePriority& b) {
        return a.priority > b.priority;
    });

    std::vector<int> result;
    for (const auto& v : valid) {
        result.push_back(v.value);
    }
    return result;
}

// stackEntry represents an entry on the backtracking stack
struct StackEntry {
    BoardState state;
    int eliminatedValue;
};

SolveResult SolveBF(const std::string& givensString, int width, int height, int maxTier) {
    std::unique_ptr<Board> board;
    try {
        board = std::make_unique<Board>(width, height, givensString);
    } catch (...) {
        return {"unsolved", "", 0, 0};
    }

    // Filter rules by tier
    std::vector<Rule> filteredRules;
    for (const auto& rule : getRules()) {
        if (rule.tier <= maxTier) {
            filteredRules.push_back(rule);
        }
    }

    std::vector<std::string> solutions;
    std::vector<StackEntry> stack;
    stack.push_back({board->saveState(), -1});
    int totalWorkScore = 0;
    int maxTierUsed = 0;
    bool usedBranching = false;
    int pushPopScore = 0;

    while (!stack.empty() && solutions.size() < 2) {
        StackEntry entry = std::move(stack.back());
        stack.pop_back();
        board->restoreState(entry.state);
        pushPopScore++;

        // Apply rules
        auto [workScore, tierUsed] = applyRulesUntilStuck(board.get(), filteredRules);
        totalWorkScore += workScore;
        if (tierUsed > maxTierUsed) {
            maxTierUsed = tierUsed;
        }

        // Check validity
        if (!board->isValid()) {
            continue;
        }

        // Check if solved
        if (board->isSolved()) {
            if (board->isValidSolution()) {
                solutions.push_back(board->toSolutionString());
            }
            continue;
        }

        // Choose cell for branching
        Cell* cell = pickBestCell(board.get());
        if (!cell) {
            continue;
        }

        // Get valid values
        auto validValues = getValidValues(board.get(), cell);
        if (validValues.empty()) {
            continue;
        }

        // Push states for each valid value
        BoardState savedState = board->saveState();
        for (int i = (int)validValues.size() - 1; i >= 0; i--) {
            int value = validValues[i];
            board->restoreState(savedState);
            if (board->placeValue(cell, value)) {
                stack.push_back({board->saveState(), value});
                pushPopScore++;
                usedBranching = true;
            }
        }
        board->restoreState(savedState);
    }

    // Determine status
    std::string status;
    if (solutions.size() >= 2) {
        status = "mult";
    } else if (solutions.size() == 1) {
        status = "solved";
    } else {
        status = "unsolved";
    }

    // Get solution string
    std::string solutionString;
    if (solutions.size() == 1) {
        solutionString = solutions[0];
    } else {
        solutionString = board->toSolutionString();
    }

    // Add push/pop score
    totalWorkScore += pushPopScore * 2;

    // If we used branching, promote to tier 3
    if (usedBranching) {
        maxTierUsed = 3;
    }

    return {status, solutionString, totalWorkScore, maxTierUsed};
}

SolveResult SolvePR(const std::string& givensString, int width, int height, int maxTier) {
    std::unique_ptr<Board> board;
    try {
        board = std::make_unique<Board>(width, height, givensString);
    } catch (...) {
        return {"unsolved", "", 0, 0};
    }

    // Filter rules by tier
    std::vector<Rule> filteredRules;
    for (const auto& rule : getRules()) {
        if (rule.tier <= maxTier) {
            filteredRules.push_back(rule);
        }
    }

    int totalWorkScore = 0;
    int maxTierUsed = 0;
    int maxIterations = 1000;

    for (int iteration = 0; iteration < maxIterations; iteration++) {
        if (board->isSolved()) {
            break;
        }

        bool madeProgress = false;
        for (const auto& rule : filteredRules) {
            if (rule.func(board.get())) {
                totalWorkScore += rule.score;
                if (rule.tier > maxTierUsed) {
                    maxTierUsed = rule.tier;
                }
                madeProgress = true;
                break;
            }
        }

        if (!madeProgress) {
            break;
        }
    }

    std::string status;
    if (board->isSolved() && board->isValidSolution()) {
        status = "solved";
    } else {
        status = "unsolved";
    }

    return {status, board->toSolutionString(), totalWorkScore, maxTierUsed};
}
