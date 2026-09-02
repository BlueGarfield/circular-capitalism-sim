"""Security regression tests for the one-shot GitHub deployment helper."""

from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "deploy_github.sh"


def test_git_remote_never_persists_github_token():
    script = SCRIPT.read_text()

    assert "x-access-token:${GITHUB_TOKEN}@github.com" not in script
    assert 'git remote add origin "https://github.com/$OWNER/$REPO.git"' in script
    assert 'GIT_ASKPASS="$ASKPASS" GIT_TERMINAL_PROMPT=0 git push' in script
    assert "trap cleanup EXIT" in script
