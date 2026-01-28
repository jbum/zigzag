#include "rules.h"
#include <map>
#include <set>
#include <cmath>

std::vector<Rule> getRules() {
    return {
        {"clue_finish_b", 1, 1, ruleClueFinishB},
        {"clue_finish_a", 2, 1, ruleClueFinishA},
        {"no_loops", 2, 1, ruleNoLoops},
        {"edge_clue_constraints", 2, 2, ruleEdgeClueConstraints},
        {"border_two_v_shape", 3, 2, ruleBorderTwoVShape},
        {"loop_avoidance_2", 5, 1, ruleLoopAvoidance2},
        {"v_pattern_with_three", 6, 2, ruleVPatternWithThree},
        {"adjacent_ones", 8, 2, ruleAdjacentOnes},
        {"adjacent_threes", 8, 2, ruleAdjacentThrees},
        {"dead_end_avoidance", 9, 2, ruleDeadEndAvoidance},
        {"equivalence_classes", 9, 2, ruleEquivalenceClasses},
        {"vbitmap_propagation", 9, 2, ruleVBitmapPropagation},
        {"simon_unified", 9, 2, ruleSimonUnified},
    };
}

// ruleClueFinishA: If a clue needs all remaining unknowns to touch, fill them.
bool ruleClueFinishA(Board* board) {
    bool madeProgress = false;

    for (Vertex* vertex : board->getCluedVertices()) {
        auto adjacent = board->getAdjacentCellsForVertex(vertex);
        int clue = vertex->clue;

        int currentTouches = 0;
        std::vector<AdjacentCellInfo> unknownCells;

        for (auto& adj : adjacent) {
            if (adj.cell->value == UNKNOWN) {
                unknownCells.push_back(adj);
            } else if (adj.cell->value == SLASH && adj.slashTouches) {
                currentTouches++;
            } else if (adj.cell->value == BACKSLASH && adj.backslashTouches) {
                currentTouches++;
            }
        }

        int neededTouches = clue - currentTouches;

        // If all unknowns must touch to reach the clue
        if (neededTouches > 0 && neededTouches == (int)unknownCells.size()) {
            for (auto& adj : unknownCells) {
                if (adj.slashTouches) {
                    if (!board->wouldFormLoop(adj.cell, SLASH)) {
                        board->placeValue(adj.cell, SLASH);
                        madeProgress = true;
                    }
                } else {
                    if (!board->wouldFormLoop(adj.cell, BACKSLASH)) {
                        board->placeValue(adj.cell, BACKSLASH);
                        madeProgress = true;
                    }
                }
            }
        }
    }

    return madeProgress;
}

// ruleClueFinishB: If a clue already has enough touches, fill avoiders.
bool ruleClueFinishB(Board* board) {
    bool madeProgress = false;

    for (Vertex* vertex : board->getCluedVertices()) {
        auto adjacent = board->getAdjacentCellsForVertex(vertex);
        int clue = vertex->clue;

        int currentTouches = 0;
        std::vector<AdjacentCellInfo> unknownCells;

        for (auto& adj : adjacent) {
            if (adj.cell->value == UNKNOWN) {
                unknownCells.push_back(adj);
            } else if (adj.cell->value == SLASH && adj.slashTouches) {
                currentTouches++;
            } else if (adj.cell->value == BACKSLASH && adj.backslashTouches) {
                currentTouches++;
            }
        }

        // If we already have enough touches, remaining must avoid
        if (currentTouches == clue && !unknownCells.empty()) {
            for (auto& adj : unknownCells) {
                if (adj.slashTouches) {
                    // Slash would touch, so place backslash to avoid
                    if (!board->wouldFormLoop(adj.cell, BACKSLASH)) {
                        board->placeValue(adj.cell, BACKSLASH);
                        madeProgress = true;
                    }
                } else {
                    // Backslash would touch, so place slash to avoid
                    if (!board->wouldFormLoop(adj.cell, SLASH)) {
                        board->placeValue(adj.cell, SLASH);
                        madeProgress = true;
                    }
                }
            }
        }
    }

    return madeProgress;
}

// ruleNoLoops: If placing one diagonal creates a loop, place the other.
bool ruleNoLoops(Board* board) {
    bool madeProgress = false;

    for (Cell* cell : board->getUnknownCells()) {
        bool slashLoops = board->wouldFormLoop(cell, SLASH);
        bool backslashLoops = board->wouldFormLoop(cell, BACKSLASH);

        if (slashLoops && !backslashLoops) {
            board->placeValue(cell, BACKSLASH);
            madeProgress = true;
        } else if (backslashLoops && !slashLoops) {
            board->placeValue(cell, SLASH);
            madeProgress = true;
        }
    }

    return madeProgress;
}

// ruleEdgeClueConstraints: Edge/corner vertices have stricter constraints.
bool ruleEdgeClueConstraints(Board* board) {
    bool madeProgress = false;

    for (Vertex* vertex : board->getCluedVertices()) {
        auto adjacent = board->getAdjacentCellsForVertex(vertex);
        int maxPossible = (int)adjacent.size();
        int clue = vertex->clue;

        if (clue > maxPossible) {
            continue;
        }

        // If clue equals max possible, all must touch
        if (clue == maxPossible) {
            for (auto& adj : adjacent) {
                if (adj.cell->value != UNKNOWN) {
                    continue;
                }
                if (adj.slashTouches) {
                    if (!board->wouldFormLoop(adj.cell, SLASH)) {
                        board->placeValue(adj.cell, SLASH);
                        madeProgress = true;
                    }
                } else {
                    if (!board->wouldFormLoop(adj.cell, BACKSLASH)) {
                        board->placeValue(adj.cell, BACKSLASH);
                        madeProgress = true;
                    }
                }
            }
        }
    }

    return madeProgress;
}

// ruleBorderTwoVShape: A 2 on the border with only 2 adjacent cells forces V-shape.
bool ruleBorderTwoVShape(Board* board) {
    bool madeProgress = false;

    for (Vertex* vertex : board->getCluedVertices()) {
        if (vertex->clue != 2) {
            continue;
        }

        auto adjacent = board->getAdjacentCellsForVertex(vertex);
        if (adjacent.size() != 2) {
            continue;
        }

        auto [current, unknown] = board->countTouches(vertex);
        if (current + unknown == 2 && unknown > 0) {
            for (auto& adj : adjacent) {
                if (adj.cell->value != UNKNOWN) {
                    continue;
                }
                if (adj.slashTouches) {
                    if (!board->wouldFormLoop(adj.cell, SLASH)) {
                        board->placeValue(adj.cell, SLASH);
                        madeProgress = true;
                    }
                } else {
                    if (!board->wouldFormLoop(adj.cell, BACKSLASH)) {
                        board->placeValue(adj.cell, BACKSLASH);
                        madeProgress = true;
                    }
                }
            }
        }
    }

    return madeProgress;
}

// ruleLoopAvoidance2: Detect when finishing a 2 would force a loop.
bool ruleLoopAvoidance2(Board* board) {
    bool madeProgress = false;

    for (Vertex* vertex : board->getCluedVertices()) {
        if (vertex->clue != 2) {
            continue;
        }

        auto adjacent = board->getAdjacentCellsForVertex(vertex);
        int currentTouches = 0;
        std::vector<AdjacentCellInfo> unknownCells;

        for (auto& adj : adjacent) {
            if (adj.cell->value == UNKNOWN) {
                unknownCells.push_back(adj);
            } else if (adj.cell->value == SLASH && adj.slashTouches) {
                currentTouches++;
            } else if (adj.cell->value == BACKSLASH && adj.backslashTouches) {
                currentTouches++;
            }
        }

        if (currentTouches != 0 || unknownCells.size() != 2) {
            continue;
        }

        // Both unknowns must touch
        Cell* cell1 = unknownCells[0].cell;
        bool slash1 = unknownCells[0].slashTouches;
        Cell* cell2 = unknownCells[1].cell;
        bool slash2 = unknownCells[1].slashTouches;

        int val1 = slash1 ? SLASH : BACKSLASH;
        int val2 = slash2 ? SLASH : BACKSLASH;

        // Save state and try
        auto state = board->saveState();

        if (board->wouldFormLoop(cell1, val1)) {
            board->restoreState(state);
            continue;
        }

        board->placeValue(cell1, val1);

        if (board->wouldFormLoop(cell2, val2)) {
            // Would form loop - contradiction
            board->restoreState(state);
            continue;
        }

        board->restoreState(state);
    }

    return madeProgress;
}

// ruleVPatternWithThree: V pattern with 3 clue detection.
bool ruleVPatternWithThree(Board* board) {
    bool madeProgress = false;

    for (int y = 0; y < board->height; y++) {
        for (int x = 0; x < board->width - 1; x++) {
            Cell* cellLeft = board->getCell(x, y);
            Cell* cellRight = board->getCell(x + 1, y);

            if (!cellLeft || !cellRight) {
                continue;
            }

            // Check for \/ pattern (V pointing down)
            if (cellLeft->value == BACKSLASH && cellRight->value == SLASH) {
                Vertex* vertexAbove = board->getVertex(x + 1, y);
                if (vertexAbove && vertexAbove->hasClue && vertexAbove->clue == 3) {
                    auto [current, unknown] = board->countTouches(vertexAbove);
                    if (current == 2 && unknown > 0) {
                        for (auto& adj : board->getAdjacentCellsForVertex(vertexAbove)) {
                            if (adj.cell->value != UNKNOWN || adj.cell->y >= y) {
                                continue;
                            }
                            if (adj.slashTouches) {
                                if (!board->wouldFormLoop(adj.cell, SLASH)) {
                                    board->placeValue(adj.cell, SLASH);
                                    madeProgress = true;
                                }
                            } else {
                                if (!board->wouldFormLoop(adj.cell, BACKSLASH)) {
                                    board->placeValue(adj.cell, BACKSLASH);
                                    madeProgress = true;
                                }
                            }
                        }
                    }
                }
            }

            // Check for /\ pattern (V pointing up)
            if (cellLeft->value == SLASH && cellRight->value == BACKSLASH) {
                Vertex* vertexBelow = board->getVertex(x + 1, y + 1);
                if (vertexBelow && vertexBelow->hasClue && vertexBelow->clue == 3) {
                    auto [current, unknown] = board->countTouches(vertexBelow);
                    if (current == 2 && unknown > 0) {
                        for (auto& adj : board->getAdjacentCellsForVertex(vertexBelow)) {
                            if (adj.cell->value != UNKNOWN || adj.cell->y <= y) {
                                continue;
                            }
                            if (adj.slashTouches) {
                                if (!board->wouldFormLoop(adj.cell, SLASH)) {
                                    board->placeValue(adj.cell, SLASH);
                                    madeProgress = true;
                                }
                            } else {
                                if (!board->wouldFormLoop(adj.cell, BACKSLASH)) {
                                    board->placeValue(adj.cell, BACKSLASH);
                                    madeProgress = true;
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    return madeProgress;
}

// ruleAdjacentOnes: Adjacent 1-1 pattern constraints.
bool ruleAdjacentOnes(Board* board) {
    bool madeProgress = false;

    for (Vertex* vertex : board->getCluedVertices()) {
        if (vertex->clue != 1) {
            continue;
        }

        int vx = vertex->vx;
        int vy = vertex->vy;
        auto [current, _] = board->countTouches(vertex);

        if (current == 1) {
            // Check adjacent 1s and mark shared cells as avoiders
            int directions[][2] = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};
            for (auto& dir : directions) {
                Vertex* neighbor = board->getVertex(vx + dir[0], vy + dir[1]);
                if (!neighbor || !neighbor->hasClue || neighbor->clue != 1) {
                    continue;
                }

                auto neighborAdj = board->getAdjacentCellsForVertex(neighbor);
                std::set<Cell*> neighborCells;
                for (auto& n : neighborAdj) {
                    neighborCells.insert(n.cell);
                }

                for (auto& adj : board->getAdjacentCellsForVertex(vertex)) {
                    if (adj.cell->value != UNKNOWN) {
                        continue;
                    }
                    if (neighborCells.count(adj.cell)) {
                        // Shared cell - must avoid this vertex
                        if (adj.slashTouches) {
                            if (!board->wouldFormLoop(adj.cell, BACKSLASH)) {
                                board->placeValue(adj.cell, BACKSLASH);
                                madeProgress = true;
                            }
                        } else {
                            if (!board->wouldFormLoop(adj.cell, SLASH)) {
                                board->placeValue(adj.cell, SLASH);
                                madeProgress = true;
                            }
                        }
                    }
                }
            }
        }
    }

    return madeProgress;
}

// ruleAdjacentThrees: Adjacent 3-3 pattern constraints.
bool ruleAdjacentThrees(Board* board) {
    bool madeProgress = false;

    for (Vertex* vertex : board->getCluedVertices()) {
        if (vertex->clue != 3) {
            continue;
        }

        int vx = vertex->vx;
        int vy = vertex->vy;
        auto [current, _] = board->countTouches(vertex);

        int directions[][2] = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};
        for (auto& dir : directions) {
            Vertex* neighbor = board->getVertex(vx + dir[0], vy + dir[1]);
            if (!neighbor || !neighbor->hasClue || neighbor->clue != 3) {
                continue;
            }

            auto myAdj = board->getAdjacentCellsForVertex(vertex);
            auto neighborAdj = board->getAdjacentCellsForVertex(neighbor);
            std::set<Cell*> neighborCells;
            for (auto& n : neighborAdj) {
                neighborCells.insert(n.cell);
            }

            std::vector<AdjacentCellInfo> sharedCells, unsharedCells;
            for (auto& adj : myAdj) {
                if (neighborCells.count(adj.cell)) {
                    sharedCells.push_back(adj);
                } else {
                    unsharedCells.push_back(adj);
                }
            }

            std::vector<AdjacentCellInfo> unsharedUnknown;
            for (auto& adj : unsharedCells) {
                if (adj.cell->value == UNKNOWN) {
                    unsharedUnknown.push_back(adj);
                }
            }

            if (current + (int)unsharedUnknown.size() + (int)sharedCells.size() == 3 && !unsharedUnknown.empty()) {
                for (auto& adj : unsharedUnknown) {
                    if (adj.slashTouches) {
                        if (!board->wouldFormLoop(adj.cell, SLASH)) {
                            board->placeValue(adj.cell, SLASH);
                            madeProgress = true;
                        }
                    } else {
                        if (!board->wouldFormLoop(adj.cell, BACKSLASH)) {
                            board->placeValue(adj.cell, BACKSLASH);
                            madeProgress = true;
                        }
                    }
                }
            }
        }
    }

    return madeProgress;
}

// ruleDeadEndAvoidance: Prevent creating isolated regions.
bool ruleDeadEndAvoidance(Board* board) {
    bool madeProgress = false;

    for (Cell* cell : board->getUnknownCells()) {
        int x = cell->x;
        int y = cell->y;

        bool fSlash = false;
        bool fBack = false;

        // Check backslash: connects (x,y) to (x+1,y+1)
        int tlExits = board->getVertexGroupExits(x, y);
        int brExits = board->getVertexGroupExits(x + 1, y + 1);
        bool tlBorder = board->getVertexGroupBorder(x, y);
        bool brBorder = board->getVertexGroupBorder(x + 1, y + 1);

        if (!tlBorder && !brBorder && tlExits <= 1 && brExits <= 1) {
            fSlash = true;
        }

        // Check slash: connects (x+1,y) to (x,y+1)
        int trExits = board->getVertexGroupExits(x + 1, y);
        int blExits = board->getVertexGroupExits(x, y + 1);
        bool trBorder = board->getVertexGroupBorder(x + 1, y);
        bool blBorder = board->getVertexGroupBorder(x, y + 1);

        if (!trBorder && !blBorder && trExits <= 1 && blExits <= 1) {
            fBack = true;
        }

        // fSlash means "backslash is forbidden, force slash"
        // fBack means "slash is forbidden, force backslash"
        if (fSlash && !fBack) {
            if (!board->wouldFormLoop(cell, SLASH)) {
                board->placeValue(cell, SLASH);
                madeProgress = true;
            }
        } else if (fBack && !fSlash) {
            if (!board->wouldFormLoop(cell, BACKSLASH)) {
                board->placeValue(cell, BACKSLASH);
                madeProgress = true;
            }
        }
    }

    return madeProgress;
}

// ruleEquivalenceClasses: Track and propagate cell equivalences.
bool ruleEquivalenceClasses(Board* board) {
    bool madeProgress = false;

    // First pass: establish equivalences from clues
    for (Vertex* vertex : board->getCluedVertices()) {
        auto adjacent = board->getAdjacentCellsForVertex(vertex);
        int currentTouches = 0;
        std::vector<AdjacentCellInfo> unknownCells;

        for (auto& adj : adjacent) {
            if (adj.cell->value == UNKNOWN) {
                unknownCells.push_back(adj);
            } else if (adj.cell->value == SLASH && adj.slashTouches) {
                currentTouches++;
            } else if (adj.cell->value == BACKSLASH && adj.backslashTouches) {
                currentTouches++;
            }
        }

        int needed = vertex->clue - currentTouches;

        if (needed == 1 && unknownCells.size() == 2) {
            Cell* cell1 = unknownCells[0].cell;
            Cell* cell2 = unknownCells[1].cell;

            int dx = std::abs(cell1->x - cell2->x);
            int dy = std::abs(cell1->y - cell2->y);
            bool cellsAreAdjacent = (dx == 1 && dy == 0) || (dx == 0 && dy == 1);

            if (cellsAreAdjacent) {
                if (board->markCellsEquivalent(cell1, cell2)) {
                    madeProgress = true;
                }
            }
        }
    }

    // Second pass: propagate known values
    for (Cell* cell : board->getUnknownCells()) {
        int equivValue = board->getEquivalenceClassValue(cell);

        if (equivValue != UNKNOWN) {
            if (!board->wouldFormLoop(cell, equivValue)) {
                board->placeValue(cell, equivValue);
                madeProgress = true;
            } else {
                int otherValue = (equivValue == BACKSLASH) ? SLASH : BACKSLASH;
                if (!board->wouldFormLoop(cell, otherValue)) {
                    board->placeValue(cell, otherValue);
                    madeProgress = true;
                }
            }
        }
    }

    return madeProgress;
}

// ruleVBitmapPropagation: Track and propagate v-shape possibilities.
bool ruleVBitmapPropagation(Board* board) {
    bool madeProgress = false;
    int w = board->width;
    int h = board->height;

    // Local vbitmap for this iteration
    std::vector<std::vector<int>> vbitmap(h, std::vector<int>(w, 0xF));

    bool changed = true;
    while (changed) {
        changed = false;

        // Apply constraints from known cell values
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                Cell* cell = board->getCell(x, y);
                if (cell->value == UNKNOWN) {
                    continue;
                }
                int s = cell->value;
                int old = vbitmap[y][x];
                if (s == SLASH) {
                    vbitmap[y][x] &= ~0x5;
                    if (x > 0 && (vbitmap[y][x - 1] & 0x2)) {
                        vbitmap[y][x - 1] &= ~0x2;
                        changed = true;
                    }
                    if (y > 0 && (vbitmap[y - 1][x] & 0x8)) {
                        vbitmap[y - 1][x] &= ~0x8;
                        changed = true;
                    }
                } else {
                    vbitmap[y][x] &= ~0xA;
                    if (x > 0 && (vbitmap[y][x - 1] & 0x1)) {
                        vbitmap[y][x - 1] &= ~0x1;
                        changed = true;
                    }
                    if (y > 0 && (vbitmap[y - 1][x] & 0x4)) {
                        vbitmap[y - 1][x] &= ~0x4;
                        changed = true;
                    }
                }
                if (vbitmap[y][x] != old) {
                    changed = true;
                }
            }
        }

        // Apply constraints from clues
        for (int vy = 1; vy < h; vy++) {
            for (int vx = 1; vx < w; vx++) {
                Vertex* vertex = board->getVertex(vx, vy);
                if (!vertex || !vertex->hasClue) {
                    continue;
                }
                int c = vertex->clue;

                if (c == 1) {
                    int old1 = vbitmap[vy - 1][vx - 1];
                    int old2 = vbitmap[vy][vx - 1];
                    int old3 = vbitmap[vy - 1][vx];
                    vbitmap[vy - 1][vx - 1] &= ~0x5;
                    if (vy < h) {
                        vbitmap[vy][vx - 1] &= ~0x2;
                    }
                    if (vx < w) {
                        vbitmap[vy - 1][vx] &= ~0x8;
                    }
                    if (vbitmap[vy - 1][vx - 1] != old1 || vbitmap[vy][vx - 1] != old2 || vbitmap[vy - 1][vx] != old3) {
                        changed = true;
                    }
                } else if (c == 3) {
                    int old1 = vbitmap[vy - 1][vx - 1];
                    int old2 = vbitmap[vy][vx - 1];
                    int old3 = vbitmap[vy - 1][vx];
                    vbitmap[vy - 1][vx - 1] &= ~0xA;
                    if (vy < h) {
                        vbitmap[vy][vx - 1] &= ~0x1;
                    }
                    if (vx < w) {
                        vbitmap[vy - 1][vx] &= ~0x4;
                    }
                    if (vbitmap[vy - 1][vx - 1] != old1 || vbitmap[vy][vx - 1] != old2 || vbitmap[vy - 1][vx] != old3) {
                        changed = true;
                    }
                } else if (c == 2) {
                    int oldTL = vbitmap[vy - 1][vx - 1];
                    int oldBL = vbitmap[vy][vx - 1];
                    int oldTR = vbitmap[vy - 1][vx];

                    if (vy < h) {
                        int top = vbitmap[vy - 1][vx - 1] & 0x3;
                        int bot = vbitmap[vy][vx - 1] & 0x3;
                        vbitmap[vy - 1][vx - 1] &= ~(0x3 ^ bot);
                        vbitmap[vy][vx - 1] &= ~(0x3 ^ top);
                    }

                    if (vx < w) {
                        int left = vbitmap[vy - 1][vx - 1] & 0xC;
                        int right = vbitmap[vy - 1][vx] & 0xC;
                        vbitmap[vy - 1][vx - 1] &= ~(0xC ^ right);
                        vbitmap[vy - 1][vx] &= ~(0xC ^ left);
                    }

                    if (vbitmap[vy - 1][vx - 1] != oldTL || vbitmap[vy][vx - 1] != oldBL || vbitmap[vy - 1][vx] != oldTR) {
                        changed = true;
                    }
                }
            }
        }

        // Mark equivalent cells
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                Cell* cell = board->getCell(x, y);

                if (x + 1 < w) {
                    Cell* rightCell = board->getCell(x + 1, y);
                    if ((vbitmap[y][x] & 0x3) == 0) {
                        if (board->markCellsEquivalent(cell, rightCell)) {
                            madeProgress = true;
                            changed = true;
                        }
                    }
                }

                if (y + 1 < h) {
                    Cell* belowCell = board->getCell(x, y + 1);
                    if ((vbitmap[y][x] & 0xC) == 0) {
                        if (board->markCellsEquivalent(cell, belowCell)) {
                            madeProgress = true;
                            changed = true;
                        }
                    }
                }
            }
        }
    }

    return madeProgress;
}

// ruleSimonUnified: Unified rule mimicking Simon Tatham's solver.
bool ruleSimonUnified(Board* board) {
    int w = board->width;
    int h = board->height;
    int W = w + 1;
    int H = h + 1;
    bool madeProgress = false;
    bool doneSomething = true;

    while (doneSomething) {
        doneSomething = false;

        // Phase 1: Clue completion with equivalence tracking
        for (int vy = 0; vy < H; vy++) {
            for (int vx = 0; vx < W; vx++) {
                Vertex* vertex = board->getVertex(vx, vy);
                if (!vertex || !vertex->hasClue) {
                    continue;
                }

                int c = vertex->clue;

                // Build list of neighbors
                struct NeighborInfo {
                    Cell* cell;
                    int slashType;
                };
                std::vector<NeighborInfo> neighbours;

                if (vx > 0 && vy > 0) {
                    Cell* cell = board->getCell(vx - 1, vy - 1);
                    neighbours.push_back({cell, BACKSLASH});
                }
                if (vx > 0 && vy < h) {
                    Cell* cell = board->getCell(vx - 1, vy);
                    neighbours.push_back({cell, SLASH});
                }
                if (vx < w && vy < h) {
                    Cell* cell = board->getCell(vx, vy);
                    neighbours.push_back({cell, BACKSLASH});
                }
                if (vx < w && vy > 0) {
                    Cell* cell = board->getCell(vx, vy - 1);
                    neighbours.push_back({cell, SLASH});
                }

                if (neighbours.empty()) {
                    continue;
                }

                int nneighbours = (int)neighbours.size();
                int nu = 0;
                int nl = c;

                Cell* lastCell = neighbours[nneighbours - 1].cell;
                int lastEq = -1;
                if (lastCell->value == UNKNOWN) {
                    lastEq = board->getCellEquivRoot(lastCell);
                }

                int meq = -1;
                Cell* mj1 = nullptr;
                Cell* mj2 = nullptr;

                for (int i = 0; i < nneighbours; i++) {
                    Cell* cell = neighbours[i].cell;
                    int slashType = neighbours[i].slashType;
                    if (cell->value == UNKNOWN) {
                        nu++;
                        if (meq < 0) {
                            int eq = board->getCellEquivRoot(cell);
                            if (eq == lastEq && lastCell != cell) {
                                meq = eq;
                                mj1 = lastCell;
                                mj2 = cell;
                                nl--;
                                nu -= 2;
                            } else {
                                lastEq = eq;
                            }
                        }
                    } else {
                        lastEq = -1;
                        if (cell->value == slashType) {
                            nl--;
                        }
                    }
                    lastCell = cell;
                }

                if (nl < 0 || nl > nu) {
                    continue;
                }

                if (nu > 0 && (nl == 0 || nl == nu)) {
                    for (auto& n : neighbours) {
                        if (n.cell == mj1 || n.cell == mj2) {
                            continue;
                        }
                        if (n.cell->value == UNKNOWN) {
                            int value;
                            if (nl > 0) {
                                value = n.slashType;
                            } else {
                                value = (n.slashType == SLASH) ? BACKSLASH : SLASH;
                            }

                            if (!board->wouldFormLoop(n.cell, value)) {
                                board->placeValue(n.cell, value);
                                doneSomething = true;
                                madeProgress = true;
                            }
                        }
                    }
                } else if (nu == 2 && nl == 1) {
                    int lastIdx = -1;
                    for (int i = 0; i < nneighbours; i++) {
                        Cell* cell = neighbours[i].cell;
                        if (cell->value == UNKNOWN && cell != mj1 && cell != mj2) {
                            if (lastIdx < 0) {
                                lastIdx = i;
                            } else if (lastIdx == i - 1 || (lastIdx == 0 && i == nneighbours - 1)) {
                                Cell* cell1 = neighbours[lastIdx].cell;
                                Cell* cell2 = neighbours[i].cell;
                                if (board->markCellsEquivalent(cell1, cell2)) {
                                    doneSomething = true;
                                    madeProgress = true;
                                }
                                break;
                            }
                        }
                    }
                }
            }
        }

        if (doneSomething) {
            continue;
        }

        // Phase 2: Loop avoidance, dead-end avoidance, equivalence filling
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                Cell* cell = board->getCell(x, y);
                if (cell->value != UNKNOWN) {
                    continue;
                }

                bool fs = false;
                bool bs = false;

                int v = board->getEquivalenceClassValue(cell);
                if (v == SLASH) {
                    fs = true;
                } else if (v == BACKSLASH) {
                    bs = true;
                }

                // Check backslash loop
                int c1 = board->getVertexRoot(x, y);
                int c2 = board->getVertexRoot(x + 1, y + 1);
                if (c1 == c2) {
                    fs = true;
                }

                // Dead-end avoidance for backslash
                if (!fs) {
                    if (!board->getVertexGroupBorder(x, y) &&
                        !board->getVertexGroupBorder(x + 1, y + 1) &&
                        board->getVertexGroupExits(x, y) <= 1 &&
                        board->getVertexGroupExits(x + 1, y + 1) <= 1) {
                        fs = true;
                    }
                }

                // Check slash loop
                c1 = board->getVertexRoot(x + 1, y);
                c2 = board->getVertexRoot(x, y + 1);
                if (c1 == c2) {
                    bs = true;
                }

                // Dead-end avoidance for slash
                if (!bs) {
                    if (!board->getVertexGroupBorder(x + 1, y) &&
                        !board->getVertexGroupBorder(x, y + 1) &&
                        board->getVertexGroupExits(x + 1, y) <= 1 &&
                        board->getVertexGroupExits(x, y + 1) <= 1) {
                        bs = true;
                    }
                }

                if (fs && bs) {
                    continue;
                }

                if (fs) {
                    board->placeValue(cell, SLASH);
                    doneSomething = true;
                    madeProgress = true;
                } else if (bs) {
                    board->placeValue(cell, BACKSLASH);
                    doneSomething = true;
                    madeProgress = true;
                }
            }
        }

        if (doneSomething) {
            continue;
        }

        // Phase 3: V-bitmap propagation
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                Cell* cell = board->getCell(x, y);
                int s = cell->value;

                if (s != UNKNOWN) {
                    if (x > 0) {
                        Cell* leftCell = board->getCell(x - 1, y);
                        int bits = (s == SLASH) ? 0x2 : 0x1;
                        if (board->vbitmapClear(leftCell, bits)) {
                            doneSomething = true;
                            madeProgress = true;
                        }
                    }

                    if (x + 1 < w) {
                        int bits = (s == SLASH) ? 0x1 : 0x2;
                        if (board->vbitmapClear(cell, bits)) {
                            doneSomething = true;
                            madeProgress = true;
                        }
                    }

                    if (y > 0) {
                        Cell* aboveCell = board->getCell(x, y - 1);
                        int bits = (s == SLASH) ? 0x8 : 0x4;
                        if (board->vbitmapClear(aboveCell, bits)) {
                            doneSomething = true;
                            madeProgress = true;
                        }
                    }

                    if (y + 1 < h) {
                        int bits = (s == SLASH) ? 0x4 : 0x8;
                        if (board->vbitmapClear(cell, bits)) {
                            doneSomething = true;
                            madeProgress = true;
                        }
                    }
                }

                if (x + 1 < w && (board->vbitmapGet(cell) & 0x3) == 0) {
                    Cell* rightCell = board->getCell(x + 1, y);
                    if (board->markCellsEquivalent(cell, rightCell)) {
                        doneSomething = true;
                        madeProgress = true;
                    }
                }

                if (y + 1 < h && (board->vbitmapGet(cell) & 0xC) == 0) {
                    Cell* belowCell = board->getCell(x, y + 1);
                    if (board->markCellsEquivalent(cell, belowCell)) {
                        doneSomething = true;
                        madeProgress = true;
                    }
                }
            }
        }

        // V-bitmap constraints from interior clues
        for (int vy = 1; vy < H - 1; vy++) {
            for (int vx = 1; vx < W - 1; vx++) {
                Vertex* vertex = board->getVertex(vx, vy);
                if (!vertex || !vertex->hasClue) {
                    continue;
                }

                int c = vertex->clue;
                Cell* tl = board->getCell(vx - 1, vy - 1);
                Cell* bl = board->getCell(vx - 1, vy);
                Cell* tr = board->getCell(vx, vy - 1);

                if (c == 1) {
                    if (board->vbitmapClear(tl, 0x5)) {
                        doneSomething = true;
                        madeProgress = true;
                    }
                    if (board->vbitmapClear(bl, 0x2)) {
                        doneSomething = true;
                        madeProgress = true;
                    }
                    if (board->vbitmapClear(tr, 0x8)) {
                        doneSomething = true;
                        madeProgress = true;
                    }
                } else if (c == 3) {
                    if (board->vbitmapClear(tl, 0xA)) {
                        doneSomething = true;
                        madeProgress = true;
                    }
                    if (board->vbitmapClear(bl, 0x1)) {
                        doneSomething = true;
                        madeProgress = true;
                    }
                    if (board->vbitmapClear(tr, 0x4)) {
                        doneSomething = true;
                        madeProgress = true;
                    }
                } else if (c == 2) {
                    int tlH = board->vbitmapGet(tl) & 0x3;
                    int blH = board->vbitmapGet(bl) & 0x3;
                    if (board->vbitmapClear(tl, 0x3 ^ blH)) {
                        doneSomething = true;
                        madeProgress = true;
                    }
                    if (board->vbitmapClear(bl, 0x3 ^ tlH)) {
                        doneSomething = true;
                        madeProgress = true;
                    }

                    int tlV = board->vbitmapGet(tl) & 0xC;
                    int trV = board->vbitmapGet(tr) & 0xC;
                    if (board->vbitmapClear(tl, 0xC ^ trV)) {
                        doneSomething = true;
                        madeProgress = true;
                    }
                    if (board->vbitmapClear(tr, 0xC ^ tlV)) {
                        doneSomething = true;
                        madeProgress = true;
                    }
                }
            }
        }
    }

    return madeProgress;
}
