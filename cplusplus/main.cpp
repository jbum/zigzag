#include "solver.h"
#include <iostream>
#include <fstream>
#include <sstream>
#include <vector>
#include <string>
#include <chrono>
#include <algorithm>
#include <map>
#include <cstring>

struct Puzzle {
    std::string name;
    int width;
    int height;
    std::string givens;
    std::string answer;
    std::string comment;
};

Puzzle* parsePuzzleLine(const std::string& line) {
    std::string trimmed = line;
    // Trim whitespace
    size_t start = trimmed.find_first_not_of(" \t\r\n");
    if (start == std::string::npos) return nullptr;
    trimmed = trimmed.substr(start);
    size_t end = trimmed.find_last_not_of(" \t\r\n");
    if (end != std::string::npos) trimmed = trimmed.substr(0, end + 1);

    if (trimmed.empty() || trimmed[0] == '#' || trimmed[0] == ';') {
        return nullptr;
    }

    std::vector<std::string> parts;
    std::istringstream iss(trimmed);
    std::string part;
    while (std::getline(iss, part, '\t')) {
        parts.push_back(part);
    }

    if (parts.size() < 4) {
        return nullptr;
    }

    int width, height;
    try {
        width = std::stoi(parts[1]);
        height = std::stoi(parts[2]);
    } catch (...) {
        return nullptr;
    }

    Puzzle* puzzle = new Puzzle();
    puzzle->name = parts[0];
    puzzle->width = width;
    puzzle->height = height;
    puzzle->givens = parts[3];

    if (parts.size() > 4) {
        puzzle->answer = parts[4];
    }
    if (parts.size() > 5) {
        std::string comment = parts[5];
        if (!comment.empty() && comment[0] == '#') {
            comment = comment.substr(1);
            size_t s = comment.find_first_not_of(" \t");
            if (s != std::string::npos) comment = comment.substr(s);
        }
        puzzle->comment = comment;
    }

    return puzzle;
}

std::vector<Puzzle*> loadPuzzles(const std::string& filepath) {
    std::vector<Puzzle*> puzzles;
    std::ifstream file(filepath);
    if (!file.is_open()) {
        std::cerr << "Error opening file: " << filepath << std::endl;
        return puzzles;
    }

    std::string line;
    while (std::getline(file, line)) {
        Puzzle* puzzle = parsePuzzleLine(line);
        if (puzzle) {
            puzzles.push_back(puzzle);
        }
    }

    return puzzles;
}

void printUsage(const char* progname) {
    std::cerr << "Usage: " << progname << " [options] <input_file>\n";
    std::cerr << "Options:\n";
    std::cerr << "  -v            Output testsuite-compatible lines with work scores\n";
    std::cerr << "  -d            Show debug output for each puzzle\n";
    std::cerr << "  -f <filter>   Filter puzzles by partial name match\n";
    std::cerr << "  -n <count>    Maximum number of puzzles to test (0 = all)\n";
    std::cerr << "  -ofst <num>   Puzzle number to start at (1-based, default: 1)\n";
    std::cerr << "  -s <solver>   Solver to use: PR (production rules) or BF (brute force, default)\n";
    std::cerr << "  -mt <tier>    Maximum rule tier to use (1, 2, or 3). Default 10 uses all rules\n";
    std::cerr << "  -ou           Output list of unsolved puzzles (sorted by size)\n";
}

int main(int argc, char* argv[]) {
    // Parse command line arguments
    bool verbose = false;
    bool debug = false;
    std::string filter;
    int numPuzzles = 0;
    int offset = 1;
    std::string solver = "BF";
    int maxTier = 10;
    bool outputUnsolved = false;
    std::string inputFile;

    for (int i = 1; i < argc; i++) {
        std::string arg = argv[i];
        if (arg == "-v") {
            verbose = true;
        } else if (arg == "-d") {
            debug = true;
        } else if (arg == "-f" && i + 1 < argc) {
            filter = argv[++i];
        } else if (arg == "-n" && i + 1 < argc) {
            numPuzzles = std::stoi(argv[++i]);
        } else if (arg == "-ofst" && i + 1 < argc) {
            offset = std::stoi(argv[++i]);
        } else if (arg == "-s" && i + 1 < argc) {
            solver = argv[++i];
        } else if (arg == "-mt" && i + 1 < argc) {
            maxTier = std::stoi(argv[++i]);
        } else if (arg == "-ou") {
            outputUnsolved = true;
        } else if (arg[0] != '-') {
            inputFile = arg;
        } else {
            std::cerr << "Unknown option: " << arg << std::endl;
            printUsage(argv[0]);
            return 1;
        }
    }

    if (inputFile.empty()) {
        printUsage(argv[0]);
        return 1;
    }

    // Load puzzles
    auto puzzles = loadPuzzles(inputFile);
    if (puzzles.empty()) {
        std::cerr << "No puzzles found in " << inputFile << std::endl;
        return 1;
    }

    // Apply filter
    if (!filter.empty()) {
        std::vector<Puzzle*> filtered;
        for (auto* p : puzzles) {
            if (p->name.find(filter) != std::string::npos) {
                filtered.push_back(p);
            } else {
                delete p;
            }
        }
        puzzles = filtered;
        if (puzzles.empty()) {
            std::cerr << "No puzzles matching filter '" << filter << "'" << std::endl;
            return 1;
        }
    }

    // Apply offset and limit
    int startIdx = offset - 1;
    if (startIdx < 0) startIdx = 0;
    if (startIdx >= (int)puzzles.size()) {
        std::cerr << "Offset " << offset << " is beyond the number of puzzles (" << puzzles.size() << ")" << std::endl;
        return 1;
    }

    // Remove puzzles before startIdx
    for (int i = 0; i < startIdx; i++) {
        delete puzzles[i];
    }
    puzzles.erase(puzzles.begin(), puzzles.begin() + startIdx);

    if (numPuzzles > 0 && numPuzzles < (int)puzzles.size()) {
        for (size_t i = numPuzzles; i < puzzles.size(); i++) {
            delete puzzles[i];
        }
        puzzles.resize(numPuzzles);
    }

    // Select solve function
    auto solveFn = (solver == "PR") ? SolvePR : SolveBF;

    // Solve puzzles
    int totalPuzzles = (int)puzzles.size();
    int solvedCount = 0;
    int unsolvedCount = 0;
    int multCount = 0;
    int totalWorkScore = 0;
    std::vector<Puzzle*> unsolvedPuzzles;
    int totalUnsolvedSquares = 0;
    std::map<int, int> tierCounts = {{1, 0}, {2, 0}, {3, 0}};

    auto startTime = std::chrono::high_resolution_clock::now();

    for (int i = 0; i < (int)puzzles.size(); i++) {
        Puzzle* puzzle = puzzles[i];
        int puzzleNum = startIdx + i + 1;

        if (debug) {
            std::cout << "\n" << std::string(60, '=') << "\n";
            std::cout << "Puzzle " << puzzleNum << ": " << puzzle->name
                      << " (" << puzzle->width << "x" << puzzle->height << ")\n";
            std::cout << "Givens: " << puzzle->givens << "\n";
            std::cout << std::string(60, '=') << "\n";
        }

        SolveResult result = solveFn(puzzle->givens, puzzle->width, puzzle->height, maxTier);

        // Count unsolved squares
        int unsolvedSquares = 0;
        for (char c : result.solutionString) {
            if (c == '.') unsolvedSquares++;
        }
        totalUnsolvedSquares += unsolvedSquares;

        bool isSolved = (result.status == "solved");
        bool isMult = (result.status == "mult");

        if (isSolved) {
            solvedCount++;
            totalWorkScore += result.workScore;
            if (tierCounts.find(result.maxTierUsed) != tierCounts.end()) {
                tierCounts[result.maxTierUsed]++;
            }

            if (debug && !puzzle->answer.empty() && result.solutionString != puzzle->answer) {
                std::cout << "NOTE: Solution differs from expected answer\n";
                std::cout << "  Got:      " << result.solutionString << "\n";
                std::cout << "  Expected: " << puzzle->answer << "\n";
            }
        } else if (isMult) {
            multCount++;
            unsolvedPuzzles.push_back(puzzle);
        } else {
            unsolvedCount++;
            unsolvedPuzzles.push_back(puzzle);
        }

        if (debug) {
            std::string statusUpper = result.status;
            for (auto& c : statusUpper) c = toupper(c);
            std::cout << "\nStatus: " << statusUpper << ", Work score: " << result.workScore << "\n";
            if (unsolvedSquares > 0) {
                std::cout << "Unsolved cells: " << unsolvedSquares << "\n";
            }
        }

        if (verbose) {
            std::string solutionStr = isSolved ? result.solutionString : "";
            std::vector<std::string> commentParts;
            if (!puzzle->comment.empty()) {
                commentParts.push_back(puzzle->comment);
            }
            commentParts.push_back("work_score=" + std::to_string(result.workScore));
            if (!isSolved) {
                commentParts.push_back("status=" + result.status);
                if (unsolvedSquares > 0) {
                    commentParts.push_back("unsolved=" + std::to_string(unsolvedSquares));
                }
            }
            std::string comment;
            for (size_t j = 0; j < commentParts.size(); j++) {
                if (j > 0) comment += " ";
                comment += commentParts[j];
            }

            std::cout << puzzle->name << "\t" << puzzle->width << "\t" << puzzle->height
                      << "\t" << puzzle->givens << "\t" << solutionStr << "\t# " << comment << "\n";
        }
    }

    auto endTime = std::chrono::high_resolution_clock::now();
    double elapsedTime = std::chrono::duration<double>(endTime - startTime).count();

    // Print summary
    double solvedPct = (totalPuzzles > 0) ? (double)solvedCount / totalPuzzles * 100 : 0;
    double unsolvedPct = (totalPuzzles > 0) ? (double)(unsolvedCount + multCount) / totalPuzzles * 100 : 0;

    if (!verbose) {
        std::cout << "\nInput file: " << inputFile << "\n";
        std::cout << "Solver: " << solver << "\n";
        if (maxTier < 10) {
            std::cout << "Max tier: " << maxTier << "\n";
        }
        std::cout << "Puzzles tested: " << totalPuzzles << "\n";
        std::cout << "Solved: " << solvedCount << " (" << std::fixed;
        std::cout.precision(1);
        std::cout << solvedPct << "%)\n";
        if (multCount > 0) {
            std::cout << "Multiple solutions: " << multCount << "\n";
        }
        std::cout << "Unsolved: " << unsolvedCount << " (" << unsolvedPct << "%)\n";
        if (solvedCount > 0) {
            std::cout << "Tiers: ";
            for (int tier = 1; tier <= 3; tier++) {
                int count = tierCounts[tier];
                double pct = (double)count / solvedCount * 100;
                if (tier > 1) std::cout << " ";
                std::cout << tier << "=" << count << " (" << (int)pct << "%)";
            }
            std::cout << "\n";
        }
        std::cout.precision(3);
        std::cout << "Elapsed time: " << elapsedTime << "s\n";
        std::cout << "Total work score: " << totalWorkScore << "\n";
        if (solvedCount > 0) {
            std::cout.precision(1);
            std::cout << "Average work score per solved puzzle: "
                      << (double)totalWorkScore / solvedCount << "\n";
        }
    } else {
        std::cout.precision(3);
        std::cout << "# Summary: " << solvedCount << "/" << totalPuzzles
                  << " (" << solvedPct << "%) solved, time=" << elapsedTime
                  << "s, total_work_score=" << totalWorkScore << "\n";
    }

    // Output unsolved puzzles
    if (outputUnsolved && !unsolvedPuzzles.empty()) {
        std::cout << "\nUnsolved puzzles (sorted by size):\n";

        // Sort by area, then by name
        std::sort(unsolvedPuzzles.begin(), unsolvedPuzzles.end(), [](Puzzle* a, Puzzle* b) {
            int areaA = a->width * a->height;
            int areaB = b->width * b->height;
            if (areaA != areaB) return areaA < areaB;
            return a->name < b->name;
        });

        for (Puzzle* p : unsolvedPuzzles) {
            int area = p->width * p->height;
            std::cout << "  " << p->name << ": " << p->width << "x" << p->height
                      << " (area=" << area << ")\n";
        }
    }

    // Cleanup
    for (auto* p : puzzles) {
        delete p;
    }

    return 0;
}
