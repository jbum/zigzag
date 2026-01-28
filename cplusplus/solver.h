#ifndef SOLVER_H
#define SOLVER_H

#include <string>

// SolveResult contains the result of solving a puzzle
struct SolveResult {
    std::string status;  // "solved", "unsolved", or "mult"
    std::string solutionString;
    int workScore;
    int maxTierUsed;
};

// SolveBF solves a puzzle using brute-force backtracking
SolveResult SolveBF(const std::string& givensString, int width, int height, int maxTier);

// SolvePR solves a puzzle using production rules only (no backtracking)
SolveResult SolvePR(const std::string& givensString, int width, int height, int maxTier);

#endif // SOLVER_H
