import sys
import pygame
import SudokuPuzzles
from playsound import playsound


# Everytime a value is added we re calc for each cell the avail values.
# Each cell stores its avail values in an array that is indexed by the solved_step.
# i.e. cell.avail_values[0] holds a set of the avail values for this cell after
# solved step 0 (load_puzzle).
# cell.avail_values[1] holds a set of the avail values for this cell after solved_step 1
# That allows to go backward ("undo") to the exact setting's of the previous step.

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
        self.cells = [[SudokuCell(row, col, self) for col in range(9)] for row in range(9)]

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
        self.print_text("Use key q in quit.", 4)
        self.print_text("Use key a in order to show available value.", 5)
        self.print_text("Use any other key in order to hide available values.", 6)
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

        self.print_text(self.msg, 28, self.msg_color)

    def show_values(self):
        cell_size = self.CONTAINER_WIDTH_HEIGHT // 9
        cells_solved = 0
        for row in range(9):
            for col in range(9):
                cell = self.cells[row][col]
                if cell.value is None:
                    self.solved = False

                    if self.show_available_values:
                        for i, avail_value in enumerate(cell.available_values[self.solved_step]):
                            text = self.avail_font.render(str(avail_value), True, Color.GREEN)
                            draw_v = cell_size * row + (cell_size // 3) * (i // 3) + (cell_size // 3)
                            draw_h = cell_size * col + cell_size // 3 * (i % 3) + (cell_size // 3)

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
            self.surf.fill(Color.GREY)
            self.draw_grid(9)
            self.solved = True  # changed to False on the first unsolved cell found
            cell_solved = self.show_values()
            self.print_instructions(cell_solved)
            pygame.display.update()

    def do_trial(self):
        row = int(self.trial[0]) - 1
        col = int(self.trial[1]) - 1
        val = int(self.trial[2])

        cell = self.cells[row][col]
        if cell.value is None:
            if val in cell.available_values[self.solved_step]:
                self.solved_step += 1
                self.cells[row][col].solved(self.solved_step, val, True)
                self.update_all_available_values(new_step=True, update_derived=False)
                self.msg = f"Trying {val} at ({row},{col})"
                self.msg_color = Color.YELLOW
            else:
                self.msg = f"Cell ({row + 1},{col + 1}): {val} is not available in this cell."
                self.msg_color = Color.RED
        else:
            self.msg = f"Cell ({row + 1},{col + 1}): already has value of {cell.value}"
            self.msg_color = Color.RED

    def check_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()

            if event.type == pygame.locals.KEYDOWN:
                self.show_available_values = False
                if event.key == pygame.locals.K_a:
                    self.show_available_values = True

                if event.key == pygame.locals.K_q:
                    pygame.quit()
                    sys.exit()

                if event.key == pygame.locals.K_DOWN or event.key == pygame.locals.K_RIGHT:
                    if self.on:
                        self.solve_next_cell()

                if event.key == pygame.locals.K_f:
                    for _ in range(81):
                        if self.on:
                            self.solve_next_cell()

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

    def update_all_available_values(self, new_step, update_derived):
        while True:
            avail_changed = False
            derive_changed = False
            for row in range(9):
                for col in range(9):
                    cell = self.cells[row][col]
                    if new_step:
                        cell.available_values.append(cell.available_values[-1].copy())
                    if cell.value is None:
                        avail_changed = self.update_available_values(cell) or avail_changed
                        if len(cell.available_values[self.solved_step]) == 0:
                            self.solve_able = False
                            self.msg = f"Not solvable!!! cell ({cell.row + 1},{cell.col + 1}) has no avail values"
                            self.msg_color = Color.RED

            new_step = False
            if update_derived and self.solve_able:
                for row in range(9):
                    for col in range(9):
                        cell = self.cells[row][col]
                        if cell.value is None:
                            derive_changed = self.remove_derived_values(cell) or derive_changed
                            if len(cell.available_values[self.solved_step]) == 0:
                                self.msg = f"Not solvable!!! cell ({cell.row},{cell.col}) has no avail values"
                                self.msg_color = Color.RED
                                self.solve_able = False

            if not avail_changed and not derive_changed:
                break

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

    def solve_next_cell(self, second_run=False):
        # Find cells that have unique values
        solved_cell = False
        for row in range(9):
            if not solved_cell and self.solve_able:
                for col in range(9):
                    cell = self.cells[row][col]
                    if cell.value is None:
                        # populate available values
                        # self.update_available_values(cell)
                        # self.remove_derived_values(cell)

                        if len(cell.available_values[self.solved_step]) == 1:
                            value = list(cell.available_values[self.solved_step])[0]
                            self.solved_step += 1
                            cell.solved(self.solved_step, value)
                            self.update_all_available_values(new_step=True, update_derived=False)
                            if self.solve_able:
                                self.msg = f"Cell ({cell.row + 1}, {cell.col + 1}): only {value} is available " + \
                                        "in this cell."
                                self.msg_color = Color.BLUE
                                solved_cell = True
                                # playsound('slice.wav')
                            break
        if not solved_cell and self.solve_able:
            # There is no cell with single value available
            # go over rows (then columns, then squares) and see if a value is only available in one cell
            solved_cell = self.find_value_avail_once_in_row()
            if not solved_cell:
                solved_cell = self.find_value_avail_once_in_col()
                if not solved_cell:
                    solved_cell = self.find_value_avail_once_in_square()
        if not second_run and not solved_cell:
            print("APPLYING DERIVED")
            self.update_all_available_values(new_step=False, update_derived=True)
            self.solve_next_cell(True)

    def find_value_avail_once_in_row(self):
        solved = False
        value_avail_in_col = None
        for row in range(9):
            if not solved:
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
                        self.solved_step += 1
                        self.cells[row][value_avail_in_col].solved(self.solved_step, value)
                        self.update_all_available_values(new_step=True, update_derived=False)
                        self.msg = f"Row {row + 1}: {value} is only available in column {value_avail_in_col + 1}."
                        self.msg_color = Color.BLUE
                        solved = True
                        # playsound('slice.wav')
                        break
        return solved

    def find_value_avail_once_in_col(self):
        solved = False
        value_avail_in_row = None
        for col in range(9):
            if not solved:
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
                        self.solved_step += 1
                        self.cells[value_avail_in_row][col].solved(self.solved_step, value)
                        self.update_all_available_values(new_step=True, update_derived=False)
                        self.msg = f"Col {col + 1}: {value} is only available in raw {value_avail_in_row + 1}."
                        self.msg_color = Color.BLUE
                        solved = True
                        break
        return solved

    def find_value_avail_once_in_square(self):
        # Todo: test!
        solved = False
        value_avail_in_row = None
        value_avail_in_col = None
        for row in range(0, 9, 3):
            if not solved:
                for col in range(0, 9, 3):
                    if not solved:
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
                                self.solved_step += 1
                                self.cells[value_avail_in_row][value_avail_in_col].solved(self.solved_step, value)
                                self.update_all_available_values(new_step=True, update_derived=False)
                                if self.verbose > 0:
                                    self.msg = f"{value} is only available in cell ({value_avail_in_row+1}" + \
                                                f",{value_avail_in_col + 1} in this square"
                                solved = True
                                break
        return solved

    def remove_non_available_value(self, cell, row, col, remove_type):
        removed = False
        cell_to_look_at = self.cells[row][col]
        if cell_to_look_at.value is not None and cell_to_look_at.value in cell.available_values[self.solved_step]:
            if self.verbose > 1:
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
        self.update_all_available_values(new_step=False, update_derived=False)


if __name__ == '__main__':
    # Todo: add instructions, sound, more logic

    sudoku = Sudoku()
    # sudoku.load_puzzle(SudokuPuzzles.haaretz_20220311_medium)
    # sudoku.load_puzzle(SudokuPuzzles.haaretz_20220401_medium)
    sudoku.load_puzzle(SudokuPuzzles.haaretz_20220311_difficult)
    sudoku.run()
