#!/usr/bin/env bash
# One-shot GitHub deployment for circular-capitalism-sim.
# Usage:  GITHUB_TOKEN=ghp_xxx ./deploy_github.sh
# Requires: git, curl, python3. Fine-grained PAT scoped to BlueGarfield with
# Administration (write), Contents (write), Pull requests (write), Workflows (write).
set -euo pipefail

OWNER="${OWNER:-BlueGarfield}"
REPO="${REPO:-circular-capitalism-sim}"
BRANCH="feat/circular-capitalism-v0.1"
API="https://api.github.com"
: "${GITHUB_TOKEN:?Set GITHUB_TOKEN to a fine-grained PAT}"
H=(-H "Authorization: Bearer $GITHUB_TOKEN" -H "Accept: application/vnd.github+json" -H "X-GitHub-Api-Version: 2022-11-28")

cd "$(dirname "$0")"
echo "== preflight"
pytest -q && ruff check . && ruff format --check .
git status --porcelain | grep -q . && { echo "Working tree not clean"; exit 1; }

echo "== repo"
if curl -sf "${H[@]}" "$API/repos/$OWNER/$REPO" >/dev/null; then
  echo "exists: $OWNER/$REPO (inspecting, not overwriting)"
  git ls-remote "https://github.com/$OWNER/$REPO" | head -3
  curl -sf "${H[@]}" -X PATCH "$API/repos/$OWNER/$REPO" -d '{"description":"Open-source agent-based economic simulator for studying tax deferral, unrealized gains, wealth concentration, capital circulation, and Circular Capitalism policy scenarios.","private":false}' >/dev/null || true
else
  # try org endpoint first, fall back to user endpoint
  BODY='{"name":"'$REPO'","description":"Open-source agent-based economic simulator for studying tax deferral, unrealized gains, wealth concentration, capital circulation, and Circular Capitalism policy scenarios.","private":false,"has_issues":true,"has_wiki":false}'
  curl -sf "${H[@]}" -X POST "$API/orgs/$OWNER/repos" -d "$BODY" >/dev/null \
    || curl -sf "${H[@]}" -X POST "$API/user/repos" -d "$BODY" >/dev/null
  echo "created public repo $OWNER/$REPO"
fi
curl -sf "${H[@]}" -X PUT "$API/repos/$OWNER/$REPO/topics" \
  -d '{"names":["circular-economy","economics","agent-based-modeling","mesa","python","wealth-inequality","taxation","capital-gains","economic-simulation","open-source"]}' >/dev/null \
  || echo "(topics skipped — set manually in repo settings)"

echo "== push"
git remote remove origin 2>/dev/null || true
git remote add origin "https://github.com/$OWNER/$REPO.git"

# Keep the PAT out of .git/config. The temporary askpass helper reads the
# token from the environment and is removed even when a push fails.
ASKPASS=$(mktemp)
cleanup() {
  rm -f "$ASKPASS"
}
trap cleanup EXIT
cat >"$ASKPASS" <<'EOF'
#!/usr/bin/env bash
case "$1" in
  *Username*) printf '%s\n' "x-access-token" ;;
  *Password*) printf '%s\n' "$GITHUB_TOKEN" ;;
  *) exit 1 ;;
esac
EOF
chmod 700 "$ASKPASS"

GIT_ASKPASS="$ASKPASS" GIT_TERMINAL_PROMPT=0 git push -u origin main
GIT_ASKPASS="$ASKPASS" GIT_TERMINAL_PROMPT=0 git push -u origin "$BRANCH"

echo "== pull request"
PR_BODY=$(cat <<'EOF'
## Circular Capitalism Simulator v0.1.0 — Deferral Engine

**Architecture:** Mesa 3.x ABM engine (staged AgentSet activation) + NumPy vectorized reference engine sharing one monthly period spec; per-period accounting-invariant checks (tax, transfer, cash, debt, asset, basis, realized-gain, government-budget identities); seeded reproducibility; Monte Carlo + one-at-a-time sensitivity runners; Streamlit dashboard.

**Scenarios:** 00 control · 01 persistent deferral · 02 deferral + asset-backed liquidity · 03 circular capitalism (deferral cap, deemed-realization threshold, dividends/public/community recirculation, behavioral responses enabled so it can underperform).

**Tests:** 43 passed — invariants every period of all four scenarios at full spec size; KPI known-array checks; same-seed reproducibility on both engines; 8 invalid-config cases; deferral generates no CG tax until realization; forced realization fires; borrowing is provably not a realization event; elasticity>0 reduces investment (falsifiability).

**Lint:** ruff check + format clean.

**Known limitations:** single asset class, no inflation, flat rates, no estate/step-up channel, no labor-supply response, simple firm sector, uncalibrated stylized parameters. Outputs are illustrative synthetic results, not empirical findings.
EOF
)
PR_JSON=$(python3 -c "import json,sys;print(json.dumps({'title':'feat: Circular Capitalism Simulator v0.1.0 (Deferral Engine)','head':'$BRANCH','base':'main','body':sys.stdin.read()}))" <<<"$PR_BODY")
PR=$(curl -sf "${H[@]}" -X POST "$API/repos/$OWNER/$REPO/pulls" -d "$PR_JSON")
PR_NUM=$(python3 -c "import json,sys;print(json.load(sys.stdin)['number'])" <<<"$PR")
PR_URL=$(python3 -c "import json,sys;print(json.load(sys.stdin)['html_url'])" <<<"$PR")
echo "PR: $PR_URL"

echo "== waiting for CI (up to 10 min)"
HEAD_SHA=$(git rev-parse "$BRANCH")
for i in $(seq 1 60); do
  RUNS=$(curl -sf "${H[@]}" "$API/repos/$OWNER/$REPO/actions/runs?head_sha=$HEAD_SHA&per_page=10")
  STATUS=$(python3 -c "
import json,sys
r=json.load(sys.stdin)['workflow_runs']
if len(r)<2: print('pending'); sys.exit()
if any(x['status']!='completed' for x in r): print('pending'); sys.exit()
print('green' if all(x['conclusion']=='success' for x in r) else 'red')" <<<"$RUNS")
  [ "$STATUS" = "green" ] && break
  [ "$STATUS" = "red" ] && { echo "CI failed — not merging. Inspect: https://github.com/$OWNER/$REPO/actions"; exit 1; }
  sleep 10
done
[ "$STATUS" = "green" ] || { echo "CI did not finish in time; merge manually when green."; exit 1; }
echo "CI green"

echo "== merge"
curl -sf "${H[@]}" -X PUT "$API/repos/$OWNER/$REPO/pulls/$PR_NUM/merge" \
  -d '{"merge_method":"merge","commit_title":"Merge v0.1.0: Circular Capitalism Simulator Deferral Engine"}' >/dev/null
git fetch origin main -q

echo "== release"
NOTES=$(cat <<'EOF'
Initial public release.

- Mesa 3.x agent-based engine with staged AgentSet activation
- NumPy vectorized reference engine for Monte Carlo and sensitivity analysis
- Four comparable policy scenarios (control, persistent deferral, deferral + asset-backed liquidity, circular capitalism)
- Exact cost-basis and unrealized-gain tracking with voluntary and forced/deemed realization
- Asset-backed liquidity model (borrowing is never a realization event)
- Circular Capitalism recirculation mechanism: deferral cap, deemed-realization threshold, citizen dividend, public and community capital — with behavioral responses enabled so the regime can underperform
- KPI suite: Gini, top shares, median wealth, Deferred Wealth Stock, Deferred Wealth Concentration, Effective Economic Tax Rate, Capital Recirculation Rate, Recirculation Gap
- Streamlit research dashboard
- 43 tests: per-period accounting invariants, KPI correctness, reproducibility, scenario validation, deferral and falsifiability mechanics
- Methodology, KPI, assumptions, calibration, and roadmap docs; white paper draft

Known limitations: single asset class, no inflation, flat tax rates, no estate/step-up channel, no labor-supply response, simple firm sector, uncalibrated stylized parameters. All outputs are illustrative synthetic results, not empirical findings.
EOF
)
REL_JSON=$(python3 -c "import json,sys;print(json.dumps({'tag_name':'v0.1.0','target_commitish':'main','name':'Circular Capitalism Simulator v0.1.0: Deferral Engine','body':sys.stdin.read()}))" <<<"$NOTES")
REL=$(curl -sf "${H[@]}" -X POST "$API/repos/$OWNER/$REPO/releases" -d "$REL_JSON")
REL_URL=$(python3 -c "import json,sys;print(json.load(sys.stdin)['html_url'])" <<<"$REL")

echo
echo "================ DONE ================"
echo "Repo:    https://github.com/$OWNER/$REPO"
echo "PR:      $PR_URL"
echo "Release: $REL_URL"
echo "Main:    $(git rev-parse origin/main)"
