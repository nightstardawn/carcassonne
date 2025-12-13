# carcassonne

This is the code for [this Computerphile video](https://www.youtube.com/watch?v=G6ZHUOSXZDo).

To run it:

1. Make sure you have Python installed, and [uv](https://docs.astral.sh/uv/getting-started/installation/) as well (this is used to build and run the code).

2. Run with `uv run main.py`

- Then press RETURN to do one step, or SPACE to toggle auto mode.
- Press D to turn on/off the information overlay.
- Press R to reset the deck.
- Press P to toggle between collapsing minimum entropy (default) and collapsing randomly weighted based on entropy.
  - The weighting for random mode is defined in `main.py`, a constant called `RANDOM_K`
  - In this mode, the relative likelihood of collapsing a cell with entropy `e` is defined to be `exp(-e * RANDOM_K)`.
  - Therefore a value of `-100` very strongly favours cells with *higher* entropy. Making `RANDOM_K` positive resembles the default behaviour where lower entropy cells are prioritised first to be collapsed.

Some potential issues when installing Pygame are addressed in [this issue](https://github.com/zac-garby/carcassonne/issues/1). If you run into some errors, this may be of use. Thanks @peardox!

## Wave functions

The wave functions and entropy definitions are defined in `wave_functions.py`. If you want to make your own, you should extend the `Extend[WF]` class. The implementations in that file show how this is done. This class also allows to to draw things for each cell and/or the whole board, if you like.

## Help?

Please reach out to me if you want to do something with this but don't know how to! Discord at `zacmg`, or email me at [zac.garby@nottingham.ac.uk](mailto:zac.garby@nottingham.ac.uk).
