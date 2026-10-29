"""Tests for speedup.py and tools/acelerar.py (no display or wx needed)."""
import builtins
import importlib
import os
import subprocess
import sys
import types
from unittest import mock

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.dirname(HERE)
ACELERAR = os.path.join(os.path.dirname(SRC), "tools", "acelerar.py")
sys.path.insert(0, SRC)

import speedup  # noqa: E402

# Capture written by atbswp before this change (no pyautogui.PAUSE line)
OLD_CAPTURE = """#!/bin/env python3
# Created by atbswp v0.3.1 (https://git.sr.ht/~rmpr/atbswp)
# on 29 Oct 2026
import pyautogui
import time
pyautogui.FAILSAFE = False

time.sleep(0.5)
pyautogui.moveTo(10, 10)
time.sleep(0.25)
pyautogui.moveTo(20, 20)
time.sleep(0.25)
pyautogui.moveTo(30, 30)
pyautogui.mouseDown(30, 30, 'left')
pyautogui.mouseUp(30, 30, 'left')
time.sleep(1.0)
pyautogui.keyDown('a')
time.sleep(0.01)
pyautogui.keyUp('a')
time.sleep(0.2)
pyautogui.moveTo(40, 40)
time.sleep(0.4)"""


def run(lines):
    """Execute a capture with fake pyautogui/time, return (calls, total sleep)."""
    calls = []
    slept = []
    fake_gui = types.SimpleNamespace(PAUSE=0.1, FAILSAFE=True)
    for name in ("moveTo", "mouseDown", "mouseUp", "keyDown", "keyUp", "press", "scroll"):
        setattr(fake_gui, name, lambda *a, _n=name: calls.append((_n,) + a))
    fake_time = types.SimpleNamespace(sleep=slept.append)
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        return {"pyautogui": fake_gui, "time": fake_time}.get(name) or real_import(name, *args, **kwargs)

    env = {"__builtins__": dict(vars(builtins), __import__=fake_import)}
    for line in lines:
        exec(line, env)
    return calls, sum(slept), fake_gui.PAUSE


def actions(calls):
    return [c for c in calls if c[0] != "moveTo"]


def test_old_capture_still_runs_unchanged():
    calls, slept, pause = run(OLD_CAPTURE.splitlines())
    assert len(calls) == 8
    assert slept == pytest.approx(2.61)
    assert pause == 0.1


def test_speed_divides_sleeps_and_keeps_every_action():
    lines = speedup.transform(OLD_CAPTURE.splitlines(), speed=2, min_wait=0)
    calls, slept, pause = run(lines)
    original_calls, _, _ = run(OLD_CAPTURE.splitlines())
    assert calls == original_calls
    assert slept == pytest.approx(2.61 / 2)
    assert pause == 0


def test_pause_line_written_once_after_import():
    lines = speedup.transform(OLD_CAPTURE.splitlines() + ["pyautogui.PAUSE = 0.1"], speed=3)
    assert lines.count(speedup.PAUSE_LINE) == 1
    assert lines.index(speedup.PAUSE_LINE) == lines.index("import pyautogui") + 1
    assert "pyautogui.PAUSE = 0.1" not in lines


def test_transform_twice_is_stable():
    once = speedup.transform(OLD_CAPTURE.splitlines(), speed=3, skip_moves=True)
    twice = speedup.transform(once, speed=1, skip_moves=True, min_wait=0)
    assert run(once)[0] == run(twice)[0]
    assert run(once)[1] == pytest.approx(run(twice)[1])


def test_skip_moves_keeps_only_last_position_before_action():
    lines = speedup.transform(OLD_CAPTURE.splitlines(), skip_moves=True, min_wait=0)
    calls, slept, _ = run(lines)
    assert calls == [
        ("moveTo", 30, 30),
        ("mouseDown", 30, 30, "left"),
        ("mouseUp", 30, 30, "left"),
        ("keyDown", "a"),
        ("keyUp", "a"),
        ("moveTo", 40, 40),  # final position at the end is kept too
    ]
    # The waits of the skipped moves are not lost (page loads, menus...)
    assert slept == pytest.approx(2.61)
    # Hover first, then wait, then click
    i = lines.index("pyautogui.moveTo(30, 30)")
    assert lines[i + 1] == "time.sleep(1.0)"
    assert lines[i + 2] == "pyautogui.mouseDown(30, 30, 'left')"


def test_min_wait_before_actions_only():
    lines = speedup.transform(OLD_CAPTURE.splitlines(), speed=1000, min_wait=0.05)
    waits = []
    for i, line in enumerate(lines):
        if line.startswith("time.sleep("):
            waits.append((float(line[11:-1]), lines[i + 1] if i + 1 < len(lines) else ""))
    before_actions = [w for w, nxt in waits if nxt.startswith("pyautogui.") and "moveTo" not in nxt]
    before_moves = [w for w, nxt in waits if "moveTo" in nxt]
    # mouseDown, mouseUp, keyDown, keyUp
    assert len(before_actions) == 4
    assert all(w >= 0.05 for w in before_actions)
    assert all(w < 0.05 for w in before_moves)


def test_invalid_values():
    with pytest.raises(ValueError):
        speedup.transform([], speed=0)
    with pytest.raises(ValueError):
        speedup.transform([], min_wait=-1)


def test_capture_without_header_gets_imports():
    lines = speedup.transform(["time.sleep(1)", "pyautogui.press('a')"], speed=2, min_wait=0)
    assert lines[:3] == ["import pyautogui", "import time", speedup.PAUSE_LINE]
    assert run(lines)[:2] == ([("press", "a")], pytest.approx(0.5))


# --- tools/acelerar.py ----------------------------------------------------

def acelerar(*args):
    return subprocess.run([sys.executable, ACELERAR, *args], capture_output=True, text=True)


@pytest.fixture
def capture(tmp_path):
    path = tmp_path / "gravacao.py"
    path.write_text(OLD_CAPTURE + "\n", encoding="utf-8")
    return path


def test_cli_creates_copy_and_keeps_original(capture):
    before = capture.read_bytes()
    result = acelerar(str(capture), "--velocidade", "3", "--sem-movimentos")
    assert result.returncode == 0, result.stderr
    out = capture.with_name("gravacao_3x_sem-movimentos.py")
    assert out.exists()
    assert capture.read_bytes() == before
    text = out.read_text(encoding="utf-8")
    compile(text, str(out), "exec")
    assert speedup.PAUSE_LINE in text
    calls, slept, _ = run(text.splitlines())
    assert len(actions(calls)) == 4
    assert len(calls) == 6


def test_cli_custom_output_and_min_wait(capture, tmp_path):
    out = tmp_path / "rapida.py"
    result = acelerar(str(capture), "--velocidade", "1000", "--espera-minima", "0.2", "-o", str(out))
    assert result.returncode == 0, result.stderr
    _, slept, _ = run(out.read_text(encoding="utf-8").splitlines())
    assert slept >= 4 * 0.2


def test_cli_refuses_to_overwrite_original(capture):
    before = capture.read_bytes()
    for extra in ([], ["--forcar"]):
        result = acelerar(str(capture), "--velocidade", "2", "-o", str(capture), *extra)
        assert result.returncode != 0
        assert "original" in result.stderr
    assert capture.read_bytes() == before


def test_cli_refuses_existing_output_without_forcar(capture):
    out = capture.with_name("gravacao_2x.py")
    out.write_text("x", encoding="utf-8")
    assert acelerar(str(capture), "--velocidade", "2").returncode != 0
    assert out.read_text(encoding="utf-8") == "x"
    assert acelerar(str(capture), "--velocidade", "2", "--forcar").returncode == 0
    assert out.read_text(encoding="utf-8") != "x"


@pytest.mark.parametrize("args", [["--velocidade", "0"], ["--velocidade", "-2"], ["--espera-minima", "-1"]])
def test_cli_rejects_invalid_values(capture, args):
    assert acelerar(str(capture), *args).returncode == 2


def test_cli_missing_file(tmp_path):
    assert acelerar(str(tmp_path / "nao_existe.py")).returncode == 2


def test_cli_reads_cp1252_capture(tmp_path):
    # atbswp writes captures in the system encoding (cp1252 on Windows)
    path = tmp_path / "acentos.py"
    path.write_bytes((OLD_CAPTURE + "\npyautogui.keyDown('ç')\n").encode("cp1252"))
    with mock.patch("locale.getpreferredencoding", return_value="cp1252"):
        sys.path.insert(0, os.path.dirname(ACELERAR))
        try:
            ferramenta = importlib.import_module("acelerar")
        finally:
            sys.path.pop(0)
        assert ferramenta.main([str(path), "--velocidade", "2"]) == 0
    out = tmp_path / "acentos_2x.py"
    assert "pyautogui.keyDown('ç')" in out.read_bytes().decode("cp1252")


# --- recording: removal of the click/key that stopped the recording -------

@pytest.fixture
def record_ctrl(monkeypatch):
    """A RecordCtrl-like object, importing control.py with stubbed GUI libs."""
    for name in ("pyautogui", "pynput", "pynput.keyboard", "pynput.mouse", "wx", "wx.adv",
                 "wx.lib", "wx.lib.newevent", "custom_widgets"):
        monkeypatch.setitem(sys.modules, name, mock.MagicMock())
    monkeypatch.delitem(sys.modules, "control", raising=False)
    sys.modules["pyautogui"].position.return_value = (0, 0)
    control = importlib.import_module("control")
    ctrl = control.RecordCtrl()
    ctrl.control = control
    ctrl.remove = ctrl.remove_stop_trigger
    yield ctrl
    sys.modules.pop("control", None)


@pytest.mark.parametrize("trigger", [
    # press and release recorded
    ["time.sleep(0.3)", "pyautogui.mouseDown(1, 1, 'left')", "time.sleep(0.1)", "pyautogui.mouseUp(1, 1, 'left')"],
    # release not recorded yet
    ["time.sleep(0.3)", "pyautogui.mouseDown(1, 1, 'left')"],
    ["time.sleep(0.3)", "pyautogui.keyDown('f9')", "time.sleep(0.1)", "pyautogui.keyUp('f9')"],
    ["time.sleep(0.3)", "pyautogui.keyDown('f9')"],
])
def test_stop_trigger_removed_without_losing_real_actions(record_ctrl, trigger):
    body = ["HEADER", "time.sleep(1)", "pyautogui.keyDown('a')", "time.sleep(0.1)", "pyautogui.keyUp('a')"]
    record_ctrl._capture = body + trigger
    record_ctrl.remove()
    # The wait before reaching the stop button stays (time between repeats)
    assert record_ctrl._capture == body + ["time.sleep(0.3)"]


def test_stop_trigger_never_removes_header(record_ctrl):
    record_ctrl._capture = ["HEADER", "time.sleep(0.3)"]
    record_ctrl.remove()
    assert record_ctrl._capture == ["HEADER"]


# --- recording: mouse wheel ------------------------------------------------

@pytest.mark.parametrize("windows, expected", [
    (False, ["pyautogui.scroll(-1, 300, 400)", "pyautogui.scroll(2, 300, 400)", "pyautogui.hscroll(1, 300, 400)"]),
    # pyautogui on Windows: 120 per wheel notch, and no real horizontal scroll
    (True, ["pyautogui.scroll(-120, 300, 400)", "pyautogui.scroll(240, 300, 400)"]),
])
def test_scroll_records_wheel_notches(record_ctrl, monkeypatch, windows, expected):
    monkeypatch.setattr(record_ctrl.control, "WINDOWS", windows)
    record_ctrl.recording = True
    record_ctrl.last_time = 0
    record_ctrl._capture = ["HEADER"]
    record_ctrl.on_scroll(300, 400, 0, -1)
    record_ctrl.on_scroll(300, 400, 0, 2)
    record_ctrl.on_scroll(300, 400, 1, 0)
    assert [l for l in record_ctrl._capture if l.startswith("pyautogui.")] == expected
    # Every scroll gets its delay, and the speed-up still treats it as an action
    lines = speedup.transform(record_ctrl._capture, speed=2, min_wait=0)
    assert [l for l in lines if "scroll(" in l] == expected


# --- extra speeds ----------------------------------------------------------

def test_speed_labels():
    assert [speedup.speed_label(s) for s in speedup.SPEEDS] == \
        ["1x", "2x", "3x", "5x", "10x", "20x", "50x", "max"]
    assert speedup.speed_label(2.5) == "2.5x"


def test_max_speed_keeps_only_min_wait():
    lines = speedup.transform(OLD_CAPTURE.splitlines(), speed=speedup.MAX_SPEED, min_wait=0.05)
    calls, slept, _ = run(lines)
    assert calls == run(OLD_CAPTURE.splitlines())[0]
    # mouseDown, mouseUp, keyDown, keyUp: 4 * 0.05, nothing else
    assert slept == pytest.approx(4 * 0.05)


def test_max_speed_survives_the_config(tmp_path):
    import configparser
    config = configparser.ConfigParser()
    config["DEFAULT"]["Playback Speed"] = str(speedup.MAX_SPEED)
    assert config.getfloat("DEFAULT", "Playback Speed") == speedup.MAX_SPEED


@pytest.mark.parametrize("value, name", [("max", "gravacao_max.py"), ("50", "gravacao_50x.py")])
def test_cli_extra_speeds(capture, value, name):
    result = acelerar(str(capture), "--velocidade", value)
    assert result.returncode == 0, result.stderr
    out = capture.with_name(name)
    compile(out.read_text(encoding="utf-8"), str(out), "exec")
