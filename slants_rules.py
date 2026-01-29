"""
Production rules for Slants (Gokigen Naname) puzzle solver.

Each rule function takes a Board and returns True if it made progress, False otherwise.
Rules should modify the board in place when they make progress.
"""

from slants_board import Board, UNKNOWN, SLASH, BACKSLASH


def rule_clue_finish_a(board):
    """
    If a clue has sufficient non-meets (avoiders), then fill in its meets.

    For a vertex with clue N:
    - Count current touches (diagonals already touching)
    - Count confirmed avoiders (cells with diagonal that doesn't touch)
    - If (4 - confirmed_avoiders) == clue, remaining unknowns must touch

    For corner/edge vertices, max_adjacent < 4.
    """
    made_progress = False

    for vertex in board.get_clued_vertices():
        adjacent = board.get_adjacent_cells_for_vertex(vertex)
        clue = vertex.clue

        current_touches = 0
        confirmed_avoiders = 0
        unknown_cells = []

        for cell, slash_touches, backslash_touches in adjacent:
            if cell.value == UNKNOWN:
                unknown_cells.append((cell, slash_touches, backslash_touches))
            elif cell.value == SLASH:
                if slash_touches:
                    current_touches += 1
                else:
                    confirmed_avoiders += 1
            else:  # BACKSLASH
                if backslash_touches:
                    current_touches += 1
                else:
                    confirmed_avoiders += 1

        # How many more touches do we need?
        needed_touches = clue - current_touches

        # If all unknowns must touch to reach the clue
        if needed_touches > 0 and needed_touches == len(unknown_cells):
            for cell, slash_touches, backslash_touches in unknown_cells:
                if slash_touches:
                    if not board.would_form_loop(cell, SLASH):
                        board.place_value(cell, SLASH)
                        made_progress = True
                else:  # backslash_touches
                    if not board.would_form_loop(cell, BACKSLASH):
                        board.place_value(cell, BACKSLASH)
                        made_progress = True

    return made_progress


def rule_clue_finish_b(board):
    """
    If a clue has sufficient meets (touches), then fill its avoiders.

    For a vertex with clue N:
    - If we already have N touches, remaining unknowns must avoid
    """
    made_progress = False

    for vertex in board.get_clued_vertices():
        adjacent = board.get_adjacent_cells_for_vertex(vertex)
        clue = vertex.clue

        current_touches = 0
        unknown_cells = []

        for cell, slash_touches, backslash_touches in adjacent:
            if cell.value == UNKNOWN:
                unknown_cells.append((cell, slash_touches, backslash_touches))
            elif cell.value == SLASH and slash_touches:
                current_touches += 1
            elif cell.value == BACKSLASH and backslash_touches:
                current_touches += 1

        # If we already have enough touches, remaining must avoid
        if current_touches == clue and unknown_cells:
            for cell, slash_touches, backslash_touches in unknown_cells:
                # Place the non-touching diagonal
                if slash_touches:
                    # Slash would touch, so place backslash to avoid
                    if not board.would_form_loop(cell, BACKSLASH):
                        board.place_value(cell, BACKSLASH)
                        made_progress = True
                else:
                    # Backslash would touch, so place slash to avoid
                    if not board.would_form_loop(cell, SLASH):
                        board.place_value(cell, SLASH)
                        made_progress = True

    return made_progress


def rule_no_loops(board):
    """
    If placing a slant in an unknown square creates a loop, place the counter slant.

    For each unknown cell, check if one diagonal would form a loop.
    If so, place the other diagonal.
    """
    made_progress = False

    for cell in board.get_unknown_cells():
        slash_loops = board.would_form_loop(cell, SLASH)
        backslash_loops = board.would_form_loop(cell, BACKSLASH)

        if slash_loops and not backslash_loops:
            board.place_value(cell, BACKSLASH)
            made_progress = True
        elif backslash_loops and not slash_loops:
            board.place_value(cell, SLASH)
            made_progress = True
        # If both would form loops, we have a contradiction (shouldn't happen in valid puzzles)

    return made_progress


def rule_forced_solution_avoidance(board):
    """
    If providing the final slant to a given would cause an adjacent given to be unsolvable,
    it cannot be in that square.

    For each clued vertex that needs exactly 1 more touch:
    - For each unknown adjacent cell that could provide that touch
    - Check if placing that touch would make any OTHER adjacent clued vertex unsolvable
    - If so, that cell must be an avoider for this vertex
    """
    made_progress = False

    for vertex in board.get_clued_vertices():
        adjacent = board.get_adjacent_cells_for_vertex(vertex)
        clue = vertex.clue

        current_touches = 0
        unknown_cells = []

        for cell, slash_touches, backslash_touches in adjacent:
            if cell.value == UNKNOWN:
                unknown_cells.append((cell, slash_touches, backslash_touches))
            elif cell.value == SLASH and slash_touches:
                current_touches += 1
            elif cell.value == BACKSLASH and backslash_touches:
                current_touches += 1

        needed = clue - current_touches
        if needed != 1 or len(unknown_cells) <= 1:
            continue

        # For each unknown that could provide the final touch
        for cell, slash_touches, backslash_touches in unknown_cells:
            # Determine which diagonal would touch this vertex
            if slash_touches:
                touch_value = SLASH
                avoid_value = BACKSLASH
            else:
                touch_value = BACKSLASH
                avoid_value = SLASH

            # Check if placing touch_value would break any other adjacent vertex
            would_break = False

            # Get all vertices this cell touches
            corners = board.get_cell_corners(cell)
            tl, tr, bl, br = corners

            for corner in [tl, tr, bl, br]:
                if corner is None or corner == vertex:
                    continue
                if corner.clue is None:
                    continue

                # Check if this placement would cause corner to exceed its clue
                # or make it impossible to reach its clue

                # Does touch_value touch this corner?
                if touch_value == SLASH:
                    touches_corner = (corner == tr or corner == bl)
                else:  # BACKSLASH
                    touches_corner = (corner == tl or corner == br)

                c_current, c_unknown = board.count_touches(corner)

                if touches_corner:
                    # Would add a touch to corner
                    if c_current + 1 > corner.clue:
                        would_break = True
                        break
                else:
                    # Would be an avoider for corner - check if corner can still reach clue
                    # After this placement, corner loses one potential touch
                    # c_unknown - 1 remaining unknowns
                    if c_current + (c_unknown - 1) < corner.clue:
                        would_break = True
                        break

            if would_break:
                # This cell cannot touch this vertex - must avoid
                if not board.would_form_loop(cell, avoid_value):
                    board.place_value(cell, avoid_value)
                    made_progress = True

    return made_progress


def rule_loop_avoidance_2(board):
    """
    If finishing a 2 with two slants would force a loop, then the 2 must be
    finished in some other way.

    For each vertex with clue 2 that has exactly 0 touches and 2 unknowns:
    - If both unknowns touching would create a loop, at least one must avoid
    - This rule looks for forced patterns where the only valid completion
      requires specific placements
    """
    made_progress = False

    for vertex in board.get_clued_vertices():
        if vertex.clue != 2:
            continue

        adjacent = board.get_adjacent_cells_for_vertex(vertex)
        current_touches = 0
        unknown_cells = []

        for cell, slash_touches, backslash_touches in adjacent:
            if cell.value == UNKNOWN:
                unknown_cells.append((cell, slash_touches, backslash_touches))
            elif cell.value == SLASH and slash_touches:
                current_touches += 1
            elif cell.value == BACKSLASH and backslash_touches:
                current_touches += 1

        # Need exactly 2 more touches from exactly 2 unknowns
        if current_touches != 0 or len(unknown_cells) != 2:
            continue

        # Both unknowns must touch - determine what diagonals that requires
        cell1, slash1, back1 = unknown_cells[0]
        cell2, slash2, back2 = unknown_cells[1]

        val1 = SLASH if slash1 else BACKSLASH
        val2 = SLASH if slash2 else BACKSLASH

        # Check if placing both would form a loop
        # We need to simulate placing the first, then check if second forms loop

        # Save state
        state = board.save_state()

        # Try placing first
        if board.would_form_loop(cell1, val1):
            # First already forms loop - can't place it
            board.restore_state(state)
            continue

        board.place_value(cell1, val1)

        # Now check if second forms loop
        if board.would_form_loop(cell2, val2):
            # Placing both touching diagonals would form a loop
            # So we cannot have both touching - at least one must avoid
            # But the clue requires 2 touches... This is actually a contradiction
            # unless there are other unknown cells we missed
            board.restore_state(state)
            # This might indicate an error or need for different logic
            continue

        board.restore_state(state)

    return made_progress


def rule_corner_zero(board):
    """
    A vertex with clue 0 forces all adjacent cells to avoid it.
    (This is a special case of clue_finish_b but often applies early)
    """
    made_progress = False

    for vertex in board.get_clued_vertices():
        if vertex.clue != 0:
            continue

        adjacent = board.get_adjacent_cells_for_vertex(vertex)

        for cell, slash_touches, backslash_touches in adjacent:
            if cell.value != UNKNOWN:
                continue

            # Place the non-touching diagonal
            if slash_touches:
                if not board.would_form_loop(cell, BACKSLASH):
                    board.place_value(cell, BACKSLASH)
                    made_progress = True
            else:
                if not board.would_form_loop(cell, SLASH):
                    board.place_value(cell, SLASH)
                    made_progress = True

    return made_progress


def rule_corner_four(board):
    """
    A vertex with clue 4 forces all adjacent cells to touch it.
    (This is a special case of clue_finish_a)
    """
    made_progress = False

    for vertex in board.get_clued_vertices():
        if vertex.clue != 4:
            continue

        adjacent = board.get_adjacent_cells_for_vertex(vertex)

        for cell, slash_touches, backslash_touches in adjacent:
            if cell.value != UNKNOWN:
                continue

            # Place the touching diagonal
            if slash_touches:
                if not board.would_form_loop(cell, SLASH):
                    board.place_value(cell, SLASH)
                    made_progress = True
            else:
                if not board.would_form_loop(cell, BACKSLASH):
                    board.place_value(cell, BACKSLASH)
                    made_progress = True

    return made_progress


def rule_edge_clue_constraints(board):
    """
    Edge and corner vertices have fewer adjacent cells, making their clues
    more constraining.

    - Corner vertex (1 adjacent cell): clue 0 or 1 only
    - Edge vertex (2 adjacent cells): clue 0, 1, or 2 only

    This rule enforces these constraints by detecting impossible situations.
    """
    made_progress = False

    for vertex in board.get_clued_vertices():
        adjacent = board.get_adjacent_cells_for_vertex(vertex)
        max_possible = len(adjacent)
        clue = vertex.clue

        if clue > max_possible:
            # Invalid puzzle - clue cannot be satisfied
            continue

        # If clue equals max possible, all must touch
        if clue == max_possible:
            for cell, slash_touches, backslash_touches in adjacent:
                if cell.value != UNKNOWN:
                    continue
                if slash_touches:
                    if not board.would_form_loop(cell, SLASH):
                        board.place_value(cell, SLASH)
                        made_progress = True
                else:
                    if not board.would_form_loop(cell, BACKSLASH):
                        board.place_value(cell, BACKSLASH)
                        made_progress = True

    return made_progress


def rule_adjacent_ones(board):
    """
    Adjacent 1-1 pattern: Two horizontally or vertically adjacent vertices
    both with clue 1 create constraints on the shared cells.

    Key insight: A cell between two adjacent 1s can only touch ONE of them.
    So if both 1s have only the shared cell(s) available for their touch,
    one must get it and the other must look elsewhere.

    If a 1 has already been satisfied, cells shared with an adjacent 1 must avoid.
    """
    made_progress = False

    for vertex in board.get_clued_vertices():
        if vertex.clue != 1:
            continue

        vx, vy = vertex.vx, vertex.vy
        current, unknown = board.count_touches(vertex)

        # If this 1 is already satisfied, any shared cells with adjacent 1s must avoid us
        if current == 1:
            # Check adjacent 1s and mark shared cells as avoiders
            for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                neighbor = board.get_vertex(vx + dx, vy + dy)
                if neighbor and neighbor.clue == 1:
                    # Find shared cells and mark them to avoid this vertex
                    for cell, slash_t, back_t in board.get_adjacent_cells_for_vertex(vertex):
                        if cell.value != UNKNOWN:
                            continue
                        # Check if this cell is also adjacent to neighbor
                        neighbor_adj = board.get_adjacent_cells_for_vertex(neighbor)
                        for n_cell, n_slash_t, n_back_t in neighbor_adj:
                            if n_cell == cell:
                                # Shared cell - must avoid this vertex since we're satisfied
                                if slash_t:
                                    if not board.would_form_loop(cell, BACKSLASH):
                                        board.place_value(cell, BACKSLASH)
                                        made_progress = True
                                else:
                                    if not board.would_form_loop(cell, SLASH):
                                        board.place_value(cell, SLASH)
                                        made_progress = True
                                break

    return made_progress


def rule_adjacent_threes(board):
    """
    Adjacent 3-3 pattern: Two adjacent vertices both with clue 3 force
    specific diagonal orientations.

    Key insight: Each 3 needs 3 touches. Shared cells between two 3s can only
    touch one of them. So if a 3 only has 3 cells available and one is shared
    with another 3, the non-shared cells must all touch.
    """
    made_progress = False

    for vertex in board.get_clued_vertices():
        if vertex.clue != 3:
            continue

        vx, vy = vertex.vx, vertex.vy
        current, unknown = board.count_touches(vertex)

        # Check for adjacent 3s and analyze shared/unshared cells
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            neighbor = board.get_vertex(vx + dx, vy + dy)
            if not neighbor or neighbor.clue != 3:
                continue

            # Find cells adjacent to this vertex
            my_adj = board.get_adjacent_cells_for_vertex(vertex)
            neighbor_adj = board.get_adjacent_cells_for_vertex(neighbor)
            neighbor_cells = set(c for c, s, b in neighbor_adj)

            # Categorize my cells as shared or unshared
            shared_cells = []
            unshared_cells = []
            for cell, slash_t, back_t in my_adj:
                if cell in neighbor_cells:
                    shared_cells.append((cell, slash_t, back_t))
                else:
                    unshared_cells.append((cell, slash_t, back_t))

            # Calculate touches from unshared cells
            unshared_touches = 0
            unshared_unknown = []
            for cell, slash_t, back_t in unshared_cells:
                if cell.value == UNKNOWN:
                    unshared_unknown.append((cell, slash_t, back_t))
                elif (cell.value == SLASH and slash_t) or (cell.value == BACKSLASH and back_t):
                    unshared_touches += 1

            # If we need exactly as many touches as unshared unknowns can provide,
            # all unshared unknowns must touch
            needed_from_unshared = 3 - current - len(shared_cells)  # Max shared can give is 1 each
            # Actually, shared cells can each give at most 1 touch to us
            # (they can't give touches to both us and neighbor)

            # Simpler logic: if unshared_touches + len(unshared_unknown) == 3 - current - shared_contribution
            # But we need to be careful about what shared can contribute

            # Conservative: if all unshared must touch to have any chance
            if current + len(unshared_unknown) + len(shared_cells) == 3 and unshared_unknown:
                # All unshared unknowns must touch
                for cell, slash_t, back_t in unshared_unknown:
                    if slash_t:
                        if not board.would_form_loop(cell, SLASH):
                            board.place_value(cell, SLASH)
                            made_progress = True
                    else:
                        if not board.would_form_loop(cell, BACKSLASH):
                            board.place_value(cell, BACKSLASH)
                            made_progress = True

    return made_progress


def rule_v_pattern_with_three(board):
    """
    V-shaped pattern detection: If two diagonals form a V pointing up or down,
    and there's a 3 clue one cell above/below the point of the V, the 3 must
    have its remaining touches on the opposite side.

    Pattern: V shape with 3 above the meeting point means 3 can't have two touches
    going down (would close the V into a loop), so it needs two touches above.
    """
    made_progress = False

    # Look for V patterns formed by adjacent cells
    for y in range(board.height):
        for x in range(board.width - 1):
            cell_left = board.get_cell(x, y)
            cell_right = board.get_cell(x + 1, y)

            if cell_left is None or cell_right is None:
                continue

            # Check for \/ pattern (V pointing down)
            if cell_left.value == BACKSLASH and cell_right.value == SLASH:
                # V points down, meeting at vertex (x+1, y+1)
                # Check for 3 above this point at (x+1, y)
                vertex_above = board.get_vertex(x + 1, y)
                if vertex_above and vertex_above.clue == 3:
                    # The 3 at (x+1, y) already has 2 touches from the V below
                    # It needs 1 more from the cells above

                    current, unknown = board.count_touches(vertex_above)
                    if current == 2 and unknown > 0:
                        # Force the remaining touches to come from above
                        for cell, slash_t, back_t in board.get_adjacent_cells_for_vertex(vertex_above):
                            if cell.value != UNKNOWN:
                                continue
                            if cell.y < y:  # Cell is above the V
                                if slash_t:
                                    if not board.would_form_loop(cell, SLASH):
                                        board.place_value(cell, SLASH)
                                        made_progress = True
                                else:
                                    if not board.would_form_loop(cell, BACKSLASH):
                                        board.place_value(cell, BACKSLASH)
                                        made_progress = True

            # Check for /\ pattern (V pointing up)
            if cell_left.value == SLASH and cell_right.value == BACKSLASH:
                # V points up, meeting at vertex (x+1, y)
                # Check for 3 below this point at (x+1, y+1)
                vertex_below = board.get_vertex(x + 1, y + 1)
                if vertex_below and vertex_below.clue == 3:
                    current, unknown = board.count_touches(vertex_below)
                    if current == 2 and unknown > 0:
                        # Force remaining touches from below
                        for cell, slash_t, back_t in board.get_adjacent_cells_for_vertex(vertex_below):
                            if cell.value != UNKNOWN:
                                continue
                            if cell.y > y:  # Cell is below the V
                                if slash_t:
                                    if not board.would_form_loop(cell, SLASH):
                                        board.place_value(cell, SLASH)
                                        made_progress = True
                                else:
                                    if not board.would_form_loop(cell, BACKSLASH):
                                        board.place_value(cell, BACKSLASH)
                                        made_progress = True

    return made_progress


def rule_border_two_v_shape(board):
    """
    A 2 on the border creates a V-shape pattern.

    For a 2 on the top edge (vy=0), both cells below must touch it,
    creating a V-shape pattern. Similarly for other edges.
    """
    made_progress = False

    for vertex in board.get_clued_vertices():
        if vertex.clue != 2:
            continue

        vx, vy = vertex.vx, vertex.vy
        adjacent = board.get_adjacent_cells_for_vertex(vertex)

        # Check if on an edge (exactly 2 adjacent cells)
        if len(adjacent) != 2:
            continue

        # Both cells must touch
        current, unknown = board.count_touches(vertex)
        if current + unknown == 2 and unknown > 0:
            # All unknowns must touch
            for cell, slash_t, back_t in adjacent:
                if cell.value != UNKNOWN:
                    continue
                if slash_t:
                    if not board.would_form_loop(cell, SLASH):
                        board.place_value(cell, SLASH)
                        made_progress = True
                else:
                    if not board.would_form_loop(cell, BACKSLASH):
                        board.place_value(cell, BACKSLASH)
                        made_progress = True

    return made_progress


def rule_diagonal_ones(board):
    """
    Diagonal 1-1 pattern: Two vertices with clue 1 that are diagonally adjacent
    share exactly one cell. That cell's diagonal can only touch one of them.

    If both 1s have no other way to get their touch, we have a contradiction.
    If one 1 has another option and the other doesn't, the shared cell must
    touch the one without options.
    """
    made_progress = False

    for vertex in board.get_clued_vertices():
        if vertex.clue != 1:
            continue

        vx, vy = vertex.vx, vertex.vy
        current, unknown = board.count_touches(vertex)

        if current == 1:
            continue  # Already satisfied

        # Check diagonal neighbors
        for dx, dy in [(1, 1), (1, -1), (-1, 1), (-1, -1)]:
            neighbor = board.get_vertex(vx + dx, vy + dy)
            if not neighbor or neighbor.clue != 1:
                continue

            n_current, n_unknown = board.count_touches(neighbor)
            if n_current == 1:
                continue  # Neighbor already satisfied

            # Find the shared cell (it's at the corner between them)
            # For diagonal (dx, dy), shared cell is at position that touches both
            if dx == 1 and dy == 1:
                shared_cell = board.get_cell(vx, vy)  # Cell where vertex is top-left
            elif dx == 1 and dy == -1:
                shared_cell = board.get_cell(vx, vy - 1)  # Cell where vertex is bottom-left
            elif dx == -1 and dy == 1:
                shared_cell = board.get_cell(vx - 1, vy)  # Cell where vertex is top-right
            else:  # dx == -1 and dy == -1
                shared_cell = board.get_cell(vx - 1, vy - 1)  # Cell where vertex is bottom-right

            if shared_cell is None or shared_cell.value != UNKNOWN:
                continue

            # Count non-shared options for each vertex
            my_options = 0
            for cell, slash_t, back_t in board.get_adjacent_cells_for_vertex(vertex):
                if cell.value == UNKNOWN and cell != shared_cell:
                    my_options += 1

            neighbor_options = 0
            for cell, slash_t, back_t in board.get_adjacent_cells_for_vertex(neighbor):
                if cell.value == UNKNOWN and cell != shared_cell:
                    neighbor_options += 1

            # If one has no other options, shared cell must touch it
            if my_options == 0 and neighbor_options > 0:
                # Shared cell must touch me (this vertex)
                for cell, slash_t, back_t in board.get_adjacent_cells_for_vertex(vertex):
                    if cell == shared_cell:
                        if slash_t:
                            if not board.would_form_loop(cell, SLASH):
                                board.place_value(cell, SLASH)
                                made_progress = True
                        else:
                            if not board.would_form_loop(cell, BACKSLASH):
                                board.place_value(cell, BACKSLASH)
                                made_progress = True
                        break

            elif neighbor_options == 0 and my_options > 0:
                # Shared cell must touch neighbor (avoid me)
                for cell, slash_t, back_t in board.get_adjacent_cells_for_vertex(vertex):
                    if cell == shared_cell:
                        if slash_t:
                            if not board.would_form_loop(cell, BACKSLASH):
                                board.place_value(cell, BACKSLASH)
                                made_progress = True
                        else:
                            if not board.would_form_loop(cell, SLASH):
                                board.place_value(cell, SLASH)
                                made_progress = True
                        break

    return made_progress


def rule_trial_clue_violation(board):
    """
    For each unknown cell, try each diagonal and check if it immediately
    violates any clue constraint. If one option violates, use the other.

    This is a simple form of look-ahead that catches obvious contradictions.
    """
    made_progress = False

    for cell in board.get_unknown_cells():
        slash_valid = True
        backslash_valid = True

        # Check if SLASH would violate any clue
        if not board.would_form_loop(cell, SLASH):
            corners = board.get_cell_corners(cell)
            tl, tr, bl, br = corners
            # SLASH touches bl and tr
            for corner in [bl, tr]:
                if corner and corner.clue is not None:
                    current, _ = board.count_touches(corner)
                    if current + 1 > corner.clue:
                        slash_valid = False
                        break
            # SLASH avoids tl and br - check if they can still reach their clue
            for corner in [tl, br]:
                if corner and corner.clue is not None:
                    current, unknown = board.count_touches(corner)
                    # After placing SLASH, unknown decreases by 1
                    if current + (unknown - 1) < corner.clue:
                        slash_valid = False
                        break
        else:
            slash_valid = False

        # Check if BACKSLASH would violate any clue
        if not board.would_form_loop(cell, BACKSLASH):
            corners = board.get_cell_corners(cell)
            tl, tr, bl, br = corners
            # BACKSLASH touches tl and br
            for corner in [tl, br]:
                if corner and corner.clue is not None:
                    current, _ = board.count_touches(corner)
                    if current + 1 > corner.clue:
                        backslash_valid = False
                        break
            # BACKSLASH avoids bl and tr
            for corner in [bl, tr]:
                if corner and corner.clue is not None:
                    current, unknown = board.count_touches(corner)
                    if current + (unknown - 1) < corner.clue:
                        backslash_valid = False
                        break
        else:
            backslash_valid = False

        # If only one option is valid, use it
        if slash_valid and not backslash_valid:
            board.place_value(cell, SLASH)
            made_progress = True
        elif backslash_valid and not slash_valid:
            board.place_value(cell, BACKSLASH)
            made_progress = True

    return made_progress


def rule_one_step_lookahead(board):
    """
    For each unknown cell, try placing each diagonal and check if it creates
    an immediate impossible situation for any adjacent cell (both options invalid).

    This is a 1-step lookahead that catches contradictions one move ahead.
    """
    made_progress = False

    for cell in board.get_unknown_cells():
        # Try SLASH
        slash_causes_contradiction = False
        if not board.would_form_loop(cell, SLASH):
            state = board.save_state()
            try:
                board.place_value(cell, SLASH)
                # Check if any adjacent unknown cell now has no valid options
                for adj_cell in board.get_unknown_cells():
                    if adj_cell == cell:
                        continue
                    slash_ok = not board.would_form_loop(adj_cell, SLASH)
                    back_ok = not board.would_form_loop(adj_cell, BACKSLASH)

                    # Also check clue violations
                    if slash_ok:
                        corners = board.get_cell_corners(adj_cell)
                        tl, tr, bl, br = corners
                        for corner in [bl, tr]:  # SLASH touches these
                            if corner and corner.clue is not None:
                                current, _ = board.count_touches(corner)
                                if current + 1 > corner.clue:
                                    slash_ok = False
                                    break
                        if slash_ok:
                            for corner in [tl, br]:  # SLASH avoids these
                                if corner and corner.clue is not None:
                                    current, unknown = board.count_touches(corner)
                                    if current + (unknown - 1) < corner.clue:
                                        slash_ok = False
                                        break

                    if back_ok:
                        corners = board.get_cell_corners(adj_cell)
                        tl, tr, bl, br = corners
                        for corner in [tl, br]:  # BACKSLASH touches these
                            if corner and corner.clue is not None:
                                current, _ = board.count_touches(corner)
                                if current + 1 > corner.clue:
                                    back_ok = False
                                    break
                        if back_ok:
                            for corner in [bl, tr]:  # BACKSLASH avoids these
                                if corner and corner.clue is not None:
                                    current, unknown = board.count_touches(corner)
                                    if current + (unknown - 1) < corner.clue:
                                        back_ok = False
                                        break

                    if not slash_ok and not back_ok:
                        slash_causes_contradiction = True
                        break
            except:
                slash_causes_contradiction = True
            board.restore_state(state)
        else:
            slash_causes_contradiction = True  # Loop means invalid

        # Try BACKSLASH
        back_causes_contradiction = False
        if not board.would_form_loop(cell, BACKSLASH):
            state = board.save_state()
            try:
                board.place_value(cell, BACKSLASH)
                for adj_cell in board.get_unknown_cells():
                    if adj_cell == cell:
                        continue
                    slash_ok = not board.would_form_loop(adj_cell, SLASH)
                    back_ok = not board.would_form_loop(adj_cell, BACKSLASH)

                    if slash_ok:
                        corners = board.get_cell_corners(adj_cell)
                        tl, tr, bl, br = corners
                        for corner in [bl, tr]:
                            if corner and corner.clue is not None:
                                current, _ = board.count_touches(corner)
                                if current + 1 > corner.clue:
                                    slash_ok = False
                                    break
                        if slash_ok:
                            for corner in [tl, br]:
                                if corner and corner.clue is not None:
                                    current, unknown = board.count_touches(corner)
                                    if current + (unknown - 1) < corner.clue:
                                        slash_ok = False
                                        break

                    if back_ok:
                        corners = board.get_cell_corners(adj_cell)
                        tl, tr, bl, br = corners
                        for corner in [tl, br]:
                            if corner and corner.clue is not None:
                                current, _ = board.count_touches(corner)
                                if current + 1 > corner.clue:
                                    back_ok = False
                                    break
                        if back_ok:
                            for corner in [bl, tr]:
                                if corner and corner.clue is not None:
                                    current, unknown = board.count_touches(corner)
                                    if current + (unknown - 1) < corner.clue:
                                        back_ok = False
                                        break

                    if not slash_ok and not back_ok:
                        back_causes_contradiction = True
                        break
            except:
                back_causes_contradiction = True
            board.restore_state(state)
        else:
            back_causes_contradiction = True

        # If one causes contradiction, use the other
        if slash_causes_contradiction and not back_causes_contradiction:
            board.place_value(cell, BACKSLASH)
            made_progress = True
        elif back_causes_contradiction and not slash_causes_contradiction:
            board.place_value(cell, SLASH)
            made_progress = True

    return made_progress


def rule_single_path_extension(board):
    """
    If a path of diagonals reaches a dead end (vertex with no more possible
    connections except one), that connection must be made to avoid a loop.

    This detects situations where a diagonal chain would be trapped
    if not extended in a specific direction.
    """
    made_progress = False

    # For each vertex, check if it's at the end of a chain with only one escape
    for vy in range(board.height + 1):
        for vx in range(board.width + 1):
            vertex = board.get_vertex(vx, vy)
            if vertex is None:
                continue

            # Count how many diagonals currently connect to this vertex
            current, unknown = board.count_touches(vertex)

            # If exactly 1 diagonal connects (chain endpoint) and only 1 unknown
            # that unknown must also connect to extend the chain
            if current == 1 and unknown == 1:
                # This vertex is at the end of a chain with one possible extension
                # Check if NOT extending would trap the chain

                adjacent = board.get_adjacent_cells_for_vertex(vertex)
                for cell, slash_t, back_t in adjacent:
                    if cell.value != UNKNOWN:
                        continue

                    # This is the only unknown - determine if it must connect
                    # to avoid creating an isolated chain segment

                    # If the vertex has a clue, use that constraint
                    if vertex.clue is not None:
                        needed = vertex.clue - current
                        if needed == 1:
                            # Must touch
                            if slash_t:
                                if not board.would_form_loop(cell, SLASH):
                                    board.place_value(cell, SLASH)
                                    made_progress = True
                            else:
                                if not board.would_form_loop(cell, BACKSLASH):
                                    board.place_value(cell, BACKSLASH)
                                    made_progress = True
                        elif needed == 0:
                            # Must avoid
                            if slash_t:
                                if not board.would_form_loop(cell, BACKSLASH):
                                    board.place_value(cell, BACKSLASH)
                                    made_progress = True
                            else:
                                if not board.would_form_loop(cell, SLASH):
                                    board.place_value(cell, SLASH)
                                    made_progress = True

    return made_progress


def rule_dead_end_avoidance(board):
    """
    Dead-end avoidance: Prevent connecting two non-border vertex groups
    that would create an isolated region.

    Uses the board's persistent exits/border tracking.
    A "dead end" is a non-border group with exits <= 1.
    Connecting two dead ends creates an isolated region - forbidden.

    This rule was derived from techniques in Simon Tatham's Portable Puzzle
    Collection (https://www.chiark.greenend.org.uk/~sgtatham/puzzles/),
    used under the MIT license.
    """
    made_progress = False

    for cell in board.get_unknown_cells():
        x, y = cell.x, cell.y

        slash_forbidden = False
        back_forbidden = False

        # Check BACKSLASH: connects (x, y) to (x+1, y+1) - TL to BR
        # If both TL and BR are non-border dead-ends, forbid backslash
        tl_exits = board.get_vertex_group_exits(x, y)
        br_exits = board.get_vertex_group_exits(x + 1, y + 1)
        tl_border = board.get_vertex_group_border(x, y)
        br_border = board.get_vertex_group_border(x + 1, y + 1)

        if (not tl_border and not br_border and
            tl_exits <= 1 and br_exits <= 1):
            back_forbidden = True

        # Check SLASH: connects (x+1, y) to (x, y+1) - TR to BL
        # If both TR and BL are non-border dead-ends, forbid slash
        tr_exits = board.get_vertex_group_exits(x + 1, y)
        bl_exits = board.get_vertex_group_exits(x, y + 1)
        tr_border = board.get_vertex_group_border(x + 1, y)
        bl_border = board.get_vertex_group_border(x, y + 1)

        if (not tr_border and not bl_border and
            tr_exits <= 1 and bl_exits <= 1):
            slash_forbidden = True

        # If one is forbidden and the other isn't, place the other
        if back_forbidden and not slash_forbidden:
            if not board.would_form_loop(cell, SLASH):
                board.place_value(cell, SLASH)
                made_progress = True
        elif slash_forbidden and not back_forbidden:
            if not board.would_form_loop(cell, BACKSLASH):
                board.place_value(cell, BACKSLASH)
                made_progress = True

    return made_progress


def rule_equivalence_classes(board):
    """
    Equivalence class tracking: Track squares that must have the same slash orientation.

    Uses the board's persistent equivalence tracking so that equivalences discovered
    by any rule are shared and accumulated across rule invocations.

    This rule:
    1. Discovers new equivalences from clue constraints (need 1 from 2 adjacent unknowns)
    2. Propagates known values through equivalence classes
    3. Detects when one diagonal would force a loop in an equivalent cell

    This rule was derived from techniques in Simon Tatham's Portable Puzzle
    Collection (https://www.chiark.greenend.org.uk/~sgtatham/puzzles/),
    used under the MIT license.
    """
    made_progress = False

    # First pass: establish equivalences from clues with exactly 2 unknowns and 1 needed
    for vertex in board.get_clued_vertices():
        adjacent = board.get_adjacent_cells_for_vertex(vertex)
        current_touches = 0
        unknown_cells = []

        for cell, slash_touches, backslash_touches in adjacent:
            if cell.value == UNKNOWN:
                unknown_cells.append((cell, slash_touches, backslash_touches))
            elif cell.value == SLASH and slash_touches:
                current_touches += 1
            elif cell.value == BACKSLASH and backslash_touches:
                current_touches += 1

        needed = vertex.clue - current_touches

        # If we need exactly 1 more line and have exactly 2 unknowns
        # and they are ADJACENT (share an edge), they must have the same slash value
        if needed == 1 and len(unknown_cells) == 2:
            cell1, slash1, back1 = unknown_cells[0]
            cell2, slash2, back2 = unknown_cells[1]

            # Check if they're adjacent (share an edge, not diagonal)
            dx = abs(cell1.x - cell2.x)
            dy = abs(cell1.y - cell2.y)
            cells_are_adjacent = (dx == 1 and dy == 0) or (dx == 0 and dy == 1)

            if cells_are_adjacent:
                # Use board's equivalence tracking - may raise SolverDebugError if conflicts
                if board.mark_cells_equivalent(cell1, cell2):
                    made_progress = True

    # Second pass: propagate known values through equivalence classes
    for cell in board.get_unknown_cells():
        equiv_value = board.get_equivalence_class_value(cell)

        if equiv_value != UNKNOWN:
            # This cell should have this value
            if not board.would_form_loop(cell, equiv_value):
                board.place_value(cell, equiv_value)
                made_progress = True
            else:
                # Would form a loop - try the other value
                other_value = BACKSLASH if equiv_value == SLASH else SLASH
                if not board.would_form_loop(cell, other_value):
                    board.place_value(cell, other_value)
                    made_progress = True

    # Third pass: check if one diagonal would force a loop in an equivalent cell
    for cell in board.get_unknown_cells():
        equiv_cells = [c for c in board.get_equivalent_cells(cell)
                       if c != cell and c.value == UNKNOWN]

        if not equiv_cells:
            continue

        # Check if SLASH would force any equivalent cell into a loop
        slash_forbidden = any(board.would_form_loop(c, SLASH) for c in equiv_cells)
        back_forbidden = any(board.would_form_loop(c, BACKSLASH) for c in equiv_cells)

        # If one is forbidden, use the other
        if slash_forbidden and not back_forbidden:
            if not board.would_form_loop(cell, BACKSLASH):
                board.place_value(cell, BACKSLASH)
                made_progress = True
        elif back_forbidden and not slash_forbidden:
            if not board.would_form_loop(cell, SLASH):
                board.place_value(cell, SLASH)
                made_progress = True

    return made_progress


def rule_vbitmap_propagation(board):
    """
    V-bitmap propagation: Track and propagate which v-shapes are possible.

    Uses the board's persistent equivalence tracking so that equivalences
    discovered here are shared with other rules.

    V-bitmap (per cell):
    - bit 0: can form \/ shape with cell to the right
    - bit 1: can form /\ shape with cell to the right
    - bit 2: can form > shape with cell below
    - bit 3: can form < shape with cell below

    Rules:
    1. A 1 clue can never have a v-shape pointing AT it
    2. A 3 clue can never have a v-shape pointing AWAY from it
    3. A 2 clue propagates restrictions across
    4. When both v-shapes are ruled out between two cells, they're equivalent

    This rule iterates until no more changes can be made to the v-bitmap.

    This rule was derived from techniques in Simon Tatham's Portable Puzzle
    Collection (https://www.chiark.greenend.org.uk/~sgtatham/puzzles/),
    used under the MIT license.
    """
    made_progress = False
    w, h = board.width, board.height

    # Initialize vbitmap - all shapes initially possible
    vbitmap = [[0xF for _ in range(w)] for _ in range(h)]

    # Iterate until convergence
    changed = True
    while changed:
        changed = False

        # Apply constraints from known cell values
        for y in range(h):
            for x in range(w):
                cell = board.get_cell(x, y)
                if cell.value == UNKNOWN:
                    continue
                s = cell.value
                old = vbitmap[y][x]
                if s == SLASH:
                    vbitmap[y][x] &= ~0x5  # Can't do \/ or >
                    if x > 0 and (vbitmap[y][x-1] & 0x2):
                        vbitmap[y][x-1] &= ~0x2
                        changed = True
                    if y > 0 and (vbitmap[y-1][x] & 0x8):
                        vbitmap[y-1][x] &= ~0x8
                        changed = True
                else:
                    vbitmap[y][x] &= ~0xA  # Can't do /\ or <
                    if x > 0 and (vbitmap[y][x-1] & 0x1):
                        vbitmap[y][x-1] &= ~0x1
                        changed = True
                    if y > 0 and (vbitmap[y-1][x] & 0x4):
                        vbitmap[y-1][x] &= ~0x4
                        changed = True
                if vbitmap[y][x] != old:
                    changed = True

        # Apply constraints from clue values (interior vertices only)
        for vy in range(1, h):
            for vx in range(1, w):
                vertex = board.get_vertex(vx, vy)
                if vertex is None or vertex.clue is None:
                    continue
                c = vertex.clue

                if c == 1:
                    # 1 clue: no v-shape pointing AT it
                    old1 = vbitmap[vy-1][vx-1]
                    old2 = vbitmap[vy][vx-1]
                    old3 = vbitmap[vy-1][vx]
                    vbitmap[vy-1][vx-1] &= ~0x5
                    vbitmap[vy][vx-1] &= ~0x2
                    vbitmap[vy-1][vx] &= ~0x8
                    if vbitmap[vy-1][vx-1] != old1 or vbitmap[vy][vx-1] != old2 or vbitmap[vy-1][vx] != old3:
                        changed = True

                elif c == 3:
                    # 3 clue: no v-shape pointing AWAY from it
                    old1 = vbitmap[vy-1][vx-1]
                    old2 = vbitmap[vy][vx-1]
                    old3 = vbitmap[vy-1][vx]
                    vbitmap[vy-1][vx-1] &= ~0xA
                    vbitmap[vy][vx-1] &= ~0x1
                    vbitmap[vy-1][vx] &= ~0x4
                    if vbitmap[vy-1][vx-1] != old1 or vbitmap[vy][vx-1] != old2 or vbitmap[vy-1][vx] != old3:
                        changed = True

                elif c == 2:
                    # 2 clue: propagate restrictions across
                    old_tl = vbitmap[vy-1][vx-1]
                    old_bl = vbitmap[vy][vx-1]
                    old_tr = vbitmap[vy-1][vx]

                    # Horizontal: between top pair and bottom pair
                    top = vbitmap[vy-1][vx-1] & 0x3
                    bot = vbitmap[vy][vx-1] & 0x3
                    vbitmap[vy-1][vx-1] &= ~(0x3 ^ bot)
                    vbitmap[vy][vx-1] &= ~(0x3 ^ top)

                    # Vertical: between left pair and right pair
                    left = vbitmap[vy-1][vx-1] & 0xC
                    right = vbitmap[vy-1][vx] & 0xC
                    vbitmap[vy-1][vx-1] &= ~(0xC ^ right)
                    vbitmap[vy-1][vx] &= ~(0xC ^ left)

                    if vbitmap[vy-1][vx-1] != old_tl or vbitmap[vy][vx-1] != old_bl or vbitmap[vy-1][vx] != old_tr:
                        changed = True

        # When both v-shapes are ruled out between adjacent cells,
        # mark them as equivalent
        for y in range(h):
            for x in range(w):
                cell = board.get_cell(x, y)

                # Check horizontal neighbor
                if x + 1 < w:
                    right_cell = board.get_cell(x + 1, y)
                    if not (vbitmap[y][x] & 0x3):
                        if board.mark_cells_equivalent(cell, right_cell):
                            made_progress = True
                            changed = True

                # Check vertical neighbor
                if y + 1 < h:
                    below_cell = board.get_cell(x, y + 1)
                    if not (vbitmap[y][x] & 0xC):
                        if board.mark_cells_equivalent(cell, below_cell):
                            made_progress = True
                            changed = True

    return made_progress


def rule_simon_unified(board):
    """
    Unified rule that closely mimics Simon Tatham's slant solver.

    This implements all of Simon's deduction techniques in a single rule,
    using the board's persistent tracking (slashval, vbitmap, exits, border)
    to allow information to flow efficiently between techniques.

    Techniques:
    1. Clue completion with equivalence tracking
    2. Loop avoidance + dead-end avoidance + equivalence-based filling
    3. V-bitmap propagation

    This rule was derived from the slant solver in Simon Tatham's Portable
    Puzzle Collection (https://www.chiark.greenend.org.uk/~sgtatham/puzzles/),
    used under the MIT license.
    """
    w, h = board.width, board.height
    W, H = w + 1, h + 1
    made_progress = False
    done_something = True

    while done_something:
        done_something = False

        # =================================================================
        # PHASE 1: Clue completion with adjacent equivalent pair tracking
        # =================================================================
        for vy in range(H):
            for vx in range(W):
                vertex = board.get_vertex(vx, vy)
                if vertex is None or vertex.clue is None:
                    continue

                c = vertex.clue

                # Build list of neighbors with their slash relationship
                # Order matters - we need them in order around the vertex
                neighbours = []
                if vx > 0 and vy > 0:
                    cell = board.get_cell(vx - 1, vy - 1)
                    neighbours.append((cell, BACKSLASH))  # \ touches BR corner
                if vx > 0 and vy < h:
                    cell = board.get_cell(vx - 1, vy)
                    neighbours.append((cell, SLASH))      # / touches TR corner
                if vx < w and vy < h:
                    cell = board.get_cell(vx, vy)
                    neighbours.append((cell, BACKSLASH))  # \ touches TL corner
                if vx < w and vy > 0:
                    cell = board.get_cell(vx, vy - 1)
                    neighbours.append((cell, SLASH))      # / touches BL corner

                if not neighbours:
                    continue

                nneighbours = len(neighbours)

                # Count undecided (nu) and lines still needed (nl)
                # Also track adjacent equivalent pairs (like Simon's solver)
                nu = 0
                nl = c

                # Get equiv class of last cell (wrapping around)
                last_cell = neighbours[nneighbours - 1][0]
                if last_cell.value == UNKNOWN:
                    last_eq = board.get_cell_equiv_root(last_cell)
                else:
                    last_eq = -1

                # Track equivalent pair: meq = equiv class, mj1/mj2 = the two cells
                meq = -1
                mj1 = None
                mj2 = None

                for i in range(nneighbours):
                    cell, slash_type = neighbours[i]
                    if cell.value == UNKNOWN:
                        nu += 1
                        if meq < 0:
                            eq = board.get_cell_equiv_root(cell)
                            if eq == last_eq and last_cell != cell:
                                # Found adjacent equivalent pair!
                                meq = eq
                                mj1 = last_cell
                                mj2 = cell
                                nl -= 1    # Count as one line
                                nu -= 2    # Remove both from undecided
                            else:
                                last_eq = eq
                    else:
                        last_eq = -1
                        if cell.value == slash_type:
                            nl -= 1  # This cell provides a line
                    last_cell = cell

                # Check if impossible
                if nl < 0 or nl > nu:
                    continue

                # If we can fill remaining cells
                if nu > 0 and (nl == 0 or nl == nu):
                    for cell, slash_type in neighbours:
                        # Skip cells in equivalent pair - they're handled as unit
                        if cell == mj1 or cell == mj2:
                            continue
                        if cell.value == UNKNOWN:
                            if nl > 0:
                                value = slash_type
                            else:
                                value = BACKSLASH if slash_type == SLASH else SLASH

                            if not board.would_form_loop(cell, value):
                                board.place_value(cell, value)
                                done_something = True
                                made_progress = True

                # If exactly 2 undecided and need 1 line, and they're adjacent,
                # mark them as equivalent (they must have same slash type)
                elif nu == 2 and nl == 1:
                    # Find the two undecided cells
                    last_idx = -1
                    for i in range(nneighbours):
                        cell, _ = neighbours[i]
                        if cell.value == UNKNOWN and cell != mj1 and cell != mj2:
                            if last_idx < 0:
                                last_idx = i
                            elif last_idx == i - 1 or (last_idx == 0 and i == nneighbours - 1):
                                # Adjacent! Mark them equivalent
                                cell1 = neighbours[last_idx][0]
                                cell2 = neighbours[i][0]
                                if board.mark_cells_equivalent(cell1, cell2):
                                    done_something = True
                                    made_progress = True
                                break

        if done_something:
            continue

        # =================================================================
        # PHASE 2: Loop avoidance, dead-end avoidance, equivalence filling
        # =================================================================
        for y in range(h):
            for x in range(w):
                cell = board.get_cell(x, y)
                if cell.value != UNKNOWN:
                    continue

                fs = False  # Force slash
                bs = False  # Force backslash

                # Check equivalence class value
                v = board.get_equivalence_class_value(cell)
                if v == SLASH:
                    fs = True
                elif v == BACKSLASH:
                    bs = True

                # Check if backslash would form loop (then must be slash)
                # Backslash connects (x,y) to (x+1,y+1)
                c1 = board.get_vertex_root(x, y)
                c2 = board.get_vertex_root(x + 1, y + 1)
                if c1 == c2:
                    fs = True  # Would form loop, force slash

                # Dead-end avoidance for backslash
                if not fs:
                    if (not board.get_vertex_group_border(x, y) and
                        not board.get_vertex_group_border(x + 1, y + 1) and
                        board.get_vertex_group_exits(x, y) <= 1 and
                        board.get_vertex_group_exits(x + 1, y + 1) <= 1):
                        fs = True  # Dead-end avoidance

                # Check if slash would form loop (then must be backslash)
                # Slash connects (x+1,y) to (x,y+1)
                c1 = board.get_vertex_root(x + 1, y)
                c2 = board.get_vertex_root(x, y + 1)
                if c1 == c2:
                    bs = True  # Would form loop, force backslash

                # Dead-end avoidance for slash
                if not bs:
                    if (not board.get_vertex_group_border(x + 1, y) and
                        not board.get_vertex_group_border(x, y + 1) and
                        board.get_vertex_group_exits(x + 1, y) <= 1 and
                        board.get_vertex_group_exits(x, y + 1) <= 1):
                        bs = True  # Dead-end avoidance

                if fs and bs:
                    continue  # Contradiction, skip

                if fs:
                    board.place_value(cell, SLASH)
                    done_something = True
                    made_progress = True
                elif bs:
                    board.place_value(cell, BACKSLASH)
                    done_something = True
                    made_progress = True

        if done_something:
            continue

        # =================================================================
        # PHASE 3: V-bitmap propagation
        # =================================================================
        for y in range(h):
            for x in range(w):
                cell = board.get_cell(x, y)
                s = cell.value

                # If cell has a value, clear contradicting v-shapes
                if s != UNKNOWN:
                    # Clear from left neighbor
                    if x > 0:
                        left_cell = board.get_cell(x - 1, y)
                        bits = 0x1 if s == BACKSLASH else 0x2  # \ means no >, / means no <
                        if board.vbitmap_clear(left_cell, bits):
                            done_something = True
                            made_progress = True

                    # Clear from self for right neighbor
                    if x + 1 < w:
                        bits = 0x2 if s == BACKSLASH else 0x1  # \ means no <, / means no >
                        if board.vbitmap_clear(cell, bits):
                            done_something = True
                            made_progress = True

                    # Clear from above neighbor
                    if y > 0:
                        above_cell = board.get_cell(x, y - 1)
                        bits = 0x4 if s == BACKSLASH else 0x8  # \ means no v, / means no ^
                        if board.vbitmap_clear(above_cell, bits):
                            done_something = True
                            made_progress = True

                    # Clear from self for below neighbor
                    if y + 1 < h:
                        bits = 0x8 if s == BACKSLASH else 0x4  # \ means no ^, / means no v
                        if board.vbitmap_clear(cell, bits):
                            done_something = True
                            made_progress = True

                # If both h-shapes ruled out, mark cells equivalent
                if x + 1 < w and not (board.vbitmap_get(cell) & 0x3):
                    right_cell = board.get_cell(x + 1, y)
                    if board.mark_cells_equivalent(cell, right_cell):
                        done_something = True
                        made_progress = True

                # If both v-shapes ruled out, mark cells equivalent
                if y + 1 < h and not (board.vbitmap_get(cell) & 0xC):
                    below_cell = board.get_cell(x, y + 1)
                    if board.mark_cells_equivalent(cell, below_cell):
                        done_something = True
                        made_progress = True

        # V-bitmap constraints from clues (only interior clues)
        for vy in range(1, H - 1):
            for vx in range(1, W - 1):
                vertex = board.get_vertex(vx, vy)
                if vertex is None or vertex.clue is None:
                    continue

                c = vertex.clue
                tl = board.get_cell(vx - 1, vy - 1)
                bl = board.get_cell(vx - 1, vy)
                tr = board.get_cell(vx, vy - 1)

                if c == 1:
                    # 1 clue: no v pointing at it
                    # TL cell: clear both > (0x1) and v (0x4) pointing at clue
                    if board.vbitmap_clear(tl, 0x5):
                        done_something = True
                        made_progress = True
                    # BL cell: clear < (0x2) pointing at clue
                    if board.vbitmap_clear(bl, 0x2):
                        done_something = True
                        made_progress = True
                    # TR cell: clear ^ (0x8) pointing at clue
                    if board.vbitmap_clear(tr, 0x8):
                        done_something = True
                        made_progress = True

                elif c == 3:
                    # 3 clue: no v pointing away
                    # TL cell: clear < (0x2) and ^ (0x8) pointing away
                    if board.vbitmap_clear(tl, 0xA):
                        done_something = True
                        made_progress = True
                    # BL cell: clear > (0x1) pointing away
                    if board.vbitmap_clear(bl, 0x1):
                        done_something = True
                        made_progress = True
                    # TR cell: clear v (0x4) pointing away
                    if board.vbitmap_clear(tr, 0x4):
                        done_something = True
                        made_progress = True

                elif c == 2:
                    # 2 clue: propagate constraints across
                    # Horizontal propagation (between tl and bl)
                    tl_h = board.vbitmap_get(tl) & 0x3
                    bl_h = board.vbitmap_get(bl) & 0x3
                    if board.vbitmap_clear(tl, 0x3 ^ bl_h):
                        done_something = True
                        made_progress = True
                    if board.vbitmap_clear(bl, 0x3 ^ tl_h):
                        done_something = True
                        made_progress = True

                    # Vertical propagation (between tl and tr)
                    tl_v = board.vbitmap_get(tl) & 0xC
                    tr_v = board.vbitmap_get(tr) & 0xC
                    if board.vbitmap_clear(tl, 0xC ^ tr_v):
                        done_something = True
                        made_progress = True
                    if board.vbitmap_clear(tr, 0xC ^ tl_v):
                        done_something = True
                        made_progress = True

    return made_progress
