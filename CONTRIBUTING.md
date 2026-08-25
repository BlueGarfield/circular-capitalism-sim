# Contributing

Thanks for helping build an open economic laboratory. Contributions of code,
tests, documentation, scenarios, and calibration work are all welcome.

## Development setup

```bash
git clone https://github.com/BlueGarfield/circular-capitalism-sim.git
cd circular-capitalism-sim
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Branch naming

- `feat/<short-description>` — new capability
- `fix/<short-description>` — bug fix
- `docs/<short-description>` — documentation only
- `calib/<short-description>` — calibration data/parameters

## Testing expectations

- `pytest` must pass locally before opening a PR.
- New mechanisms require tests, including at least one **accounting
  invariant** or **falsifiability** test where applicable.
- Same-seed reproducibility must not break.

## Formatting / linting

```bash
ruff check .
ruff format .
```

CI enforces both. Line length 100, Python 3.12 target.

## Proposing new policy scenarios

1. Add a YAML file under `scenarios/` with a `metadata.description`.
2. Document every new assumption in `docs/assumptions.md`.
3. Add the scenario to `tests/test_scenarios.py` expectations.
4. Open a PR using the "Research / model assumption proposal" issue first if
   the mechanism is nontrivial.

## Assumption documentation requirement

**All new parameters and behavioral mechanisms must be documented in
`docs/assumptions.md`.** Stylized parameters must never be presented as
empirical facts. Calibrated parameters must ship with source metadata
(dataset, vintage, retrieval date, transformation) per `docs/calibration.md`.

## Reproducibility expectations

- All randomness flows through the seeded generator.
- Results in issues/PRs must state: scenario file, seed(s), engine, package
  version, and — for any distributional claim — Monte Carlo run counts.
- Single-seed results are exploratory only.

## Scientific integrity

The model must remain capable of producing results that support, weaken, or
contradict the Circular Capitalism hypothesis. PRs that hard-code a policy
conclusion, disable adverse behavioral channels by default, or manipulate
chart scales will not be merged.
