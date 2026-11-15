import pytest

from run_pipeline import STEPS, select_steps, split_batches


def keys(steps):
    return [s[0] for s in steps]


def test_all_steps_run_in_order_by_default():
    assert keys(select_steps(STEPS)) == ["load", "dq", "build", "views", "check"]


def test_start_at_a_later_step():
    assert keys(select_steps(STEPS, start="build")) == ["build", "views", "check"]


def test_skip_checks_removes_only_the_final_validation():
    assert keys(select_steps(STEPS, skip_checks=True)) == ["load", "dq", "build", "views"]


def test_unknown_start_step_is_rejected():
    with pytest.raises(ValueError, match="Unknown step"):
        select_steps(STEPS, start="deploy")


def test_sql_is_split_at_go_lines():
    sql = "SELECT 1;\nGO\nSELECT 2;\nGO\n"
    assert split_batches(sql) == ["SELECT 1;", "SELECT 2;"]


def test_go_is_not_case_sensitive_and_empty_batches_are_dropped():
    sql = "SELECT 1;\n go \n\nGO\nSELECT 2;"
    assert split_batches(sql) == ["SELECT 1;", "SELECT 2;"]


def test_comments_are_removed_before_splitting():
    sql = "/* what is this? */\nSELECT 1;\nGO\n"
    assert [b.strip() for b in split_batches(sql)] == ["SELECT 1;"]


# ------------------------------------------------------------ the whole run
def fake_steps(calls, fail_at=None):
    def make(name):
        def action():
            if name == fail_at:
                raise RuntimeError("boom")
            calls.append(name)
        return action
    return [(n, n.upper(), make(n), f"log {n}") for n in ("a", "b", "c")]


def test_a_failing_step_stops_the_run(monkeypatch, capsys):
    import run_pipeline
    calls = []
    monkeypatch.setattr(run_pipeline, "STEPS", fake_steps(calls, fail_at="b"))
    assert run_pipeline.main(["--from", "a"]) == 1
    assert calls == ["a"]
    assert "FAILED at step 'b'" in capsys.readouterr().out


def test_a_clean_run_returns_zero(monkeypatch):
    import run_pipeline
    calls = []
    monkeypatch.setattr(run_pipeline, "STEPS", fake_steps(calls))
    assert run_pipeline.main(["--from", "a"]) == 0
    assert calls == ["a", "b", "c"]