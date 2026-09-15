# Potencia-1

Electrónica de Potencia coursework: rectifier analysis, a verified Python
solver library, and the LaTeX report for the T2 assignment.

## Structure

```
T2.pdf                     Assignment statement (5 rectifier exercises)
T2/
  main.tex                 LaTeX report (a=3, b=9, c=3), ready for Overleaf
  images/                  Generated waveform plots referenced by main.tex
  generate_plots.py        Regenerates the images from the verified solvers
scripts/
  dump_t2_values.py        Prints all T2 numeric results as JSON
  rectifiers/
    ex1_bridge_rl.py            Three-phase 6-pulse full-bridge rectifier
    ex2_three_phase_hw.py       Three-phase half-wave rectifier
    ex3_scr_hw_rl.py            Single-phase SCR half-wave controlled rectifier
    ex4_fullwave_controlled_rl.py  Single-phase full-wave controlled rectifier
tests/
  test_ex1..ex4_*.py        Pytest suites for each module
  conftest.py               Shared randomized-parameter fixtures
Main_report_2/, sample/    Earlier reference solutions used to match the
                            required derivation/report format
```

## Solver library

Each `scripts/rectifiers/exN_*.py` module exposes:

- `solve(...)` — closed-form analytic solution (Fourier series / transient RL
  response, matching the derivation style used in the report).
- `solve_numeric(...)` — an independent cross-check via direct numerical
  integration of the circuit's ODE (not a re-evaluation of the same formula),
  used only to validate `solve()`.

## Running the tests

```bash
pip install numpy scipy pytest
pytest tests/ -v
```

Tests check each module against hand-verified reference values plus
randomized `(R, L)` (and firing angle, where relevant) cases, asserting the
analytic and numeric solutions agree within a documented tolerance, and that
physical invariants hold (PF ≤ 1, η ≤ 1, RMS ≥ DC, etc.).

## Regenerating the report figures

```bash
python T2/generate_plots.py
```

## Compiling the report

`T2/main.tex` is self-contained with `T2/images/` — upload the `T2/` folder
to Overleaf (or compile locally with `pdflatex`/`latexmk`) to build the PDF.
