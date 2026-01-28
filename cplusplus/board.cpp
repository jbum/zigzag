#include "board.h"
#include <stdexcept>

Board::Board(int w, int h, const std::string& givensString)
    : width(w), height(h) {

    // Initialize cells
    cells.reserve(width * height);
    for (int y = 0; y < height; y++) {
        for (int x = 0; x < width; x++) {
            cells.push_back(std::make_unique<Cell>(x, y));
        }
    }

    // Decode givens and initialize vertices
    auto decodedClues = decodeGivens(givensString);
    int expectedVertices = (width + 1) * (height + 1);

    if ((int)decodedClues.size() != expectedVertices) {
        throw std::runtime_error("Givens decode mismatch");
    }

    vertices.reserve(expectedVertices);
    for (int i = 0; i < expectedVertices; i++) {
        int vx = i % (width + 1);
        int vy = i / (width + 1);
        vertices.push_back(std::make_unique<Vertex>(vx, vy, decodedClues[i]));
    }

    initUnionFind();
    initEquivalence();
    initVBitmap();
    initExitsBorder();
}

std::vector<int> Board::decodeGivens(const std::string& givensString) {
    std::vector<int> result;
    for (char c : givensString) {
        if (c >= '0' && c <= '4') {
            result.push_back(c - '0');
        } else if (c >= 'a' && c <= 'z') {
            int runLength = c - 'a' + 1;
            for (int i = 0; i < runLength; i++) {
                result.push_back(-1);  // -1 means no clue
            }
        }
    }
    return result;
}

void Board::initUnionFind() {
    int numVertices = (width + 1) * (height + 1);
    parent.resize(numVertices);
    rank.resize(numVertices, 0);
    for (int i = 0; i < numVertices; i++) {
        parent[i] = i;
    }
}

void Board::initEquivalence() {
    int numCells = width * height;
    equivParent.resize(numCells);
    equivRank.resize(numCells, 0);
    slashval.resize(numCells, 0);
    for (int i = 0; i < numCells; i++) {
        equivParent[i] = i;
    }
}

void Board::initVBitmap() {
    int numCells = width * height;
    vbitmap.resize(numCells, 0xF);  // All v-shapes initially possible
}

void Board::initExitsBorder() {
    int W = width + 1;
    int H = height + 1;
    int numVertices = W * H;

    exits.resize(numVertices);
    border.resize(numVertices, false);

    for (int vy = 0; vy < H; vy++) {
        for (int vx = 0; vx < W; vx++) {
            int idx = vy * W + vx;
            // Border if on edge
            if (vy == 0 || vy == H - 1 || vx == 0 || vx == W - 1) {
                border[idx] = true;
            }
            // Exits = clue value, or 4 if no clue
            Vertex* vertex = getVertex(vx, vy);
            if (vertex->hasClue) {
                exits[idx] = vertex->clue;
            } else {
                exits[idx] = 4;
            }
        }
    }
}

int Board::find(int x) {
    if (parent[x] != x) {
        parent[x] = find(parent[x]);
    }
    return parent[x];
}

bool Board::unite(int x, int y) {
    int rx = find(x);
    int ry = find(y);
    if (rx == ry) {
        return false;  // Already connected - would form a loop
    }

    // Merge exits and border info
    int mergedExits = exits[rx] + exits[ry] - 2;
    bool mergedBorder = border[rx] || border[ry];

    if (rank[rx] < rank[ry]) {
        std::swap(rx, ry);
    }
    parent[ry] = rx;
    if (rank[rx] == rank[ry]) {
        rank[rx]++;
    }

    exits[rx] = mergedExits;
    border[rx] = mergedBorder;

    return true;
}

int Board::vertexIndex(int vx, int vy) {
    return vy * (width + 1) + vx;
}

int Board::cellIndex(Cell* cell) {
    return cell->y * width + cell->x;
}

int Board::equivFind(int x) {
    if (equivParent[x] != x) {
        equivParent[x] = equivFind(equivParent[x]);
    }
    return equivParent[x];
}

Cell* Board::getCell(int x, int y) {
    if (x >= 0 && x < width && y >= 0 && y < height) {
        return cells[y * width + x].get();
    }
    return nullptr;
}

Vertex* Board::getVertex(int vx, int vy) {
    if (vx >= 0 && vx <= width && vy >= 0 && vy <= height) {
        return vertices[vy * (width + 1) + vx].get();
    }
    return nullptr;
}

std::vector<Vertex*> Board::getCluedVertices() {
    std::vector<Vertex*> result;
    for (auto& v : vertices) {
        if (v->hasClue) {
            result.push_back(v.get());
        }
    }
    return result;
}

std::vector<Cell*> Board::getUnknownCells() {
    std::vector<Cell*> result;
    for (auto& c : cells) {
        if (c->value == UNKNOWN) {
            result.push_back(c.get());
        }
    }
    return result;
}

std::vector<AdjacentCellInfo> Board::getAdjacentCellsForVertex(Vertex* vertex) {
    int vx = vertex->vx;
    int vy = vertex->vy;
    std::vector<AdjacentCellInfo> adjacent;

    // Top-left cell (vertex is its bottom-right corner)
    if (Cell* cell = getCell(vx - 1, vy - 1)) {
        adjacent.push_back({cell, false, true});
    }
    // Top-right cell (vertex is its bottom-left corner)
    if (Cell* cell = getCell(vx, vy - 1)) {
        adjacent.push_back({cell, true, false});
    }
    // Bottom-left cell (vertex is its top-right corner)
    if (Cell* cell = getCell(vx - 1, vy)) {
        adjacent.push_back({cell, true, false});
    }
    // Bottom-right cell (vertex is its top-left corner)
    if (Cell* cell = getCell(vx, vy)) {
        adjacent.push_back({cell, false, true});
    }

    return adjacent;
}

std::pair<int, int> Board::countTouches(Vertex* vertex) {
    int current = 0;
    int unknown = 0;

    for (auto& adj : getAdjacentCellsForVertex(vertex)) {
        if (adj.cell->value == UNKNOWN) {
            unknown++;
        } else if (adj.cell->value == SLASH && adj.slashTouches) {
            current++;
        } else if (adj.cell->value == BACKSLASH && adj.backslashTouches) {
            current++;
        }
    }

    return {current, unknown};
}

void Board::getCellCorners(Cell* cell, Vertex** tl, Vertex** tr, Vertex** bl, Vertex** br) {
    int x = cell->x;
    int y = cell->y;
    *tl = getVertex(x, y);
    *tr = getVertex(x + 1, y);
    *bl = getVertex(x, y + 1);
    *br = getVertex(x + 1, y + 1);
}

bool Board::wouldFormLoop(Cell* cell, int value) {
    int x = cell->x;
    int y = cell->y;
    int v1, v2;

    if (value == SLASH) {
        v1 = vertexIndex(x, y + 1);
        v2 = vertexIndex(x + 1, y);
    } else {
        v1 = vertexIndex(x, y);
        v2 = vertexIndex(x + 1, y + 1);
    }

    return find(v1) == find(v2);
}

bool Board::placeValue(Cell* cell, int value) {
    if (cell->value != UNKNOWN) {
        return true;
    }

    int x = cell->x;
    int y = cell->y;
    int v1, v2;
    int nonV1X, nonV1Y, nonV2X, nonV2Y;

    if (value == SLASH) {
        v1 = vertexIndex(x, y + 1);
        v2 = vertexIndex(x + 1, y);
        nonV1X = x; nonV1Y = y;         // top-left
        nonV2X = x + 1; nonV2Y = y + 1; // bottom-right
    } else {
        v1 = vertexIndex(x, y);
        v2 = vertexIndex(x + 1, y + 1);
        nonV1X = x + 1; nonV1Y = y;     // top-right
        nonV2X = x; nonV2Y = y + 1;     // bottom-left
    }

    if (!unite(v1, v2)) {
        return false;  // Would form a loop
    }

    // Decrement exits for non-connected vertices
    decrExits(nonV1X, nonV1Y);
    decrExits(nonV2X, nonV2Y);

    cell->value = value;

    // Update slashval for this cell's equivalence class
    int idx = cellIndex(cell);
    int root = equivFind(idx);
    slashval[root] = value;

    return true;
}

void Board::decrExits(int vx, int vy) {
    Vertex* vertex = getVertex(vx, vy);
    if (vertex->hasClue) {
        return;  // Clued vertices have fixed exits
    }
    int idx = vertexIndex(vx, vy);
    int root = find(idx);
    exits[root]--;
}

bool Board::isSolved() {
    for (auto& cell : cells) {
        if (cell->value == UNKNOWN) {
            return false;
        }
    }
    return true;
}

bool Board::isValid() {
    for (auto& vertex : vertices) {
        if (vertex->hasClue) {
            auto [current, _] = countTouches(vertex.get());
            if (current > vertex->clue) {
                return false;
            }
        }
    }
    return true;
}

bool Board::isValidSolution() {
    if (!isSolved()) {
        return false;
    }
    for (auto& vertex : vertices) {
        if (vertex->hasClue) {
            auto [current, _] = countTouches(vertex.get());
            if (current != vertex->clue) {
                return false;
            }
        }
    }
    return true;
}

std::string Board::toSolutionString() {
    std::string result;
    result.reserve(cells.size());
    for (auto& cell : cells) {
        switch (cell->value) {
            case SLASH:
                result += '/';
                break;
            case BACKSLASH:
                result += '\\';
                break;
            default:
                result += '.';
                break;
        }
    }
    return result;
}

BoardState Board::saveState() {
    BoardState state;
    state.cellValues.resize(cells.size());
    for (size_t i = 0; i < cells.size(); i++) {
        state.cellValues[i] = cells[i]->value;
    }
    state.parent = parent;
    state.rank = rank;
    state.equivParent = equivParent;
    state.equivRank = equivRank;
    state.slashval = slashval;
    state.vbitmap = vbitmap;
    state.exits = exits;
    state.border = border;
    return state;
}

void Board::restoreState(const BoardState& state) {
    for (size_t i = 0; i < cells.size(); i++) {
        cells[i]->value = state.cellValues[i];
    }
    parent = state.parent;
    rank = state.rank;
    equivParent = state.equivParent;
    equivRank = state.equivRank;
    slashval = state.slashval;
    vbitmap = state.vbitmap;
    exits = state.exits;
    border = state.border;
}

int Board::getCellEquivRoot(Cell* cell) {
    int idx = cellIndex(cell);
    return equivFind(idx);
}

bool Board::markCellsEquivalent(Cell* cell1, Cell* cell2) {
    int idx1 = cellIndex(cell1);
    int idx2 = cellIndex(cell2);

    int r1 = equivFind(idx1);
    int r2 = equivFind(idx2);

    if (r1 == r2) {
        return false;  // Already equivalent
    }

    // Check for slashval conflict
    int sv1 = slashval[r1];
    int sv2 = slashval[r2];
    if (sv1 != 0 && sv2 != 0 && sv1 != sv2) {
        return false;  // Conflict
    }

    int mergedSV = sv1 ? sv1 : sv2;

    // Union by rank
    if (equivRank[r1] < equivRank[r2]) {
        std::swap(r1, r2);
    }
    equivParent[r2] = r1;
    if (equivRank[r1] == equivRank[r2]) {
        equivRank[r1]++;
    }

    slashval[r1] = mergedSV;

    return true;
}

int Board::getEquivalenceClassValue(Cell* cell) {
    int idx = cellIndex(cell);
    int root = equivFind(idx);
    return slashval[root];
}

int Board::vbitmapGet(Cell* cell) {
    int idx = cellIndex(cell);
    return vbitmap[idx];
}

bool Board::vbitmapClear(Cell* cell, int bits) {
    int idx = cellIndex(cell);
    int old = vbitmap[idx];
    int newVal = old & ~bits;
    if (newVal != old) {
        vbitmap[idx] = newVal;
        return true;
    }
    return false;
}

int Board::getVertexRoot(int vx, int vy) {
    int idx = vertexIndex(vx, vy);
    return find(idx);
}

int Board::getVertexGroupExits(int vx, int vy) {
    int root = getVertexRoot(vx, vy);
    return exits[root];
}

bool Board::getVertexGroupBorder(int vx, int vy) {
    int root = getVertexRoot(vx, vy);
    return border[root];
}
