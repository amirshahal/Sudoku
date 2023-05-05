import matplotlib.pyplot as plt
from skimage.io import imread
from skimage.measure import label, regionprops
from skimage.color import rgb2gray
from skimage.transform import resize
import numpy as np
from keras.models import load_model


class Digit:
    def __init__(self, min_row, max_row, min_col, max_col, pixels):
        self.min_row = min_row
        self.max_row = max_row
        self.min_col = min_col
        self.max_col = max_col
        self.pixels = pixels
        self.value = None
        self.row = int(max_row / 100)
        self.col = int(max_col / 100)
        self.image28 = resize(pixels, (18, 18))
        self.image28 = np.pad(self.image28, (5, 5), 'constant', constant_values=(1, 1))


class SudokuReader:
    def __init__(self, image_file):
        self.image_file = image_file
        self.sudoku_image = None
        self.digits = []
        self.count = 0
        self.model = load_model("mnist.h5")
        self.arr = None

    def run(self):
        self.get_digits()
        self.read_digits_to_array()

    def read_digits_to_array(self):
        self.arr = [[None for x in range(9)] for y in range(9)]
        for digit in sorted(self.digits, key=lambda x: x.row * 10 + x.col):
            f = digit.image28 * 255
            f = f.reshape(-1, 28, 28, 1)
            p = self.model.predict(f, verbose=False)
            digit.value = np.argmax(p)
            self.arr[digit.row][digit.col] = digit.value
        print(self.arr)

    def show_digits(self):
        for digit in sorted(self.digits, key=lambda x: x.row * 10 + x.col):
            f = digit.image28 * 255
            f = f.reshape(-1, 28, 28, 1)
            p = self.model.predict(f, verbose=False)
            p = np.argmax(p)
            print(f"Row= {digit.row}, Col= {digit.col}, Predicted label is {p}")
            # print(digit.image28.reshape(28, 28))
            plt.imshow(digit.image28.reshape(28, 28), cmap=plt.get_cmap('gray'))
            plt.show()

    def read_digits_src(self):
        fig, ax = plt.subplots(figsize=(5, 5))
        for digit in self.digits:
            bx = (digit.min_col, digit.max_col, digit.max_col, digit.min_col, digit.min_col)
            by = (digit.min_row, digit.min_row, digit.max_row, digit.max_row, digit.min_row)
            ax.plot(bx, by, '-r', linewidth=2)
        ax.set_title("Number of Box : {}".format(self.count))
        ax.imshow(self.sudoku_image, alpha=0.5)
        print("bp")

    def get_digits(self):
        self.sudoku_image = imread(self.image_file)
        self.sudoku_image = resize(self.sudoku_image, (900, 900), anti_aliasing=True)[:, :, :3]

        # Making binary
        bin_image = rgb2gray(self.sudoku_image) > 0.3
        label_im = label(bin_image, background=1)
        grey_image = rgb2gray(self.sudoku_image)

        # Region Props
        regions = regionprops(label_im)
        # fig, ax = plt.subplots(figsize=(5, 5))
        self.count = 0
        for props in regions:
            min_r, min_c, max_r, max_c = props.bbox
            area = (max_r - min_r) * (max_c - min_c)
            # Filtering Box by Area
            if 500 < area < 4000:
                # bx = (min_c, max_c, max_c, min_c, min_c)
                # by = (min_r, min_r, max_r, max_r, min_r)
                # ax.plot(bx, by, '-r', linewidth=2)
                self.count += 1
                print(f"Digit #{self.count} is at ({min_r},{min_c}) to ({max_r},{max_c})")
                digit = Digit(min_r, max_r, min_c, max_c, grey_image[min_r:max_r, min_c:max_c])
                self.digits.append(digit)

        # ax.set_title("Number of Box : {}".format(count))
        # ax.imshow(image, alpha=0.5)


sudoku_reader = SudokuReader('SudokuPuzzle1.png')
sudoku_reader.run()
