# 15 Tile Puzzle Game for Numworks Calculator
## Overview

This is a classic 15-tile sliding puzzle game developed for the Numworks calculator. The game includes image compression using a custom implementation of the LZ77 algorithm tailored to work efficiently with the Numworks calculator constraints, with images encoded in base64 and stored in a 16-color palette. The color palette is uncompressed for ease of rendering. Images are 108x108 and enlarged to 216x216 when displaying them.

## Features:

- 4x4 sliding puzzle where the player arranges tiles in sequence by sliding them into an empty space.
- Performs a Fisher–Yates tile shuffling and checks solvability of the shuffled puzzle, making it always solvable.
- Displays match count for tiles in the correct position.
- When the puzzle is successfully completed a "SOLVED!!!" message is displayed.

## Code Structure

The main classes and functions are:

The main classes and functions are:
- **`TP` (Tile Properties)**: Encodes properties for tiles, such as width and length, for decompression and display.
- **`SW` (Sliding Window)**: Manages the sliding window for decompression.
- **`TI` (Tile Image)**: Handles decompression and display of tile images.
- **`dld`**: Decodes lengths and distances for image decompression.
- **`dc` (Decompression)**: Primary decompression function, which yields bytes for tiles.
- **`fb64`**: Base64 decoding for the compressed tile images.
- **Tile Drawing and Shuffling Functions**:
  - `draw_tiles()`, `show_matches()`, `clear_tile()`, `shuffle()`, and `is_solvable()`: Handle tile arrangement, shuffling, solvability checks, and display.

## Installation and Usage

To use this game on your Numworks calculator, load the Python code file into your calculator from the Numworks website. The game works with the ion and kandinsky libraries for PC as well. To work on the Numworks, the only modifications are to remove the lambda function and to change the constant to 1 instead of "int".

The game interface allows for the following interactions:

1. **Start and Shuffle**: Start the game and shuffle the tiles by pressing the **+ key**.
2. **Move Tiles**: Use the **arrow keys** to move the empty tile around.
3. **Check Matches**: The display shows how many tiles are in the correct position.
4. **Reset Puzzle**: Re-shuffle the puzzle at any time by pressing the **+ key** again.


## Puzzle Images

Here are the three puzzles included:

<div style="display: flex; justify-content: space-around; align-items: center;">

<div style="text-align: center;">
    <p><strong>Purple bunny puzzle</strong></p>
    <img src="img/purple_bunny.png" alt="Puzzle 1" width="216">
</div>

<div style="text-align: center;">
    <p><strong>Halloween puzzle</strong></p>
    <img src="img/jacko.png" alt="Puzzle 2" width="216">
</div>

<div style="text-align: center;">
    <p><strong>Autumn puzzle</strong></p>
    <img src="img/autumn.png" alt="Puzzle 3" width="216">
</div>

</div>