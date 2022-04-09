import sys
import pygame
import SudokuPuzzles
from playsound import playsound

# for playing note.wav file
from pygame.locals import KEYDOWN

BLACK = (0, 0, 0)
GREY = (160, 160, 160)
RED = (255, 0, 0)
PURPLE = (128, 0, 128)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
CONTAINER_WIDTH_HEIGHT = 600  # Not to be confused with SCREENSIZE


def draw_grid(divisions, surf):
    cont_x, cont_y = 10, 10  # TOP LEFT OF CONTAINER

    # DRAW Grid Border:
    # TOP lEFT TO RIGHT
    pygame.draw.line(
      surf, BLACK,
      (cont_x, cont_y),
      (CONTAINER_WIDTH_HEIGHT + cont_x, cont_y), 2)
    # # BOTTOM lEFT TO RIGHT
    pygame.draw.line(
      surf, BLACK,
      (cont_x, CONTAINER_WIDTH_HEIGHT + cont_y),
      (CONTAINER_WIDTH_HEIGHT + cont_x, CONTAINER_WIDTH_HEIGHT + cont_y), 2)
    # # LEFT TOP TO BOTTOM
    pygame.draw.line(
      surf, BLACK,
      (cont_x, cont_y),
      (cont_x, cont_y + CONTAINER_WIDTH_HEIGHT), 2)
    # # RIGHT TOP TO BOTTOM
    pygame.draw.line(
      surf, BLACK,
      (CONTAINER_WIDTH_HEIGHT + cont_x, cont_y),
      (CONTAINER_WIDTH_HEIGHT + cont_x, CONTAINER_WIDTH_HEIGHT + cont_y), 2)

    cellSize = CONTAINER_WIDTH_HEIGHT/divisions

    for x in range(divisions):
        if x % 3 == 0:
            width = 2
        else:
            width = 1

        # VERTICAL
        pygame.draw.line(
           surf, BLACK,
           (cont_x + (cellSize * x), cont_y),
           (cont_x + (cellSize * x), CONTAINER_WIDTH_HEIGHT + cont_y), width)
        # HORIZONTAL
        pygame.draw.line(
          surf, BLACK,
          (cont_x, cont_y + (cellSize*x)),
          (cont_x + CONTAINER_WIDTH_HEIGHT, cont_y + (cellSize*x)), width)


class SudokuCell:
    def __init__(self, row, col, grid):
        self.row = row
        self.col = col
        self.value = None
        self.available_values = []
        self.solved_step = None
        self.grid = grid
        self.square_cells = []

    def __str__(self):
        rv = f"Cell: row= {self.row} ,col= {self.col} ,value= {self.value} ,solved_step= {self.solved_step} " + \
             f",available_values= {self.available_values}"
        return rv

    def add_all_values(self):
        self.available_values = {1, 2, 3, 4, 5, 6, 7, 8, 9}

    def solved(self, step, value):
        self.value = value
        self.available_values = []
        self.solved_step = step

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

    def get_color(self, cell):
        if cell.solved_step == 0:
            # Input
            rv = BLACK
        elif cell.solved_step == self.solved_step:
            # Most recent
            rv = RED

        elif cell.solved_step == self.solved_step - 1:
            # Previous
            rv = PURPLE

        else:
            rv = BLUE

        return rv

    def run(self):
        if not self.loaded:
            raise ValueError("Cant draw unloaded puzzle")

        # self.print()

        # https://betterprogramming.pub/making-grids-in-python-7cf62c95f413

        # This is the main game loop, it constantly runs until you press the Q KEY
        # or close the window.
        # CAUTION: THis will run as fast as you computer allows,
        # if you need to set a specific FPS look at tick methods.

        pygame.init()  # Initial Setup
        SCREENSIZE = CONTAINER_WIDTH_HEIGHT + 50,  CONTAINER_WIDTH_HEIGHT + 50

        surf = pygame.display.set_mode(SCREENSIZE)
        pygame.display.set_caption('Amir\'s Sudoku')

        text_font = pygame.font.SysFont("comics", CONTAINER_WIDTH_HEIGHT // 10)
        avail_font = pygame.font.SysFont("comics", CONTAINER_WIDTH_HEIGHT // 30)

        while True:
            self.check_events()
            surf.fill(GREY)
            draw_grid(9, surf)
            self.solved = True

            cell_size = CONTAINER_WIDTH_HEIGHT // 9

            for row in range(9):
                for col in range(9):
                    cell = self.cells[row][col]
                    if cell.value is None:
                        self.solved = False

                        if self.show_available_values:
                            for i, avail_value in enumerate(cell.available_values):
                                text = avail_font.render(str(avail_value), True, GREEN)
                                draw_v = cell_size * row + (cell_size // 3) * (i // 3) + (cell_size // 3)
                                draw_h = cell_size * col + cell_size // 3 * (i % 3) + (cell_size // 3)

                                # draw_h = cell_size * col + i % 3 * cell_size // 3 + 15
                                surf.blit(text, (draw_h, draw_v))

                    else:
                        color = self.get_color(cell)
                        text = text_font.render(str(cell.value), True, color)
                        draw_h = cell_size * col + cell_size // 2
                        draw_v = cell_size * row + cell_size // 2
                        surf.blit(text, (draw_h, draw_v))

            pygame.display.update()
            if self.solved:
                print("SOLVED !!!!!!")
                # Todo make sound!!!!

    def do_trial(self):
        # print(f"Do trial. self.trail is {self.trial}")
        row = int(self.trial[0])
        col = int(self.trial[1])
        val = int(self.trial[2])

        cell = self.cells[row][col]
        if cell.value is None:
            self.solved_step += 1
            self.cells[row][col].solved(self.solved_step, val)
        else:
            print(f"Cant use value {val} at cell({row},{col}) that already has value of {cell.value}")

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
                    self.solve_next_cell()
                    # self.print()

                if event.key == pygame.locals.K_UP or event.key == pygame.locals.K_LEFT:
                    self.undo()

                if event.key == pygame.locals.K_t:
                    self.trial = ""

                elif self.trial is not None:
                    if pygame.locals.K_0 <= event.key <= pygame.locals.K_9:
                        self.trial += str(event.key - 48)
                        if len(self.trial) == 3:
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
        if self.solved_step == 0:
            # Todo make sound
            pass
        else:
            found = False
            for row in range(9):
                if not found:
                    for col in range(9):
                        cell = self.cells[row][col]
                        if cell.value is not None:
                            if cell.solved_step == self.solved_step:
                                self.update_available_values(cell)
                                self.solved_step -= 1
                                found = True
                                break

    def update_all_available_values(self):
        for row in range(9):
            for col in range(9):
                cell = self.cells[row][col]
                if cell.value is None:
                    self.update_available_values(cell)

        for row in range(9):
            for col in range(9):
                cell = self.cells[row][col]
                if cell.value is None:
                    self.remove_derived_values(cell)


    def remove_derived_values(self, cell):
        self.remove_non_available_values(cell, 'row_derived')
        self.remove_non_available_values(cell, 'col_derived')
        self.remove_non_available_values(cell, 'square_derived')

    def update_available_values(self, cell):
        cell.value = None
        cell.solved_step = None
        cell.add_all_values()
        self.remove_non_available_values(cell, 'row')
        self.remove_non_available_values(cell, 'col')
        self.remove_non_available_values(cell, 'square')


    def solve_next_cell(self):
        # Find cells that have unique values
        solved = False
        for row in range(9):
            if not solved:
                for col in range(9):
                    cell = self.cells[row][col]
                    if cell.value is None:
                        # populate available values
                        self.update_available_values(cell)
                        self.remove_derived_values(cell)

                        if len(cell.available_values) == 1:
                            self.solved_step += 1
                            cell.solved(self.solved_step, cell.available_values.pop())
                            if self.verbose > 0:
                                print(f"Solved {cell} only value avail in cell")
                            solved = True
                            # playsound('slice.wav')
                            break
        if not solved:
            # There is no cell with single value available
            # go over rows (then columns, then squares) and see if a value is only available in one cell
            solved = self.find_value_avail_once_in_row()
            if not solved:
                solved = self.find_value_avail_once_in_col()
                if not solved:
                    self.find_value_avail_once_in_square()

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
                        elif value in self.cells[row][col].available_values:
                            value_avail_in_col = col
                            value_avail_found_times += 1
                            if value_avail_found_times > 1:
                                # No need to check this value anymore (fow now...)
                                break
                    if not value_found and value_avail_found_times == 1:
                        self.solved_step += 1
                        self.cells[row][value_avail_in_col].solved(self.solved_step, value)
                        if self.verbose > 0:
                            print(f"Solved {self.cells[row][value_avail_in_col]} only cell in row this value is avail")
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
                        elif value in self.cells[row][col].available_values:
                            value_avail_in_row = row
                            value_avail_found_times += 1
                            if value_avail_found_times > 1:
                                # No need to check this value anymore (fow now...)
                                break
                    if not value_found and value_avail_found_times == 1:
                        self.solved_step += 1
                        self.cells[value_avail_in_row][col].solved(self.solved_step, value)
                        if self.verbose > 0:
                            print(f"Solved {self.cells[value_avail_in_row][col]} only cell in col this value is avail")
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
                                elif value in cell_in_square.available_values:
                                    value_avail_in_row = cell_in_square.row
                                    value_avail_in_col = cell_in_square.col
                                    value_avail_found_times += 1
                                    if value_avail_found_times > 1:
                                        # No need to check this value anymore (fow now...)
                                        break
                            if not value_found and value_avail_found_times == 1:
                                self.solved_step += 1
                                self.cells[value_avail_in_row][value_avail_in_col].solved(self.solved_step, value)
                                if self.verbose > 0:
                                    print(f"Solved {self.cells[value_avail_in_row][value_avail_in_col]} " +
                                          f"only cell in square this value is avail")

                                solved = True
                                break
        return solved

    def remove_non_available_value(self, cell, row, col, remove_type):
        removed = False
        cell_to_look_at = self.cells[row][col]
        if cell_to_look_at.value is not None and cell_to_look_at.value in cell.available_values:
            if self.verbose > 1:
                print(f"cell={cell.row},{cell.col}: removing value of {cell_to_look_at.value} found at ({row}" +
                      f",{col}) from avail values (same {remove_type})")
            cell.available_values.remove(cell_to_look_at.value)
            removed = True
        return removed

    def remove_non_avail_row_derived(self, cell):
        """
        See remove_non_avail_square_derived
        """
        cells_with_similar_avail_values = []

        for col in range(9):
            if cell.available_values == self.cells[cell.row][col].available_values:
                cells_with_similar_avail_values.append(self.cells[cell.row][col])
        if len(cells_with_similar_avail_values) == len(cell.available_values):
            for col in range(9):
                if self.cells[cell.row][col].value is None:
                    if self.cells[cell.row][col] not in cells_with_similar_avail_values:
                        for value in cell.available_values:
                            if value in self.cells[cell.row][col].available_values:
                                self.cells[cell.row][col].available_values.remove(value)

    def remove_non_avail_col_derived(self, cell):
        """
        See remove_non_avail_square_derived
        """
        cells_with_similar_avail_values = []

        for row in range(9):
            if cell.available_values == self.cells[row][cell.col].available_values:
                cells_with_similar_avail_values.append(self.cells[row][cell.col])
        if len(cells_with_similar_avail_values) == len(cell.available_values):
            for row in range(9):
                if self.cells[row][cell.col].value is None:
                    if self.cells[row][cell.col] not in cells_with_similar_avail_values:
                        for value in cell.available_values:
                            if value in self.cells[row][cell.col].available_values:
                                self.cells[row][cell.col].available_values.remove(value)


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
        cells_with_similar_avail_values = []
        for cell_in_square in cell.square_cells:
            if cell.available_values == cell_in_square.available_values:
                cells_with_similar_avail_values.append(cell_in_square)
        if len(cells_with_similar_avail_values) == len(cell.available_values):
            for cell_in_square in cell.square_cells:
                if cell_in_square not in cells_with_similar_avail_values:
                    for value in cell.available_values:
                        if value in cell_in_square.available_values:
                            cell_in_square.available_values.remove(value)

    def remove_non_available_values(self, cell, remove_type):
        removed = False
        if remove_type == "row":
            row = cell.row
            for col in range(9):
                removed_cell = self.remove_non_available_value(cell, row, col, remove_type)
                if removed_cell:
                    removed = True

        if remove_type == "col":
            col = cell.col
            for row in range(9):
                removed_cell = self.remove_non_available_value(cell, row, col, remove_type)
            if removed_cell:
                removed = True

        if remove_type == "square":
            for cell_in_square in cell.square_cells:
                removed_cell = self.remove_non_available_value(cell, cell_in_square.row,
                                                               cell_in_square.col, remove_type)
                if removed_cell:
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
                else:
                    cell.value = cell_input
                    cell.solved_step = 0
        self.update_all_available_values()


if __name__ == '__main__':
    # Todo: add instructions

    sudoku = Sudoku()
    # sudoku.load_puzzle(SudokuPuzzles.haaretz_20220311_medium)
    sudoku.load_puzzle(SudokuPuzzles.haaretz_20220401_medium)
    sudoku.run()

