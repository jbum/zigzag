#ifndef RULES_H
#define RULES_H

#include "board.h"
#include <functional>
#include <string>
#include <vector>

// Rule represents a production rule for solving Slants puzzles
struct Rule {
    std::string name;
    int score;
    int tier;
    std::function<bool(Board*)> func;
};

// Get the list of all rules
std::vector<Rule> getRules();

// Individual rule functions
bool ruleClueFinishB(Board* board);
bool ruleClueFinishA(Board* board);
bool ruleNoLoops(Board* board);
bool ruleEdgeClueConstraints(Board* board);
bool ruleBorderTwoVShape(Board* board);
bool ruleLoopAvoidance2(Board* board);
bool ruleVPatternWithThree(Board* board);
bool ruleAdjacentOnes(Board* board);
bool ruleAdjacentThrees(Board* board);
bool ruleDeadEndAvoidance(Board* board);
bool ruleEquivalenceClasses(Board* board);
bool ruleVBitmapPropagation(Board* board);
bool ruleSimonUnified(Board* board);

#endif // RULES_H
