#ifndef BOARD_H
#define BOARD_H

#include <string>
#include <vector>
#include <memory>

// Cell values
constexpr int UNKNOWN = 0;
constexpr int SLASH = 1;     // /  - connects bottom-left to top-right
constexpr int BACKSLASH = 2; // \  - connects top-left to bottom-right

// Vertex represents a corner point in a Slants puzzle
struct Vertex {
    int vx, vy;
    int clue;      // -1 means no clue, 0-4 are valid clues
    bool hasClue;

    Vertex(int x, int y, int c) : vx(x), vy(y), clue(c), hasClue(c >= 0) {}
};

// Cell represents a single cell in a Slants puzzle
struct Cell {
    int x, y;
    int value;  // UNKNOWN, SLASH, or BACKSLASH

    Cell(int px, int py) : x(px), y(py), value(UNKNOWN) {}
};

// AdjacentCellInfo contains info about a cell adjacent to a vertex
struct AdjacentCellInfo {
    Cell* cell;
    bool slashTouches;
    bool backslashTouches;
};

// BoardState holds a snapshot for backtracking
struct BoardState {
    std::vector<int> cellValues;
    std::vector<int> parent;
    std::vector<int> rank;
    std::vector<int> equivParent;
    std::vector<int> equivRank;
    std::vector<int> slashval;
    std::vector<int> vbitmap;
    std::vector<int> exits;
    std::vector<bool> border;
};

class Board {
public:
    int width, height;
    std::vector<std::unique_ptr<Cell>> cells;
    std::vector<std::unique_ptr<Vertex>> vertices;

    // Union-find for loop detection (vertex connectivity)
    std::vector<int> parent;
    std::vector<int> rank;

    // Equivalence class tracking for cells
    std::vector<int> equivParent;
    std::vector<int> equivRank;
    std::vector<int> slashval;

    // V-bitmap tracking
    std::vector<int> vbitmap;

    // Exits and border tracking
    std::vector<int> exits;
    std::vector<bool> border;

    Board(int w, int h, const std::string& givensString);

    // Cell access
    Cell* getCell(int x, int y);
    Vertex* getVertex(int vx, int vy);
    std::vector<Vertex*> getCluedVertices();
    std::vector<Cell*> getUnknownCells();

    // Adjacent cell info
    std::vector<AdjacentCellInfo> getAdjacentCellsForVertex(Vertex* vertex);
    std::pair<int, int> countTouches(Vertex* vertex);

    // Cell corners
    void getCellCorners(Cell* cell, Vertex** tl, Vertex** tr, Vertex** bl, Vertex** br);

    // Loop detection
    bool wouldFormLoop(Cell* cell, int value);
    bool placeValue(Cell* cell, int value);

    // Board state
    bool isSolved();
    bool isValid();
    bool isValidSolution();
    std::string toSolutionString();

    // State save/restore for backtracking
    BoardState saveState();
    void restoreState(const BoardState& state);

    // Equivalence classes
    int getCellEquivRoot(Cell* cell);
    bool markCellsEquivalent(Cell* cell1, Cell* cell2);
    int getEquivalenceClassValue(Cell* cell);

    // V-bitmap
    int vbitmapGet(Cell* cell);
    bool vbitmapClear(Cell* cell, int bits);

    // Exits/border
    int getVertexRoot(int vx, int vy);
    int getVertexGroupExits(int vx, int vy);
    bool getVertexGroupBorder(int vx, int vy);

private:
    std::vector<int> decodeGivens(const std::string& givensString);
    void initUnionFind();
    void initEquivalence();
    void initVBitmap();
    void initExitsBorder();

    int find(int x);
    bool unite(int x, int y);
    int vertexIndex(int vx, int vy);
    int cellIndex(Cell* cell);
    int equivFind(int x);
    void decrExits(int vx, int vy);
};

#endif // BOARD_H
