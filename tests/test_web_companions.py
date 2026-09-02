"""Regression tests for the dependency-free web companions and Pages workflow."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_chart_lab_labels_completed_periods():
    lab = (ROOT / "web/lab.html").read_text()

    assert "labels.push(((t+1)/12).toFixed(1));" in lab
    assert "labels.push((t/12).toFixed(1));" not in lab


def test_society_progress_uses_elapsed_animation_time():
    society = (ROOT / "web/society.html").read_text()

    assert "const elapsedSeconds=lastFrameTs===null?0:(ts-lastFrameTs)/1000;" in society
    assert "acc+=spd*2*elapsedSeconds;" in society
    assert "acc+=spd/60*2;" not in society


def test_pages_workflow_enforces_documented_setup():
    workflow = (ROOT / ".github/workflows/pages.yml").read_text()
    readme = (ROOT / "README.md").read_text()

    assert "Verify Pages configuration" in workflow
    assert '"https://api.github.com/repos/${GITHUB_REPOSITORY}/pages"' in workflow
    assert "set Source to GitHub Actions" in workflow
    assert "enablement: true" not in workflow
    assert "Settings > Pages" in readme
    assert "Source** to **GitHub Actions" in readme
