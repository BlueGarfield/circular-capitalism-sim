# Web companions

Zero-infrastructure, single-file HTML companions to the simulator. Both run a
simplified JavaScript port of the vectorized engine (same period sequence,
cohorts, and seeded RNG discipline) entirely in the browser.

- `lab.html` — scenario comparison charts with policy sliders and a custom scenario.
- `society.html` — isometric "overhead society" view: building height = wealth,
  amber glow = deferred gains, blue band = asset-backed debt, sparks = realizations,
  green pulse = citizen dividends.

These are for intuition and demos. They are **not** the evidence-grade path:
no accounting-invariant checker, single seed, no firm sector. Use
`ccsim-batch` for research runs. All outputs are illustrative synthetic
results under stylized, uncalibrated assumptions.
