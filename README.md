# Potencia-1

Electrónica de Potencia coursework: rectifier analysis, a verified Python
solver library, and the LaTeX report for the T2 assignment.

## Structure

```
docs/
  assignment/              T2.pdf (statement), T2Clase.pdf (class notes)
  templates/               PlantillaEP.pdf (delivery guide), sample.tex
  examples/Main_report_2/  Earlier reference solution (report format)
T2/
  main.tex                 LaTeX report (a=3, b=9, c=3)
  generate_plots.py        Regenerates images/ex*_waveforms.png from the solvers
  images/                  Figures used by main.tex and solutions/
  solutions/               One .tex per exercise (taller_potencia_ej4/ej5)
  reference/               Velandia exercises 2 and 3 (study version) + formula sheet
  matlab/                  MATLAB scripts for exercise 5 (plots and simulation)
  simulink/                SCR_Puente_P5 Simscape model (.slx.zip) and screenshot
  drafts/                  Earlier R=15/L=38mH variants of exercises 4 and 5
Lab/Lab3/
  docs/                    Lab guide (controlled single-phase AC-DC converter)
  firmware/                ESP32-S3 Arduino sketch (zero-cross + SCR firing pulse)
  gui/                     PyQt6 serial GUI (python gui_disparo_scr.py)
scripts/
  dump_t2_values.py        Prints all T2 numeric results as JSON
  rectifiers/              Verified Python solvers (ex1..ex4)
tests/                     Pytest suites for each solver module
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

`T2/main.tex` uses `T2/images/` (run `generate_plots.py` first) — upload the `T2/` folder
to Overleaf (or compile locally with `pdflatex`/`latexmk`) to build the PDF.

## Lab 3 GUI

```bash
pip install PyQt6 pyserial
python Lab/Lab3/gui/gui_disparo_scr.py
```

Diagnostics are written to `Lab/Lab3/gui/gui_disparo_scr.log` (git-ignored).
