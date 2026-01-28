CXX = clang++
CXXFLAGS = -std=c++17 -O2 -Wall -Wextra
TARGET = solve_puzzles
SRCS = main.cpp board.cpp rules.cpp solver.cpp
OBJS = $(SRCS:.cpp=.o)

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CXX) $(CXXFLAGS) -o $(TARGET) $(OBJS)

%.o: %.cpp
	$(CXX) $(CXXFLAGS) -c $< -o $@

clean:
	rm -f $(OBJS) $(TARGET)

# Dependencies
main.o: main.cpp solver.h
board.o: board.cpp board.h
rules.o: rules.cpp rules.h board.h
solver.o: solver.cpp solver.h board.h rules.h

.PHONY: all clean
