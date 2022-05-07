import sys
import pygame
import SudokuPuzzles
import copy
from playsound import playsound

# Everytime a value is added we re calc for each cell the avail values.
# Each cell stores its avail values in an array that is indexed by the solved_step.
# i.e. cell.avail_values[0] holds a set of the avail values for this cell after
# solved step 0 (load_puzzle).
# cell.avail_values[1] holds a set of the avail values for this cell after solved_step 1
# That allows to go backward ("undo") to the exact setting's of the previous step.

# Todo:
# 1. Sounds.
# 2. For each puzzle loaded, calculate difficulty 0-100.
# 3. Store each puzzle in DB and try to find similarities.

# for playing note.wav file
from pygame.locals import KEYDOWN


class Color:
    BLACK = (0, 0, 0)
    GREY = (160, 160, 160)
    RED = (255, 0, 0)
    YELLOW = (255, 255, 0)
    ORANGE = (255, 128, 0)
    PURPLE = (128, 0, 128)
    BLUE = (0, 0, 255)
    GREEN = (0, 255, 0)


class Status:
    SOLVED = -1
    NOT_SOLVED_NOT_STUCK = -2
    STATUS_NOT_SET = -3
    MULTIPLE_NON_DECISIVE_PATHS = -4


class SudokuCell:
    def __init__(self, row, col, grid):
        self.row = row
        self.col = col
        self.value = None
        self.available_values = []  # At the time of grid.solved_step
        self.solved_step = None
        self.grid = grid
        self.square_cells = []
        self.from_trial = False
        self.steps_to_stuck = {}

    def __deepcopy__(self, memo_dict={}):
        cls = self.__class__
        result = cls.__new__(cls)
        memo_dict[id(self)] = result
        for k, v in self.__dict__.items():
            if k == 'grid' or k == 'square_cells':
                v = None
            setattr(result, k, copy.deepcopy(v, memo_dict))
        return result

    def __str__(self):
        rv = f"Cell: row= {self.row} ,col= {self.col} ,value= {self.value} ,solved_step= {self.solved_step} " + \
             f",available_values= {self.available_values[-1]}"
        return rv

    def add_all_values(self):
        self.available_values.append({1, 2, 3, 4, 5, 6, 7, 8, 9})

    def solved(self, step, value, from_trial=False):
        self.value = value
        self.solved_step = step
        self.from_trial = from_trial
        # self.available_values[-1] = {}
        if from_trial:
            self.grid.trial_on_step = step

    def get_lssfc(self):
        # lssfc is: longest surely stuck for cell i.e.:
        # Only one value is positive (i.e. stuck), other values are negative (stuck, or got to a loop)

        # 20220505: Looks like having multiple stuck is ok. We want only one NEGATIVE value. In that case the value
        # With the highest positive number is the lssfc.

        lssfc = Status.STATUS_NOT_SET
        value_for_cell = Status.STATUS_NOT_SET
        lssfc_msg = []
        negative_values_found = 0
        for value in sorted(self.steps_to_stuck.keys()):
            status = self.steps_to_stuck[value][-1][0]
            if status < 0:
                negative_values_found += 1
                if status == Status.SOLVED:
                    value_for_cell = value

            else:
                lssfc_candidate = len(self.steps_to_stuck[value])
                if lssfc == Status.STATUS_NOT_SET or (lssfc_candidate > lssfc > 0):
                    lssfc = lssfc_candidate
                    # set lssfc message
                    lssfc_msg = [""]
                    for step in self.steps_to_stuck[value]:
                        if step == self.steps_to_stuck[value][-1]:
                            lssfc_msg.append(f"Nothing fits cell ({step[0] + 1},{step[1] +1})")
                        else:
                            lssfc_msg[0] += f'{step[2]} in ({step[0] +1 },{step[1] + 1}) >>'

        if negative_values_found > 1:
            lssfc = Status.MULTIPLE_NON_DECISIVE_PATHS
            value_for_cell = Status.MULTIPLE_NON_DECISIVE_PATHS
        return lssfc, value_for_cell, lssfc_msg

    def set_square_cells(self):
        self.square_cells = []
        min_row = self.row // 3 * 3
        min_col = self.col // 3 * 3

        # print(f"({self.row},{self.col}) min_row={min_row} ,min_col={min_col}")

        for row in range(min_row, min_row + 3):
            for col in range(min_col, min_col + 3):
                # if row != self.row or col != self.col:
                self.square_cells.append(self.grid.cells[row][col])


class Sudoku:
    def __init__(self, verbose=1):
        self.verbose = verbose
        self.cells = []
        for row in range(9):
            new_row = []
            for col in range(9):
                new_row.append(SudokuCell(row, col, self))
            self.cells.append(new_row)

        # self.cells = [[SudokuCell(row, col, self) for col in range(9)] for row in range(9)]

        for row in range(9):
            for col in range(9):
                self.cells[row][col].set_square_cells()
        self.solved = True
        self.loaded = False
        self.solved_step = 0
        self.show_available_values = False
        self.trial = None
        self.trial_on_step = 100
        self.solve_able = True
        self.on = True
        self.CONTAINER_WIDTH_HEIGHT = 600  # Not to be confused with SCREENSIZE
        self.text_font = None
        self.avail_font = None
        self.surf = None
        self.msg = "Go!"
        self.msg_color = Color.BLUE
        self.hint = False
        self.algo_level = 1
        self.is_copy = False
        self.non_solve_able_cell = None

    def __copy__(self):
        cls = self.__class__
        result = cls.__new__(cls)
        for k, v in self.__dict__.items():
            # print(f's dcc {k} {v}')
            if k == 'cells':
                cells_copy = []
                for row in range(9):
                    new_row = []
                    for col in range(9):
                        new_row.append(copy.deepcopy(self.cells[row][col]))
                    cells_copy.append(new_row)
                setattr(result, k, cells_copy)
                continue
            if k == 'text_font' or k == 'avail_font':
                v = None

            setattr(result, k, copy.copy(v))
        return result

    def draw_grid(self, divisions):
        cont_x, cont_y = 10, 10  # TOP LEFT OF CONTAINER

        # DRAW Grid Border:
        # TOP lEFT TO RIGHT
        pygame.draw.line(
            self.surf, Color.BLACK,
            (cont_x, cont_y),
            (self.CONTAINER_WIDTH_HEIGHT + cont_x, cont_y), 2)
        # # BOTTOM lEFT TO RIGHT
        pygame.draw.line(
            self.surf, Color.BLACK,
            (cont_x, self.CONTAINER_WIDTH_HEIGHT + cont_y),
            (self.CONTAINER_WIDTH_HEIGHT + cont_x, self.CONTAINER_WIDTH_HEIGHT + cont_y), 2)
        # # LEFT TOP TO BOTTOM
        pygame.draw.line(
            self.surf, Color.BLACK,
            (cont_x, cont_y),
            (cont_x, cont_y + self.CONTAINER_WIDTH_HEIGHT), 2)
        # # RIGHT TOP TO BOTTOM
        pygame.draw.line(
            self.surf, Color.BLACK,
            (self.CONTAINER_WIDTH_HEIGHT + cont_x, cont_y),
            (self.CONTAINER_WIDTH_HEIGHT + cont_x, self.CONTAINER_WIDTH_HEIGHT + cont_y), 2)

        cellSize = self.CONTAINER_WIDTH_HEIGHT / divisions

        for x in range(divisions):
            if x % 3 == 0:
                width = 2
            else:
                width = 1

            # VERTICAL
            pygame.draw.line(
                self.surf, Color.BLACK,
                (cont_x + (cellSize * x), cont_y),
                (cont_x + (cellSize * x), self.CONTAINER_WIDTH_HEIGHT + cont_y), width)
            # HORIZONTAL
            pygame.draw.line(
                self.surf, Color.BLACK,
                (cont_x, cont_y + (cellSize * x)),
                (cont_x + self.CONTAINER_WIDTH_HEIGHT, cont_y + (cellSize * x)), width)

            """
            if self.hint:
                # up
                pygame.draw.line(
                    self.surf, Color.BLUE,
                    (cont_x  + (cellSize * self.hint.col)    , cont_y + (cellSize * self.hint.row)),
                    (cont_x + (cellSize * (self.hint.col +1)), cont_y + (cellSize * self.hint.row)), 3)

                # bottom
                pygame.draw.line(
                    self.surf, Color.BLUE,
                    (cont_x + (cellSize * self.hint.col), cont_y + (cellSize * (self.hint.row + 1))),
                    (cont_x + (cellSize * (self.hint.col + 1)), cont_y + (cellSize * (self.hint.row + 1))), 3)

                # left
                pygame.draw.line(
                    self.surf, Color.BLUE,
                    (cont_x + cellSize * self.hint.col, cont_y + (cellSize * self.hint.row)),
                    (cont_x + cellSize * self.hint.col,  cont_y + (cellSize * (self.hint.row + 1))), 3)

                # right
                pygame.draw.line(
                    self.surf, Color.BLUE,
                    (cont_x + cellSize * (self.hint.col + 1), cont_y + (cellSize * self.hint.row)),
                    (cont_x + cellSize * (self.hint.col + 1), cont_y + (cellSize * (self.hint.row + 1))), 3)
            """

    def get_color(self, cell):
        if cell.from_trial:
            rv = Color.YELLOW

        elif cell.solved_step == 0:
            # Input
            rv = Color.BLACK

        elif cell.solved_step == self.solved_step:
            # Most recent
            rv = Color.RED

        elif cell.solved_step == self.solved_step - 1:
            # Previous
            rv = Color.PURPLE

        elif self.trial_on_step < cell.solved_step:
            rv = Color.ORANGE

        else:
            rv = Color.BLUE

        return rv

    def print_text(self, text, row, color=Color.BLACK):
        location = (self.CONTAINER_WIDTH_HEIGHT + 30, row * 20)
        text = self.avail_font.render(text, True, color)
        self.surf.blit(text, location)

    def print_instructions(self, cells_solved):
        self.print_text("Instructions:", 1)
        self.print_text("Use right arrow (->) in order to solve next step.", 2)
        self.print_text("Use left arrow (<-) in order to undo last step.", 3)
        self.print_text("q -> quit; h -> hint", 4)
        self.print_text("a -> show available values.", 5)
        self.print_text("Use any other key in order to hide available values / hint.", 6)
        self.print_text("In order to try a value use the following combination:", 7)
        self.print_text("     t[0-9][0-9][0-9]", 8)
        self.print_text("     First digit is raw, second is column, third is value.", 9)

        self.print_text("Colors:", 12)
        self.print_text("Input cells.", 13)
        self.print_text("Most recent value found.", 14, Color.RED)
        self.print_text("2nd most recent value found.", 15, Color.PURPLE)
        self.print_text("Value found before 2nd most recent found.", 16, Color.BLUE)
        self.print_text("Tried value", 17, Color.YELLOW)
        self.print_text("Value found before 2nd most recent found, after trial.", 18, Color.ORANGE)

        self.print_text("Status:", 21)
        self.print_text(f"At step: {self.solved_step}.", 22)
        self.print_text(f"Solved cells: {cells_solved}.", 23)

        if self.trial_on_step == 100:
            trial_status = "off."
            color = Color.BLACK
        else:
            trial_status = "ON."
            color = Color.YELLOW
        self.print_text(f"Trial is {trial_status}", 24, color)

        if self.solved:
            solved_status = "YES!"
            color = Color.BLACK
            self.msg = "Well done lad!"
        else:
            color = Color.BLUE
            solved_status = "not yet..."

        self.print_text(f"Solved? {solved_status}", 25, color)

        if self.solve_able:
            if self.solved:
                solvable_status = "You bet!"
                color = Color.BLUE
            else:
                solvable_status = "looks like"
                color = Color.BLACK
        else:
            solvable_status = "NO!"
            color = Color.RED
        self.print_text(f"Solvable? {solvable_status}", 26, color)

        row = 28
        if isinstance(self.msg, list):
            for i, msg in enumerate(self.msg):
                self.print_text(msg, row + i, self.msg_color)
        else:
            self.print_text(self.msg, row, self.msg_color)

    def show_values(self):
        cell_size = self.CONTAINER_WIDTH_HEIGHT // 9
        cells_solved = 0
        self.solved = True  # changed to False on the first unsolved cell found
        for row in range(9):
            for col in range(9):
                cell = self.cells[row][col]
                if cell.value is None:
                    self.solved = False

                    if self.show_available_values:
                        for i, avail_value in enumerate(sorted(cell.available_values[self.solved_step])):
                            text = self.avail_font.render(str(avail_value), True, Color.GREEN)
                            draw_v = cell_size * row + (cell_size // 3) * (i // 3) + (cell_size // 3)
                            draw_h = cell_size * col + cell_size // 3 * (i % 3) + (cell_size // 3)

                            self.surf.blit(text, (draw_h, draw_v))

                    if self.hint and self.hint == cell:
                        text = self.text_font.render("?", True, Color.RED)
                        draw_h = cell_size * col + cell_size // 2
                        draw_v = cell_size * row + cell_size // 2
                        self.surf.blit(text, (draw_h, draw_v))

                else:
                    color = self.get_color(cell)
                    text = self.text_font.render(str(cell.value), True, color)
                    draw_h = cell_size * col + cell_size // 2
                    draw_v = cell_size * row + cell_size // 2
                    self.surf.blit(text, (draw_h, draw_v))
                    cells_solved += 1

        if self.on:
            if self.solved:
                print("SOLVED !!!!!!")
                self.on = False
                # Todo make sound!!!!
            if not self.solve_able:
                print("NOT SOLVE ABLE !!!!!!")
                self.on = False

        return cells_solved

    def run(self):
        if not self.loaded:
            raise ValueError("Cant draw unloaded puzzle")

        # https://betterprogramming.pub/making-grids-in-python-7cf62c95f413

        # This is the main game loop, it constantly runs until you press the Q KEY
        # or close the window.
        # CAUTION: THis will run as fast as you computer allows,
        # if you need to set a specific FPS look at tick methods.

        pygame.init()  # Initial Setup
        SCREENSIZE = self.CONTAINER_WIDTH_HEIGHT * 1.6 + 50, self.CONTAINER_WIDTH_HEIGHT + 50
        self.surf = pygame.display.set_mode(SCREENSIZE)
        pygame.display.set_caption('Amir\'s Sudoku')

        self.text_font = pygame.font.SysFont("comics", self.CONTAINER_WIDTH_HEIGHT // 10)
        self.avail_font = pygame.font.SysFont("comics", self.CONTAINER_WIDTH_HEIGHT // 30)

        while True:
            self.check_events()
            self.draw()

    def draw(self):
        self.surf.fill(Color.GREY)
        self.draw_grid(9)
        cells_solved = self.show_values()
        self.print_instructions(cells_solved)
        pygame.display.update()
        return cells_solved

    def do_trial(self):
        row = int(self.trial[0]) - 1
        col = int(self.trial[1]) - 1
        val = int(self.trial[2])

        cell = self.cells[row][col]
        if cell.value is None:
            if val in cell.available_values[self.solved_step]:
                self.solved_step += 1
                self.cells[row][col].solved(self.solved_step, val, True)
                self.update_all_available_values(new_step=True)
                self.msg = f"Trying {val} at ({row},{col})"
                self.msg_color = Color.YELLOW
            else:
                self.msg = f"Cell ({row + 1},{col + 1}): {val} is not available in this cell."
                self.msg_color = Color.RED
        else:
            self.msg = f"Cell ({row + 1},{col + 1}): already has value of {cell.value}"
            self.msg_color = Color.RED

    def apply_algo_level3(self):
        """
        Go over all non solved cells. Use only those with only 1 negative value
        i.e. only one value is not stuck. That means all other values get stuck.
        Among the stuck values, find the longest path for this cell. We will call
        this value "longest surely stuck for cell", LSSFC
        Find the cell with the minimal LSSFC and show it as the next solvable.
        """
        self.algo_level = 3
        self.update_all_available_values(new_step=False)
        best_cell_to_solve = None
        best_cell_to_solve_LSSFC = None
        best_cell_to_solve_value = None
        best_cell_to_solve_msg = None
        for row in range(9):
            for col in range(9):
                cell = self.cells[row][col]
                lssfc, value_for_cell, msg = cell.get_lssfc()
                if lssfc > 1 and (best_cell_to_solve_LSSFC is None or best_cell_to_solve_LSSFC > lssfc):
                    best_cell_to_solve = cell
                    best_cell_to_solve_LSSFC = lssfc
                    best_cell_to_solve_value = value_for_cell
                    best_cell_to_solve_msg = msg
                    if self.verbose > 1:
                        print(f'cell {cell} ,lssfc {lssfc} ,best_cell_to_solve_value {best_cell_to_solve_value}')

        if self.verbose > 0:
            print(f'Best cell to solve is {best_cell_to_solve}, with lssfc {best_cell_to_solve_LSSFC},' +
                  f'value_for_cell= {best_cell_to_solve_value}')

        if best_cell_to_solve is None:
            print("ALGO_LEVEL3 FAILED!!!, Call Amir 054-9574802 and get a reward!")
        else:
            self.solved_step += 1
            best_cell_to_solve.solved(self.solved_step, best_cell_to_solve_value)

            self.msg = []
            self.msg.append(f"Cell ({best_cell_to_solve.row + 1}, {best_cell_to_solve.col + 1}): only " +
                            f"{best_cell_to_solve_value} is available in this cell.")
            for msg in best_cell_to_solve_msg:
                self.msg.append(msg)
            self.algo_level = 1
            self.update_all_available_values(new_step=True)

    def check_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()

            if event.type == pygame.locals.KEYDOWN:
                self.show_available_values = False
                self.hint = False
                if event.key == pygame.locals.K_a:
                    self.show_available_values = True

                if event.key == pygame.locals.K_q:
                    pygame.quit()
                    sys.exit()

                if event.key == pygame.locals.K_3:
                    self.apply_algo_level3()

                if event.key == pygame.locals.K_v:
                    self.verbose += 1
                    print(f'Raised verbose to {self.verbose}')

                if event.key == pygame.locals.K_c:
                    self.verbose -= 1
                    print(f'Decreased verbose to {self.verbose}')

                if event.key == pygame.locals.K_h:
                    self.hint = True
                    if self.on:
                        self.solve_next_cell()

                if event.key == pygame.locals.K_DOWN or event.key == pygame.locals.K_RIGHT:
                    if self.on:
                        self.solve_next_cell()

                if event.key == pygame.locals.K_f:
                    for _ in range(81):
                        if self.on:
                            pygame.time.delay(50)
                            was_cell_solved = self.solve_next_cell()
                            cells_solved = self.draw()
                            if cells_solved == 81 or not was_cell_solved:
                                break

                if event.key == pygame.locals.K_UP or event.key == pygame.locals.K_LEFT:
                    self.undo()

                if event.key == pygame.locals.K_t:
                    self.trial = ""

                elif self.trial is not None:
                    if pygame.locals.K_0 <= event.key <= pygame.locals.K_9:
                        self.trial += str(event.key - 48)
                        if len(self.trial) == 3 and self.on:
                            self.do_trial()
                            self.trial = None
                    else:
                        self.trial = None
                else:
                    self.trial = None

    def print(self):
        for row in range(9):
            for col in range(9):
                print(self.cells[row][col])
        print("-------------------------")

    def undo(self):
        self.solve_able = True
        self.on = True
        if self.solved_step == 0:
            # Todo make sound
            pass
        else:
            found = False
            for row in range(9):
                if not found:
                    for col in range(9):
                        cell = self.cells[row][col]
                        cell.available_values.pop()
                        if cell.value is not None:
                            if cell.solved_step == self.solved_step:
                                self.msg = f"Undo: deleted value {cell.value} from cell ({cell.row + 1},{cell.col + 1})"
                                self.msg_color = Color.BLUE
                                cell.value = None

            if self.trial_on_step == self.solved_step:
                # undo trial
                self.trial_on_step = 100
            self.solved_step -= 1
            self.solved = False

    def update_all_available_values(self, new_step):
        self.solved = True
        self.non_solve_able_cell = None
        while True:
            avail_changed = False
            derive_changed = False
            for row in range(9):
                for col in range(9):
                    cell = self.cells[row][col]
                    if new_step:
                        cell.available_values.append(cell.available_values[-1].copy())
                    if cell.value is None:
                        self.solved = False
                        avail_changed = self.update_available_values(cell) or avail_changed
                        if len(cell.available_values[self.solved_step]) == 0:
                            self.solve_able = False
                            self.non_solve_able_cell = cell
                            self.msg = f"Not solvable!!! cell ({cell.row + 1},{cell.col + 1}) has no avail values"
                            self.msg_color = Color.RED

            new_step = False
            if self.algo_level > 1 and self.solve_able:
                for row in range(9):
                    for col in range(9):
                        cell = self.cells[row][col]
                        if cell.value is None:
                            if self.algo_level == 2:
                                derive_changed = self.remove_derived_values(cell) or derive_changed
                                if len(cell.available_values[self.solved_step]) == 0:
                                    self.msg = f"Not solvable!!! cell ({cell.row},{cell.col}) has no avail values"
                                    self.msg_color = Color.RED
                                    self.solve_able = False
                                    self.non_solve_able_cell = cell
                            if not self.is_copy and self.algo_level == 3:
                                self.apply_algo_level3_to_cell(cell)

            if not avail_changed and not derive_changed:
                break

    def get_copy(self):
        puzzle_copy = copy.copy(self)
        puzzle_copy.is_copy = True
        for row in range(9):
            for col in range(9):
                puzzle_copy.cells[row][col].grid = puzzle_copy
                puzzle_copy.cells[row][col].set_square_cells()
        return puzzle_copy

    def get_steps_to_stuck(self, cell, value):
        rv = []
        puzzle_copy = self.get_copy()
        puzzle_copy.cells[cell.row][cell.col].value = value
        puzzle_copy.verbose = 2
        puzzle_copy.update_all_available_values(new_step=False)
        rv.append([cell.row, cell.col, value])
        next_solved_cell = True
        while puzzle_copy.solve_able and next_solved_cell is not None and not puzzle_copy.solved:
            next_solved_cell = puzzle_copy.solve_next_cell()
            if next_solved_cell is not None:
                rv.append(next_solved_cell)
        if puzzle_copy.solved:
            rv.append([Status.SOLVED, 0, 0])
        elif puzzle_copy.solve_able:
            rv.append([Status.NOT_SOLVED_NOT_STUCK, 0, 0])
        else:
            rv.append([puzzle_copy.non_solve_able_cell.row, puzzle_copy.non_solve_able_cell.col, 'x'])
        return rv

    def apply_algo_level3_to_cell(self, cell):
        # Clean previous found values
        value = None
        cell.steps_to_stuck = {}
        for value in sorted(cell.available_values[-1]):
            cell.steps_to_stuck[value] = self.get_steps_to_stuck(cell, value)
        if self.verbose > 1:
            print(f'AL3 {cell} val {value} sts={cell.steps_to_stuck}')

    def remove_derived_values(self, cell):
        changed = self.remove_non_available_values(cell, 'row_derived')
        changed = changed or self.remove_non_available_values(cell, 'col_derived')
        changed = changed or self.remove_non_available_values(cell, 'square_derived')
        return changed

    def update_available_values(self, cell):
        changed = self.remove_non_available_values(cell, 'row')
        changed = self.remove_non_available_values(cell, 'col') or changed
        changed = self.remove_non_available_values(cell, 'square') or changed
        return changed

    def show_hint(self, cell):
        pass

    def solve_next_cell(self):
        # Find cells that have unique values
        rv = None
        for row in range(9):
            if rv is None and self.solve_able:
                for col in range(9):
                    cell = self.cells[row][col]
                    if cell.value is None:
                        if len(cell.available_values[self.solved_step]) == 1:
                            if self.hint:
                                self.hint = cell
                                self.msg = f"Cell ({cell.row + 1}, {cell.col + 1}): only ? is available " + \
                                           "in this cell."
                                self.msg_color = Color.BLUE
                                value = None
                            else:
                                value = list(cell.available_values[self.solved_step])[0]
                                self.solved_step += 1
                                cell.solved(self.solved_step, value)
                                self.update_all_available_values(new_step=True)
                                if self.solve_able:
                                    self.msg = f"Cell ({cell.row + 1}, {cell.col + 1}): only {value} is available " + \
                                            "in this cell."
                                    self.msg_color = Color.BLUE
                                if self.verbose > 2:
                                    print(f'solved step= {self.solved_step} ,{self.msg}')
                                    # playsound('slice.wav')
                            rv = [row, col, value]
                            break

        if rv is None and self.solve_able:
            # There is no cell with single value available
            # go over rows (then columns, then squares) and see if a value is only available in one cell
            rv = self.find_value_avail_once_in_row()
            if rv is None:
                rv = self.find_value_avail_once_in_col()
                if rv is None:
                    rv = self.find_value_avail_once_in_square()
        if self.algo_level < 2 and rv is None:
            if self.verbose > 2:
                print("Using algo level 2")
            self.update_all_available_values(new_step=False)
            self.algo_level = 2
            return self.solve_next_cell()

        # if self.algo_level < 3 and not solved_cell and not self.is_copy:
        #    print("TBD")
            # print("Using algo level 3")
            # self.algo_level = 3
            # For each non solved cell try every avail value. Among the values tried and found they make the puzzle not
            # solvable, remove the one that makes the puzzle not solvable in the minimal steps.
            # self.update_all_available_values(new_step=False)

        if rv is not None:
            self.algo_level = 1

        return rv

    def find_value_avail_once_in_row(self):
        rv = None
        value_avail_in_col = None
        for row in range(9):
            if rv is None:
                for value in range(1, 10):
                    value_found = False
                    value_avail_found_times = 0
                    for col in range(9):
                        if self.cells[row][col].value == value:
                            # Found value in orw. No need to look for its available columns
                            value_found = True
                            break
                        elif self.cells[row][col].value is None and \
                                value in self.cells[row][col].available_values[self.solved_step]:
                            value_avail_in_col = col
                            value_avail_found_times += 1
                            if value_avail_found_times > 1:
                                # No need to check this value anymore (fow now...)
                                break
                    if not value_found and value_avail_found_times == 1:
                        if self.hint:
                            self.hint = self.cells[row][value_avail_in_col]
                            self.msg = f"Row {row + 1}: ? is only available in column {value_avail_in_col + 1}."
                            self.msg_color = Color.BLUE
                        else:
                            self.solved_step += 1
                            self.cells[row][value_avail_in_col].solved(self.solved_step, value)
                            self.update_all_available_values(new_step=True)
                            self.msg = f"Row {row + 1}: {value} is only available in column {value_avail_in_col + 1}."
                            self.msg_color = Color.BLUE
                            if self.verbose > 2:
                                print(f'solved step= {self.solved_step} ,{self.msg}')
                        rv = [row, value_avail_in_col, value]
                        # playsound('slice.wav')
                        break
        return rv

    def find_value_avail_once_in_col(self):
        rv = None
        value_avail_in_row = None
        for col in range(9):
            if rv is None:
                for value in range(1, 10):
                    value_found = False
                    value_avail_found_times = 0
                    for row in range(9):
                        if self.cells[row][col].value == value:
                            # Found value in orw. No need to look for its available columns
                            value_found = True
                            break
                        elif self.cells[row][col].value is None and \
                                value in self.cells[row][col].available_values[self.solved_step]:
                            value_avail_in_row = row
                            value_avail_found_times += 1
                            if value_avail_found_times > 1:
                                # No need to check this value anymore (fow now...)
                                break
                    if not value_found and value_avail_found_times == 1:
                        if self.hint:
                            self.hint = self.cells[value_avail_in_row][col]
                            self.msg = f"Col {col + 1}: ? is only available in raw {value_avail_in_row + 1}."
                            self.msg_color = Color.BLUE
                        else:
                            self.solved_step += 1
                            self.cells[value_avail_in_row][col].solved(self.solved_step, value)
                            self.update_all_available_values(new_step=True)
                            self.msg = f"Col {col + 1}: {value} is only available in raw {value_avail_in_row + 1}."
                            self.msg_color = Color.BLUE
                            if self.verbose > 2:
                                print(f'solved step= {self.solved_step} ,{self.msg}')
                        rv = [value_avail_in_row, col, value]
                        break
        return rv

    def find_value_avail_once_in_square(self):
        rv = None
        value_avail_in_row = None
        value_avail_in_col = None
        for row in range(0, 9, 3):
            if rv is None:
                for col in range(0, 9, 3):
                    if rv is None:
                        for value in range(1, 10):
                            value_found = False
                            value_avail_found_times = 0
                            up_left_cell = self.cells[row][col]
                            for cell_in_square in up_left_cell.square_cells:
                                if cell_in_square.value == value:
                                    # Found value in square. No need to look for its available columns
                                    value_found = True
                                    break
                                elif cell_in_square.value is None and \
                                        value in cell_in_square.available_values[self.solved_step]:
                                    value_avail_in_row = cell_in_square.row
                                    value_avail_in_col = cell_in_square.col
                                    value_avail_found_times += 1
                                    if value_avail_found_times > 1:
                                        # No need to check this value anymore (fow now...)
                                        break
                            if not value_found and value_avail_found_times == 1:
                                if self.hint:
                                    self.hint = self.cells[value_avail_in_row][value_avail_in_col]
                                    self.msg = f"? is only available in cell ({value_avail_in_row + 1}" + \
                                        f",{value_avail_in_col + 1} in this square"
                                else:
                                    self.solved_step += 1
                                    self.cells[value_avail_in_row][value_avail_in_col].solved(self.solved_step, value)
                                    self.update_all_available_values(new_step=True)

                                    self.msg = f"{value} is only available in cell ({value_avail_in_row+1}" + \
                                               f",{value_avail_in_col + 1} in this square"
                                    if self.verbose > 2:
                                        print(f'solved step= {self.solved_step} ,{self.msg}')
                                rv = [value_avail_in_row, value_avail_in_col, value]
                                break
        return rv

    def remove_non_available_value(self, cell, row, col, remove_type):
        removed = False
        cell_to_look_at = self.cells[row][col]
        if cell_to_look_at.value is not None and cell_to_look_at.value in cell.available_values[self.solved_step]:
            if self.verbose > 2:
                print(f"cell={cell.row},{cell.col}: removing value of {cell_to_look_at.value} found at ({row}" +
                      f",{col}) from avail values (same {remove_type})")
            cell.available_values[self.solved_step].remove(cell_to_look_at.value)
            removed = True
        return removed

    def remove_non_avail_row_derived(self, cell):
        """
        See remove_non_avail_square_derived
        """
        removed = False
        cells_with_similar_avail_values = []

        for col in range(9):
            if cell.available_values[self.solved_step] == \
                    self.cells[cell.row][col].available_values[self.solved_step]:
                cells_with_similar_avail_values.append(self.cells[cell.row][col])
        if len(cells_with_similar_avail_values) == len(cell.available_values[self.solved_step]):
            for col in range(9):
                if self.cells[cell.row][col].value is None:
                    if self.cells[cell.row][col] not in cells_with_similar_avail_values:
                        for value in cell.available_values[self.solved_step]:
                            if value in self.cells[cell.row][col].available_values[self.solved_step]:
                                self.cells[cell.row][col].available_values[self.solved_step].remove(value)
                                removed = True
        return removed

    def remove_non_avail_col_derived(self, cell):
        """
        See remove_non_avail_square_derived
        """
        removed = False
        cells_with_similar_avail_values = []

        for row in range(9):
            if cell.available_values[self.solved_step] == \
                    self.cells[row][cell.col].available_values[self.solved_step]:
                cells_with_similar_avail_values.append(self.cells[row][cell.col])
        if len(cells_with_similar_avail_values) == len(cell.available_values[self.solved_step]):
            for row in range(9):
                if self.cells[row][cell.col].value is None:
                    if self.cells[row][cell.col] not in cells_with_similar_avail_values:
                        for value in cell.available_values[self.solved_step]:
                            if value in self.cells[row][cell.col].available_values[self.solved_step]:
                                self.cells[row][cell.col].available_values[self.solved_step].remove(value)
                                removed = True
        return removed

    def remove_non_avail_square_derived(self, cell):
        """
        Go over every cell in the square. For unsolved square, find other cells with
        similar available values.
        If the number of cell that share the same available values is the similar
        to the amount of the available values that means that these cell hold
        these values. For example if two cells in the square can have only 1,2
        it is derived that 1,2 are in these two cells and are not available in
        any other cells in the square.
        """
        removed = False
        cells_with_similar_avail_values = []
        for cell_in_square in cell.square_cells:
            if cell.available_values[self.solved_step] == cell_in_square.available_values[self.solved_step]:
                cells_with_similar_avail_values.append(cell_in_square)
        if len(cells_with_similar_avail_values) == len(cell.available_values[self.solved_step]):
            for cell_in_square in cell.square_cells:
                if cell_in_square not in cells_with_similar_avail_values:
                    for value in cell.available_values[self.solved_step]:
                        if value in cell_in_square.available_values[self.solved_step]:
                            cell_in_square.available_values[self.solved_step].remove(value)
                            removed = True
        return removed

    def remove_non_available_values(self, cell, remove_type):
        removed = False
        if remove_type == "row":
            row = cell.row
            for col in range(9):
                removed_value_from_cell = self.remove_non_available_value(cell, row, col, remove_type)
                if removed_value_from_cell:
                    removed = True

        if remove_type == "col":
            col = cell.col
            for row in range(9):
                removed_value_from_cell = self.remove_non_available_value(cell, row, col, remove_type)
                if removed_value_from_cell:
                    removed = True

        if remove_type == "square":
            for cell_in_square in cell.square_cells:
                removed_value_from_cell = self.remove_non_available_value(cell, cell_in_square.row,
                                                                          cell_in_square.col, remove_type)
                if removed_value_from_cell:
                    removed = True

        if remove_type == "row_derived":
            removed = self.remove_non_avail_row_derived(cell)

        if remove_type == "col_derived":
            removed = self.remove_non_avail_col_derived(cell)

        if remove_type == "square_derived":
            removed = self.remove_non_avail_square_derived(cell)

        return removed

    def load_puzzle(self, a):
        if self.loaded:
            raise ValueError("Only one puzzle is available")
        self.loaded = True
        for row_index, row in enumerate(a):
            if len(row) != 9:
                raise ValueError(f"Row {row_index}, found {len(row)} values instead of 9 expected")
            for col_index, cell_input in enumerate(row):
                cell = self.cells[row_index][col_index]
                if cell_input is None:
                    self.solved = False
                    cell.add_all_values()
                else:
                    cell.value = cell_input
                    cell.solved_step = 0
                    cell.available_values.append({})
        self.update_all_available_values(new_step=False)


if __name__ == '__main__':
    # Todo: add sound, shortest failed trial

    sudoku = Sudoku()

    # Solvable algo level 1
    # sudoku.load_puzzle(SudokuPuzzles.haaretz_20220311_medium)

    # sudoku.load_puzzle(SudokuPuzzles.haaretz_20220401_medium)
    # sudoku.load_puzzle(SudokuPuzzles.haaretz_20220421_difficult)
    sudoku.load_puzzle(SudokuPuzzles.haaretz_20220506_difficult)

    # also level 1
    # sudoku.load_puzzle(SudokuPuzzles.haaretz_20220415_medium)
    # sudoku.load_puzzle(SudokuPuzzles.haaretz_20220311_difficult)

    # Solvable algo level 1
    # sudoku.load_puzzle(SudokuPuzzles.israel_hayom_20220414_medium)
    sudoku.run()
