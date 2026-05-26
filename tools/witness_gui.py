#!/usr/bin/env python3
"""
tools/witness_gui.py — PySide6 GUI for the Witness asset pipeline.

Run:   python tools/witness_gui.py
Deps:  pip install PySide6
"""
from __future__ import annotations

import html
import re
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QSize, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QScrollBar,
    QSlider,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

REPO_ROOT         = Path(__file__).resolve().parent.parent
TEMPLATES_DIR     = REPO_ROOT / "prompts" / "asset-templates"
PROCESSED_GLB_DIR = REPO_ROOT / "processed" / "glb"
PROCESSED_GLB_RAW = PROCESSED_GLB_DIR / "raw"
PUBLIC_ASSETS_DIR = REPO_ROOT / "witness-interactive-vite" / "public" / "assets"
WITNESS_PY        = REPO_ROOT / "tools" / "witness.py"
COMFYUI_LOG       = Path("/tmp/comfyui.log")
HUNYUAN_CONTAINER = "witness-hunyuan"

# ── Discrete value lists ──────────────────────────────────────────────────────
TEXTURE_SIZES  = [512, 1024, 2048, 4096, 8192]
OCTREE_SIZES   = [256, 384, 512, 768]
ENSEMBLE_SIZES = [1, 2, 3, 5]
BAKE_SAMPLES   = [64, 128, 256, 512]

# ── Presets ───────────────────────────────────────────────────────────────────
# All integer slider values; floats stored as ints (guidance ×10, refine ×100,
# ai_denoise ×100) so they match LabeledSlider's integer interface.
PRESETS: dict[str, dict] = {
    "Draft": {
        "steps": 20, "octree_idx": 0, "guidance10": 50, "ensemble_idx": 0,
        "refine100": 30, "tex_idx": 2, "ai_denoise100": 62, "bake_idx": 0,
        "multi_view": False, "fast": True, "val_renders": False,
        "no_lods": True, "no_collision": True, "no_refine": False,
    },
    "Prop": {
        "steps": 50, "octree_idx": 2, "guidance10": 80, "ensemble_idx": 1,
        "refine100": 50, "tex_idx": 3, "ai_denoise100": 62, "bake_idx": 1,
        "multi_view": False, "fast": False, "val_renders": False,
        "no_lods": False, "no_collision": False, "no_refine": False,
    },
    "Figure": {
        "steps": 80, "octree_idx": 3, "guidance10": 80, "ensemble_idx": 1,
        "refine100": 50, "tex_idx": 4, "ai_denoise100": 65, "bake_idx": 1,
        "multi_view": True, "fast": False, "val_renders": False,
        "no_lods": False, "no_collision": False, "no_refine": False,
    },
    "Vegetation": {
        "steps": 50, "octree_idx": 2, "guidance10": 70, "ensemble_idx": 1,
        "refine100": 60, "tex_idx": 3, "ai_denoise100": 60, "bake_idx": 1,
        "multi_view": True, "fast": False, "val_renders": False,
        "no_lods": False, "no_collision": False, "no_refine": False,
    },
    "Structure": {
        "steps": 50, "octree_idx": 2, "guidance10": 60, "ensemble_idx": 1,
        "refine100": 40, "tex_idx": 4, "ai_denoise100": 55, "bake_idx": 1,
        "multi_view": False, "fast": False, "val_renders": False,
        "no_lods": False, "no_collision": False, "no_refine": False,
    },
    "Hero": {
        "steps": 80, "octree_idx": 3, "guidance10": 90, "ensemble_idx": 2,
        "refine100": 50, "tex_idx": 4, "ai_denoise100": 65, "bake_idx": 2,
        "multi_view": True, "fast": False, "val_renders": True,
        "no_lods": False, "no_collision": False, "no_refine": False,
    },
    # First-person hero hands from a single REAL dorsal photo: hero-tier mesh +
    # multi-view synthesis to fill the unseen angles, with stage-0.25 refine OFF
    # so the real reference is fed to Zero123++ untouched (refining it would
    # re-stylise the captured pose). See CHANGELOG 2026-05-26.
    "Hands": {
        "steps": 80, "octree_idx": 3, "guidance10": 90, "ensemble_idx": 2,
        "refine100": 50, "tex_idx": 4, "ai_denoise100": 65, "bake_idx": 2,
        "multi_view": True, "fast": False, "val_renders": True,
        "no_lods": False, "no_collision": False, "no_refine": True,
    },
}

# Map asset category prefix → preset name for auto-selection on asset click
CATEGORY_PRESET: dict[str, str] = {
    "prop":       "Prop",
    "figure":     "Figure",
    "vegetation": "Vegetation",
    "structure":  "Structure",
}

# Per-asset preset override (wins over CATEGORY_PRESET). The first-person hands
# are produced from a single real dorsal photo, so they default to the "Hands"
# preset (refine off, hero-tier multi-view) instead of the generic "Figure".
ASSET_PRESET: dict[str, str] = {
    "figure_grandfather_hands": "Hands",
}

# ANSI escape code stripper
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[mK]")


def _strip_ansi(s: str) -> str:
    return _ANSI_RE.sub("", s)


def _colorize_line(text: str) -> str:
    """Return an HTML-safe colored span for one console line."""
    t = _strip_ansi(text)
    escaped = html.escape(t)
    tl = t.lower()
    if any(k in tl for k in ("error", "failed", "fail:", "❌", "✗", "traceback", "exception")):
        color = "#f28b82"
    elif any(k in tl for k in ("warn", "⚠", "warning", "skipping", "skipped")):
        color = "#d7ba7d"
    elif any(k in tl for k in ("✅", "✓", "done", "success", "completed", "action=pass")):
        color = "#6ab187"
    elif any(k in tl for k in ("[gate]", "[step]", "[report]", "step ", "stage ", "━", "─")):
        color = "#9cdcfe"
    elif any(k in tl for k in ("attempt ", "seed ", "ensemble", "retry")):
        color = "#c586c0"
    else:
        color = "#cccccc"
    return f'<span style="color:{color};">{escaped}</span>'


# ── Asset scanning ────────────────────────────────────────────────────────────

def _has_ref(asset_id: str) -> bool:
    return (TEMPLATES_DIR / asset_id / "ref.png").exists()


def _has_glb(asset_id: str) -> bool:
    return (PROCESSED_GLB_DIR / f"{asset_id}.glb").exists()


def _has_textured_glb(asset_id: str) -> bool:
    return (PROCESSED_GLB_DIR / f"{asset_id}.textured.glb").exists()


def _has_raw_glb(asset_id: str) -> bool:
    raw      = PROCESSED_GLB_RAW / f"{asset_id}.glb"
    ensemble = PROCESSED_GLB_RAW / ".ensemble" / asset_id / f"{asset_id}.glb"
    return raw.exists() or ensemble.exists()


def _has_lods(asset_id: str) -> bool:
    return (
        (PROCESSED_GLB_DIR / f"{asset_id}.lod1.glb").exists()
        and (PROCESSED_GLB_DIR / f"{asset_id}.lod2.glb").exists()
    )


def _has_public_copy(asset_id: str) -> bool:
    return (PUBLIC_ASSETS_DIR / f"{asset_id}.glb").exists()


def _is_fully_complete(asset_id: str) -> bool:
    """All pipeline outputs present: final GLB, LODs, and public copy."""
    return _has_glb(asset_id) and _has_lods(asset_id) and _has_public_copy(asset_id)


def _can_post_process(asset_id: str) -> bool:
    """True when any GLB checkpoint exists but the pipeline outputs are incomplete."""
    if _is_fully_complete(asset_id):
        return False
    return _has_glb(asset_id) or _has_textured_glb(asset_id) or _has_raw_glb(asset_id)


def _scan_assets() -> list[str]:
    ids: list[str] = []
    if TEMPLATES_DIR.is_dir():
        for p in sorted(TEMPLATES_DIR.iterdir()):
            if p.is_dir() and not p.name.startswith("_"):
                ids.append(p.name)
    return ids


def _category_of(asset_id: str) -> str:
    return asset_id.split("_")[0] if "_" in asset_id else ""


# ── Worker thread ─────────────────────────────────────────────────────────────

class PipelineWorker(QThread):
    line_received: Signal = Signal(str)
    finished_ok:   Signal = Signal()
    finished_err:  Signal = Signal(int)

    def __init__(self, cmd: list[str]):
        super().__init__()
        self._cmd = cmd

    def run(self):
        proc = subprocess.Popen(
            self._cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=str(REPO_ROOT),
        )
        assert proc.stdout
        for line in proc.stdout:
            self.line_received.emit(line.rstrip())
        proc.wait()
        if proc.returncode == 0:
            self.finished_ok.emit()
        else:
            self.finished_err.emit(proc.returncode)


# ── Console window ────────────────────────────────────────────────────────────

class ConsoleWindow(QDialog):
    """Streaming pipeline log with ANSI-aware color coding."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Pipeline Console")
        self.resize(980, 540)
        self.setWindowFlags(
            self.windowFlags() | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint
        )

        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setFont(QFont("Monospace", 10))
        self._log.document().setMaximumBlockCount(5000)
        self._log.setStyleSheet(
            "QTextEdit { background: #0d0d0d; color: #cccccc; border: none; }"
        )

        clear_btn = QPushButton("Clear")
        clear_btn.setFixedWidth(80)
        clear_btn.clicked.connect(self._log.clear)

        self._error_banner = QLabel("")
        self._error_banner.setWordWrap(True)
        self._error_banner.setStyleSheet(
            "background:#3b1a1a; color:#f28b82; padding:6px 10px; "
            "border-radius:4px; font-size:12px;"
        )
        self._error_banner.hide()

        bottom = QHBoxLayout()
        bottom.setContentsMargins(0, 4, 0, 0)
        bottom.addStretch()
        bottom.addWidget(clear_btn)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(self._error_banner)
        layout.addWidget(self._log)
        layout.addLayout(bottom)

    def append(self, text: str):
        self._log.moveCursor(QTextCursor.End)
        self._log.insertHtml(_colorize_line(text) + "<br>")
        self._log.moveCursor(QTextCursor.End)

    def show_error_banner(self, msg: str):
        self._error_banner.setText(f"Pipeline error: {msg}")
        self._error_banner.show()

    def clear_error_banner(self):
        self._error_banner.hide()
        self._error_banner.setText("")


# ── Server log viewer ─────────────────────────────────────────────────────────

class ServerLogDialog(QDialog):
    """Shows the tail of ComfyUI log and Hunyuan docker logs."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Server Logs")
        self.resize(900, 600)
        self.setWindowFlags(
            self.windowFlags() | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint
        )

        self._comfy_log = QPlainTextEdit()
        self._comfy_log.setReadOnly(True)
        self._comfy_log.setFont(QFont("Monospace", 9))
        self._comfy_log.setStyleSheet(
            "QPlainTextEdit { background: #0d0d0d; color: #cccccc; border: none; }"
        )

        self._hunyuan_log = QPlainTextEdit()
        self._hunyuan_log.setReadOnly(True)
        self._hunyuan_log.setFont(QFont("Monospace", 9))
        self._hunyuan_log.setStyleSheet(
            "QPlainTextEdit { background: #0d0d0d; color: #cccccc; border: none; }"
        )

        splitter = QSplitter(Qt.Vertical)
        splitter.setHandleWidth(4)

        def _labeled(title: str, widget: QWidget) -> QWidget:
            w = QWidget()
            v = QVBoxLayout(w)
            v.setContentsMargins(0, 0, 0, 0)
            v.setSpacing(4)
            lbl = QLabel(title)
            lbl.setStyleSheet(
                "font-size:10px; font-weight:bold; letter-spacing:1px; color:#9cdcfe;"
            )
            v.addWidget(lbl)
            v.addWidget(widget)
            return w

        splitter.addWidget(_labeled("COMFYUI  (/tmp/comfyui.log)", self._comfy_log))
        splitter.addWidget(_labeled("HUNYUAN3D  (docker logs)", self._hunyuan_log))
        splitter.setSizes([300, 300])

        refresh_btn = QPushButton("↻  Refresh")
        refresh_btn.setFixedWidth(100)
        refresh_btn.clicked.connect(self.refresh)

        bottom = QHBoxLayout()
        bottom.setContentsMargins(0, 6, 0, 0)
        bottom.addStretch()
        bottom.addWidget(refresh_btn)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.addWidget(splitter)
        layout.addLayout(bottom)

        self.refresh()

    def refresh(self):
        self._comfy_log.setPlainText(self._read_comfyui_log())
        self._hunyuan_log.setPlainText(self._read_hunyuan_log())
        for w in (self._comfy_log, self._hunyuan_log):
            w.verticalScrollBar().setValue(w.verticalScrollBar().maximum())

    @staticmethod
    def _read_comfyui_log() -> str:
        if not COMFYUI_LOG.exists():
            return "(ComfyUI log not found — start ComfyUI first)"
        try:
            lines = COMFYUI_LOG.read_text(errors="replace").splitlines()
            return "\n".join(lines[-400:]) if len(lines) > 400 else "\n".join(lines)
        except OSError as exc:
            return f"(Could not read log: {exc})"

    @staticmethod
    def _read_hunyuan_log() -> str:
        try:
            result = subprocess.run(
                ["docker", "logs", "--tail", "200", HUNYUAN_CONTAINER],
                capture_output=True, text=True, timeout=8,
            )
            combined = (result.stdout + result.stderr).strip()
            if result.returncode != 0 and not result.stdout.strip():
                if "no such container" in combined.lower():
                    return (
                        f"Container '{HUNYUAN_CONTAINER}' is not running.\n\n"
                        "Start it from the GUI (▶ Start Servers) or:\n"
                        "  python tools/witness.py start --no-comfy"
                    )
                return f"docker logs returned exit {result.returncode}:\n{combined}"
            return combined or "(No output yet — container may still be loading)"
        except FileNotFoundError:
            return "(docker not found on PATH — is Docker installed?)"
        except subprocess.TimeoutExpired:
            return "(docker logs timed out after 8 s)"
        except Exception as exc:
            return f"(docker logs failed: {exc})"


# ── Labeled slider ────────────────────────────────────────────────────────────

class LabeledSlider(QWidget):
    def __init__(
        self,
        label: str,
        minimum: int,
        maximum: int,
        value: int,
        format_fn=None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._format = format_fn or (lambda v: str(v))

        name_lbl = QLabel(label)
        name_lbl.setStyleSheet("color: #d4d4d4; font-size: 12px;")
        self._val_lbl = QLabel(self._format(value))
        self._val_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._val_lbl.setMinimumWidth(64)
        self._val_lbl.setStyleSheet("color: #9cdcfe; font-weight: bold; font-size: 12px;")

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 2)
        top.addWidget(name_lbl)
        top.addStretch()
        top.addWidget(self._val_lbl)

        self._slider = QSlider(Qt.Horizontal)
        self._slider.setMinimum(minimum)
        self._slider.setMaximum(maximum)
        self._slider.setValue(value)
        self._slider.valueChanged.connect(lambda v: self._val_lbl.setText(self._format(v)))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(3)
        layout.addLayout(top)
        layout.addWidget(self._slider)

    @property
    def value(self) -> int:
        return self._slider.value()

    def set_value(self, v: int):
        self._slider.setValue(v)


# ── Preset button row ─────────────────────────────────────────────────────────

class PresetBar(QWidget):
    """Row of preset buttons; highlights the active one."""

    preset_applied: Signal = Signal(str)  # preset name

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._btns: dict[str, QPushButton] = {}
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        for name in PRESETS:
            btn = QPushButton(name)
            btn.setFixedHeight(26)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, n=name: self._on_click(n))
            self._btns[name] = btn
            row.addWidget(btn)
        row.addStretch()

    def _on_click(self, name: str):
        self._set_active(name)
        self.preset_applied.emit(name)

    def _set_active(self, name: str):
        for n, btn in self._btns.items():
            btn.setChecked(n == name)

    def set_preset(self, name: str):
        """Highlight the named preset without emitting the signal."""
        self._set_active(name)


# ── Status dot ────────────────────────────────────────────────────────────────

class StatusIndicator(QWidget):
    def __init__(self, name: str, parent: QWidget | None = None):
        super().__init__(parent)
        self._dot = QLabel("●")
        self._dot.setStyleSheet("color: #555; font-size: 16px;")
        self._lbl = QLabel(f"{name}: —")
        self._lbl.setStyleSheet("color: #888;")

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        row.addWidget(self._dot)
        row.addWidget(self._lbl)

        self._name  = name
        self._running: bool | None = None

    def set_running(self, running: bool) -> bool:
        changed = self._running != running
        self._running = running
        if running:
            self._dot.setStyleSheet("color: #4ec94e; font-size: 16px;")
            self._lbl.setText(f"{self._name}: running")
            self._lbl.setStyleSheet("color: #d4d4d4;")
        else:
            self._dot.setStyleSheet("color: #cc4444; font-size: 16px;")
            self._lbl.setText(f"{self._name}: stopped")
            self._lbl.setStyleSheet("color: #888;")
        return changed

    @property
    def is_running(self) -> bool:
        return bool(self._running)

    @property
    def was_ever_checked(self) -> bool:
        return self._running is not None


# ── Server warning banner ─────────────────────────────────────────────────────

class ServerWarningBanner(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._lbl = QLabel("")
        self._lbl.setWordWrap(True)
        self._lbl.setStyleSheet("color: #d7ba7d; font-size: 12px;")
        self._dismiss = QPushButton("✕")
        self._dismiss.setFixedSize(22, 22)
        self._dismiss.setStyleSheet(
            "QPushButton { background: transparent; color: #888; border: none; "
            "font-size: 14px; } QPushButton:hover { color: #d4d4d4; }"
        )
        self._dismiss.clicked.connect(self.hide)

        row = QHBoxLayout(self)
        row.setContentsMargins(10, 6, 6, 6)
        row.setSpacing(8)
        row.addWidget(self._lbl, 1)
        row.addWidget(self._dismiss)

        self.setStyleSheet("background: #2d2700; border-radius: 4px;")
        self.hide()

    def show_warning(self, msg: str):
        self._lbl.setText(msg)
        self.show()


# ── Dark stylesheet ───────────────────────────────────────────────────────────

DARK_QSS = """
QMainWindow, QDialog, QWidget {
    background: #1e1e1e;
    color: #d4d4d4;
    font-size: 13px;
    font-family: "Segoe UI", "SF Pro Text", sans-serif;
}
QListWidget {
    background: #252526;
    border: 1px solid #3c3c3c;
    border-radius: 4px;
    outline: none;
}
QListWidget::item { padding: 5px 8px; border-radius: 3px; }
QListWidget::item:selected { background: #094771; color: #ffffff; }
QListWidget::item:hover:!selected { background: #2a2d2e; }
QPushButton {
    background: #3c3c3c;
    border: none;
    border-radius: 4px;
    padding: 5px 12px;
    color: #d4d4d4;
}
QPushButton:hover   { background: #505050; }
QPushButton:pressed { background: #2a2a2a; }
QPushButton:disabled { color: #555; background: #2a2a2a; }
/* preset buttons */
QPushButton[checkable="true"] {
    background: #2d2d2d;
    color: #999;
    padding: 3px 10px;
    font-size: 12px;
}
QPushButton[checkable="true"]:hover  { background: #3a3a3a; color: #d4d4d4; }
QPushButton[checkable="true"]:checked {
    background: #094771;
    color: #ffffff;
    font-weight: bold;
}
QPushButton#start_btn  { background: #1b5e1b; color: #c8f0c8; }
QPushButton#start_btn:hover  { background: #246b24; }
QPushButton#stop_btn   { background: #5e1b1b; color: #f0c8c8; }
QPushButton#stop_btn:hover   { background: #6b2424; }
QPushButton#logs_btn   { background: #2a2a2a; color: #9cdcfe; }
QPushButton#logs_btn:hover   { background: #383838; }
QPushButton#gen_btn {
    background: #094771;
    color: #ffffff;
    font-weight: bold;
    padding: 8px 28px;
    font-size: 14px;
}
QPushButton#gen_btn:hover    { background: #0f6090; }
QPushButton#gen_btn:disabled { background: #252526; color: #555; }
QPushButton#post_btn {
    background: #2d4a1e;
    color: #b5e6a0;
    font-weight: bold;
    padding: 8px 18px;
    font-size: 13px;
}
QPushButton#post_btn:hover    { background: #3c6128; }
QPushButton#post_btn:disabled { background: #252526; color: #555; }
QSlider::groove:horizontal {
    height: 4px; background: #3c3c3c; border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #0078d4; width: 14px; height: 14px;
    margin: -5px 0; border-radius: 7px;
}
QSlider::sub-page:horizontal { background: #0078d4; border-radius: 2px; }
QCheckBox::indicator {
    width: 16px; height: 16px;
    border: 1px solid #555; border-radius: 3px; background: #252526;
}
QCheckBox::indicator:checked { background: #0078d4; border-color: #0078d4; }
QLabel#section_header {
    font-size: 10px; font-weight: bold;
    letter-spacing: 1.5px; color: #9cdcfe;
}
QLabel#sub_header {
    font-size: 10px; font-weight: bold;
    letter-spacing: 1px; color: #569cd6;
}
QFrame#divider {
    background: #3c3c3c; max-height: 1px; border: none;
}
QScrollBar:vertical { background: #252526; width: 10px; }
QScrollBar::handle:vertical {
    background: #424242; border-radius: 5px; min-height: 20px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollArea { border: none; }
"""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _section(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("sub_header")
    return lbl


def _divider() -> QFrame:
    f = QFrame()
    f.setObjectName("divider")
    f.setFrameShape(QFrame.HLine)
    return f


# ── Main window ───────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Witness  ·  Asset Pipeline")
        self.setMinimumSize(QSize(940, 660))

        self._worker: PipelineWorker | None = None
        self._server_worker: PipelineWorker | None = None
        self._console = ConsoleWindow(self)
        self._server_log_dialog: ServerLogDialog | None = None
        self._pipeline_running = False
        self._active_preset: str | None = None

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(10)

        # ── server bar ────────────────────────────────────────────────────────
        server_row = QHBoxLayout()
        server_row.setSpacing(12)

        self._comfy_status   = StatusIndicator("ComfyUI")
        self._hunyuan_status = StatusIndicator("Hunyuan3D")

        start_btn = QPushButton("▶  Start Servers")
        start_btn.setObjectName("start_btn")
        start_btn.setFixedHeight(32)
        stop_btn = QPushButton("■  Stop Servers")
        stop_btn.setObjectName("stop_btn")
        stop_btn.setFixedHeight(32)
        logs_btn = QPushButton("Logs")
        logs_btn.setObjectName("logs_btn")
        logs_btn.setFixedHeight(32)
        logs_btn.setToolTip("View ComfyUI and Hunyuan3D server logs")

        start_btn.clicked.connect(self._on_start_servers)
        stop_btn.clicked.connect(self._on_stop_servers)
        logs_btn.clicked.connect(self._on_view_logs)

        server_row.addWidget(self._comfy_status)
        server_row.addWidget(self._hunyuan_status)
        server_row.addStretch()
        server_row.addWidget(logs_btn)
        server_row.addWidget(start_btn)
        server_row.addWidget(stop_btn)
        root.addLayout(server_row)

        self._server_warn = ServerWarningBanner()
        root.addWidget(self._server_warn)
        root.addWidget(_divider())

        # ── main splitter ─────────────────────────────────────────────────────
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet("QSplitter::handle { background: #3c3c3c; }")

        # left — asset list
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 10, 0)
        ll.setSpacing(6)

        assets_hdr = QLabel("ASSETS")
        assets_hdr.setObjectName("section_header")
        ll.addWidget(assets_hdr)

        self._asset_list = QListWidget()
        self._asset_list.setSelectionMode(QListWidget.SingleSelection)
        self._asset_list.currentItemChanged.connect(self._on_selection_change)
        ll.addWidget(self._asset_list, 1)

        refresh_btn = QPushButton("↻  Refresh list")
        refresh_btn.setFixedHeight(28)
        refresh_btn.clicked.connect(self._populate_assets)
        ll.addWidget(refresh_btn)

        # right — scrollable settings panel
        right_outer = QWidget()
        right_outer.setMinimumWidth(320)
        right_outer_layout = QVBoxLayout(right_outer)
        right_outer_layout.setContentsMargins(10, 0, 0, 0)
        right_outer_layout.setSpacing(0)

        settings_hdr = QLabel("GENERATION SETTINGS")
        settings_hdr.setObjectName("section_header")
        right_outer_layout.addWidget(settings_hdr)
        right_outer_layout.addSpacing(6)

        # scrollable inner widget
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        inner = QWidget()
        rl = QVBoxLayout(inner)
        rl.setContentsMargins(2, 4, 8, 8)
        rl.setSpacing(2)

        # ── PRESETS ───────────────────────────────────────────────────────────
        rl.addWidget(_section("PRESET"))
        self._preset_bar = PresetBar()
        self._preset_bar.preset_applied.connect(self._apply_preset)
        rl.addWidget(self._preset_bar)
        rl.addSpacing(8)
        rl.addWidget(_divider())
        rl.addSpacing(6)

        # ── SHAPE (stage 1) ───────────────────────────────────────────────────
        rl.addWidget(_section("SHAPE  ·  STAGE 1"))
        rl.addSpacing(2)

        self._steps_slider = LabeledSlider(
            "Inference steps",
            minimum=10, maximum=100, value=50,
        )
        self._octree_slider = LabeledSlider(
            "Octree resolution",
            minimum=0, maximum=len(OCTREE_SIZES) - 1, value=2,
            format_fn=lambda i: str(OCTREE_SIZES[i]),
        )
        self._guidance_slider = LabeledSlider(
            "Guidance scale",
            minimum=30, maximum=120, value=80,
            format_fn=lambda v: f"{v / 10:.1f}",
        )
        self._ensemble_slider = LabeledSlider(
            "Ensemble size  (candidates)",
            minimum=0, maximum=len(ENSEMBLE_SIZES) - 1, value=1,
            format_fn=lambda i: str(ENSEMBLE_SIZES[i]),
        )
        for w in (self._steps_slider, self._octree_slider,
                  self._guidance_slider, self._ensemble_slider):
            rl.addWidget(w)

        rl.addSpacing(6)
        rl.addWidget(_divider())
        rl.addSpacing(6)

        # ── REFERENCE (stage 0.25) ────────────────────────────────────────────
        rl.addWidget(_section("REFERENCE  ·  STAGE 0.25  (FLUX.2)"))
        rl.addSpacing(2)

        self._refine_slider = LabeledSlider(
            "Refine strength",
            minimum=20, maximum=75, value=50,
            format_fn=lambda v: f"{v / 100:.2f}",
        )
        rl.addWidget(self._refine_slider)

        self._no_refine_check = QCheckBox(
            "Skip refine — use ref / real photo as-is  (--no-refine-ref)"
        )
        self._no_refine_check.setToolTip(
            "Skip the stage-0.25 FLUX.2 img2img pass. Turn ON when ref.png is a "
            "REAL photo you don't want re-stylised (e.g. the dorsal-hands "
            "capture) — the refine pass would drift the captured pose. The "
            "Refine strength slider above has no effect when this is checked."
        )
        self._no_refine_check.setStyleSheet("margin-top: 4px; color: #d4d4d4; font-size: 12px;")
        rl.addWidget(self._no_refine_check)

        # Real multi-view capture directory (overrides Zero123++ synthesis).
        rv_row = QHBoxLayout()
        rv_row.setSpacing(8)
        self._real_views_edit = QLineEdit()
        self._real_views_edit.setReadOnly(True)
        self._real_views_edit.setPlaceholderText(
            "Real views dir (optional) — overrides synthesis with real captures"
        )
        self._real_views_edit.setToolTip(
            "Point at a folder of REAL multi-angle photos to feed Hunyuan "
            "directly (Zero123++ synthesis is skipped). Leave empty to auto-use "
            "prompts/asset-templates/<id>/real_views/ when it exists. Each photo "
            "is background-removed + framed before use."
        )
        rv_browse = QPushButton("Browse…")
        rv_browse.setFixedHeight(26)
        rv_browse.clicked.connect(self._on_browse_real_views)
        rv_clear = QPushButton("✕")
        rv_clear.setFixedWidth(28)
        rv_clear.setFixedHeight(26)
        rv_clear.setToolTip("Clear the real-views directory.")
        rv_clear.clicked.connect(self._real_views_edit.clear)
        rv_row.addWidget(self._real_views_edit, 1)
        rv_row.addWidget(rv_browse)
        rv_row.addWidget(rv_clear)
        rl.addLayout(rv_row)

        rl.addSpacing(6)
        rl.addWidget(_divider())
        rl.addSpacing(6)

        # ── TEXTURE (stage 2) ─────────────────────────────────────────────────
        rl.addWidget(_section("TEXTURE  ·  STAGE 2  (BLENDER + FLUX.2)"))
        rl.addSpacing(2)

        self._tex_slider = LabeledSlider(
            "Texture size  (px)",
            minimum=0, maximum=len(TEXTURE_SIZES) - 1, value=3,
            format_fn=lambda i: f"{TEXTURE_SIZES[i]:,}",
        )
        self._ai_denoise_slider = LabeledSlider(
            "AI projection denoise",
            minimum=45, maximum=80, value=62,
            format_fn=lambda v: f"{v / 100:.2f}",
        )
        self._bake_slider = LabeledSlider(
            "Bake samples  (Cycles)",
            minimum=0, maximum=len(BAKE_SAMPLES) - 1, value=1,
            format_fn=lambda i: str(BAKE_SAMPLES[i]),
        )
        for w in (self._tex_slider, self._ai_denoise_slider, self._bake_slider):
            rl.addWidget(w)

        rl.addSpacing(6)
        rl.addWidget(_divider())
        rl.addSpacing(6)

        # ── OPTIONS ───────────────────────────────────────────────────────────
        rl.addWidget(_section("OPTIONS"))
        rl.addSpacing(4)

        self._multiview_check   = QCheckBox("Multi-view synthesis  (stage 0.5 Zero123++, +5 min)")
        self._fast_check        = QCheckBox("Fast mode  —  skip FLUX.2 AI projection  (stage 2b)")
        self._valrender_check   = QCheckBox("Validation renders  (turntable PNGs, +2 min)")

        opts_row = QHBoxLayout()
        opts_row.setSpacing(16)
        self._no_lods_check      = QCheckBox("Skip LODs")
        self._no_collision_check = QCheckBox("Skip collision")
        opts_row.addWidget(self._no_lods_check)
        opts_row.addWidget(self._no_collision_check)
        opts_row.addStretch()

        for w in (self._multiview_check, self._fast_check, self._valrender_check):
            w.setStyleSheet("margin-top: 4px; color: #d4d4d4; font-size: 12px;")
            rl.addWidget(w)
        rl.addSpacing(4)
        rl.addLayout(opts_row)

        rl.addStretch()
        scroll.setWidget(inner)
        right_outer_layout.addWidget(scroll, 1)

        splitter.addWidget(left)
        splitter.addWidget(right_outer)
        splitter.setSizes([400, 340])
        root.addWidget(splitter, 1)

        # ── footer ────────────────────────────────────────────────────────────
        root.addWidget(_divider())

        footer = QHBoxLayout()
        footer.setSpacing(12)

        self._gen_btn = QPushButton("▶  Generate")
        self._gen_btn.setObjectName("gen_btn")
        self._gen_btn.setFixedHeight(38)
        self._gen_btn.setEnabled(False)
        self._gen_btn.clicked.connect(self._on_generate)

        self._post_btn = QPushButton("⚙  Post-process")
        self._post_btn.setObjectName("post_btn")
        self._post_btn.setFixedHeight(38)
        self._post_btn.setEnabled(False)
        self._post_btn.setToolTip(
            "Optimize + export an already-generated mesh without re-running Hunyuan.\n"
            "Enabled when a textured or raw GLB exists but the final GLB is missing."
        )
        self._post_btn.clicked.connect(self._on_post_process)

        self._status_lbl = QLabel("Select an asset from the list.")
        self._status_lbl.setStyleSheet("color: #888;")

        console_btn = QPushButton("Console ↗")
        console_btn.setFixedHeight(38)
        console_btn.clicked.connect(self._console.show)
        console_btn.clicked.connect(self._console.raise_)

        footer.addWidget(self._gen_btn)
        footer.addWidget(self._post_btn)
        footer.addWidget(self._status_lbl, 1)
        footer.addWidget(console_btn)
        root.addLayout(footer)

        self.setStyleSheet(DARK_QSS)

        self._populate_assets()
        self._apply_preset("Prop")  # sensible default

        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll_servers)
        self._poll_timer.start(6000)
        self._poll_servers()

    # ── preset application ────────────────────────────────────────────────────

    def _apply_preset(self, name: str):
        p = PRESETS[name]
        self._steps_slider.set_value(p["steps"])
        self._octree_slider.set_value(p["octree_idx"])
        self._guidance_slider.set_value(p["guidance10"])
        self._ensemble_slider.set_value(p["ensemble_idx"])
        self._refine_slider.set_value(p["refine100"])
        self._tex_slider.set_value(p["tex_idx"])
        self._ai_denoise_slider.set_value(p["ai_denoise100"])
        self._bake_slider.set_value(p["bake_idx"])
        self._multiview_check.setChecked(p["multi_view"])
        self._fast_check.setChecked(p["fast"])
        self._valrender_check.setChecked(p["val_renders"])
        self._no_lods_check.setChecked(p["no_lods"])
        self._no_collision_check.setChecked(p["no_collision"])
        self._no_refine_check.setChecked(p.get("no_refine", False))
        self._preset_bar.set_preset(name)
        self._active_preset = name

    # ── server health ─────────────────────────────────────────────────────────

    def _check_comfy(self) -> bool:
        try:
            import urllib.request
            urllib.request.urlopen("http://localhost:8188/system_stats", timeout=3)
            return True
        except Exception:
            return False

    def _check_hunyuan(self) -> bool:
        try:
            import urllib.request
            urllib.request.urlopen("http://localhost:8081/docs", timeout=3)
            return True
        except Exception:
            return False

    def _poll_servers(self):
        comfy_now   = self._check_comfy()
        hunyuan_now = self._check_hunyuan()
        comfy_changed   = self._comfy_status.set_running(comfy_now)
        hunyuan_changed = self._hunyuan_status.set_running(hunyuan_now)

        if self._pipeline_running:
            msgs: list[str] = []
            if comfy_changed and not comfy_now:
                msgs.append("ComfyUI stopped — AI stages will fail.")
            if hunyuan_changed and not hunyuan_now:
                msgs.append("Hunyuan3D stopped — mesh generation will fail.")
            if msgs:
                self._server_warn.show_warning("  ".join(msgs))
                self._console.append("[SERVER] " + "  ".join(msgs))

    # ── server log viewer ─────────────────────────────────────────────────────

    def _on_view_logs(self):
        if self._server_log_dialog is None:
            self._server_log_dialog = ServerLogDialog(self)
        else:
            self._server_log_dialog.refresh()
        self._server_log_dialog.show()
        self._server_log_dialog.raise_()

    # ── asset list ────────────────────────────────────────────────────────────

    def _populate_assets(self):
        saved_id: str | None = None
        if ci := self._asset_list.currentItem():
            saved_id = ci.data(Qt.UserRole)

        self._asset_list.clear()
        for asset_id in _scan_assets():
            if _is_fully_complete(asset_id):
                icon, tip = "🟢", "complete — GLB + LODs + public copy ready"
            elif _can_post_process(asset_id):
                icon, tip = "🔵", "mesh ready — click Post-process to optimize + export"
            elif _has_ref(asset_id):
                icon, tip = "🟡", "ref image ready — waiting for generation"
            else:
                icon, tip = "⬜", "no ref image yet"

            item = QListWidgetItem(f"  {icon}  {asset_id}")
            item.setData(Qt.UserRole, asset_id)
            item.setToolTip(tip)
            self._asset_list.addItem(item)

        if saved_id:
            for i in range(self._asset_list.count()):
                if self._asset_list.item(i).data(Qt.UserRole) == saved_id:
                    self._asset_list.setCurrentRow(i)
                    break

    def _on_selection_change(self, current, _prev):
        busy = self._worker is not None and self._worker.isRunning()
        self._gen_btn.setEnabled(current is not None and not busy)
        if current:
            asset_id = current.data(Qt.UserRole)
            tip = current.toolTip()
            self._status_lbl.setText(f"{asset_id}  —  {tip}")
            self._status_lbl.setStyleSheet("color: #d4d4d4;")
            self._post_btn.setEnabled(not busy and _can_post_process(asset_id))
            # Auto-apply the matching preset (per-asset override > category).
            cat = _category_of(asset_id)
            suggested = ASSET_PRESET.get(asset_id) or CATEGORY_PRESET.get(cat)
            if suggested and suggested != self._active_preset:
                self._apply_preset(suggested)
            # Surface the asset's real-views capture dir if it ships one. The
            # pipeline auto-detects it too, but showing it makes the override
            # explicit; an empty field falls back to that auto-detection.
            rv_dir = TEMPLATES_DIR / asset_id / "real_views"
            has_caps = rv_dir.is_dir() and any(
                f.is_file() and f.suffix.lower() in (".png", ".jpg", ".jpeg")
                for f in rv_dir.iterdir()
            )
            self._real_views_edit.setText(str(rv_dir) if has_caps else "")
        else:
            self._post_btn.setEnabled(False)
            self._status_lbl.setText("Select an asset from the list.")
            self._status_lbl.setStyleSheet("color: #888;")

    # ── server management ─────────────────────────────────────────────────────

    def _spawn_server_cmd(self, args: list[str]):
        self._console.show()
        cmd = [sys.executable, "-u", str(WITNESS_PY)] + args
        self._console.append(f"\n$ {' '.join(cmd)}")
        self._server_worker = PipelineWorker(cmd)
        self._server_worker.line_received.connect(self._console.append)
        self._server_worker.finished_ok.connect(self._on_server_cmd_done)
        self._server_worker.finished_err.connect(self._on_server_cmd_done)
        self._server_worker.start()
        self._fast_poll_timer = QTimer(self)
        self._fast_poll_timer.timeout.connect(self._poll_servers)
        self._fast_poll_timer.start(2000)

    def _on_server_cmd_done(self, *_):
        if hasattr(self, "_fast_poll_timer"):
            self._fast_poll_timer.stop()
        self._poll_servers()

    def _on_start_servers(self):
        self._server_warn.hide()
        self._spawn_server_cmd(["start", "--no-wait"])

    def _on_stop_servers(self):
        self._spawn_server_cmd(["stop"])

    # ── pre-flight ────────────────────────────────────────────────────────────

    def _preflight_server_warning(self, asset_id: str) -> str | None:
        parts: list[str] = []
        if not self._hunyuan_status.is_running:
            parts.append(
                "Hunyuan3D is not running — mesh generation will fail at stage 1. "
                "Click Start Servers first."
            )
        if not self._comfy_status.is_running:
            parts.append(
                "ComfyUI is not running — AI stages (ref gen, FLUX.2 refine, "
                "FLUX.2 projection) will be skipped; pipeline proceeds with procedural textures."
            )
        return "  ".join(parts) if parts else None

    # ── generation ────────────────────────────────────────────────────────────

    def _on_browse_real_views(self):
        item = self._asset_list.currentItem()
        start = str(TEMPLATES_DIR)
        if item:
            cand = TEMPLATES_DIR / item.data(Qt.UserRole)
            if cand.is_dir():
                start = str(cand)
        chosen = QFileDialog.getExistingDirectory(
            self, "Select real multi-view capture directory", start
        )
        if chosen:
            self._real_views_edit.setText(chosen)

    def _on_generate(self):
        item = self._asset_list.currentItem()
        if not item:
            return

        asset_id: str = item.data(Qt.UserRole)

        # Read all settings
        steps        = self._steps_slider.value
        octree       = OCTREE_SIZES[self._octree_slider.value]
        guidance     = self._guidance_slider.value / 10.0
        ensemble     = ENSEMBLE_SIZES[self._ensemble_slider.value]
        refine       = self._refine_slider.value / 100.0
        tex_size     = TEXTURE_SIZES[self._tex_slider.value]
        ai_denoise   = self._ai_denoise_slider.value / 100.0
        bake_samples = BAKE_SAMPLES[self._bake_slider.value]
        multi_view   = self._multiview_check.isChecked()
        fast         = self._fast_check.isChecked()
        val_renders  = self._valrender_check.isChecked()
        no_lods      = self._no_lods_check.isChecked()
        no_collision = self._no_collision_check.isChecked()
        no_refine    = self._no_refine_check.isChecked()
        real_views   = self._real_views_edit.text().strip()

        warning = self._preflight_server_warning(asset_id)
        if warning:
            self._server_warn.show_warning(f"Pre-flight: {warning}")
            self._console.show()
            self._console.append(f"[PRE-FLIGHT] {warning}")
        else:
            self._server_warn.hide()
        self._console.clear_error_banner()

        cmd = [
            sys.executable, "-u", str(WITNESS_PY),
            "generate", asset_id,
            "--steps",          str(steps),
            "--octree-resolution", str(octree),
            "--guidance-scale", str(guidance),
            "--ensemble-size",  str(ensemble),
            "--refine-strength", str(refine),
            "--texture-size",   str(tex_size),
            "--ai-project-denoise", str(ai_denoise),
            "--bake-samples",   str(bake_samples),
        ]
        if multi_view:
            cmd.append("--multi-view")
        if fast:
            cmd.append("--fast")
        if val_renders:
            cmd.append("--validation-renders")
        if no_lods:
            cmd.append("--no-lods")
        if no_collision:
            cmd.append("--no-collision")
        if no_refine:
            cmd.append("--no-refine-ref")
        if real_views:
            cmd.extend(["--real-views", real_views])

        self._console.show()
        self._console.append(f"\n{'─' * 60}")
        self._console.append(f"  Generating: {asset_id}  [{self._active_preset or 'custom'}]")
        self._console.append(f"{'─' * 60}")
        self._console.append(f"$ {' '.join(cmd)}\n")

        self._pipeline_running = True
        self._worker = PipelineWorker(cmd)
        self._worker.line_received.connect(self._console.append)
        self._worker.finished_ok.connect(self._on_done_ok)
        self._worker.finished_err.connect(self._on_done_err)
        self._worker.start()

        self._gen_btn.setEnabled(False)
        self._gen_btn.setText("⏳  Running…")
        self._status_lbl.setText(f"Generating {asset_id}…")
        self._status_lbl.setStyleSheet("color: #9cdcfe;")

    def _on_done_ok(self):
        self._pipeline_running = False
        self._server_warn.hide()
        self._gen_btn.setText("▶  Generate")
        self._post_btn.setText("⚙  Post-process")
        self._status_lbl.setText("Pipeline completed successfully.")
        self._status_lbl.setStyleSheet("color: #4ec94e;")
        self._console.append("\n✓  Pipeline completed successfully.")
        self._console.clear_error_banner()
        self._populate_assets()
        self._on_selection_change(self._asset_list.currentItem(), None)

    def _on_done_err(self, code: int):
        self._pipeline_running = False
        self._gen_btn.setText("▶  Generate")
        self._post_btn.setText("⚙  Post-process")
        msg = f"Pipeline failed (exit {code}) — see console for details."
        self._status_lbl.setText(msg)
        self._status_lbl.setStyleSheet("color: #f28b82;")
        self._console.append(f"\n✗  Pipeline exited with code {code}.")
        self._console.show_error_banner(
            f"Exit code {code}. Check the log above for the first ERROR line. "
            "Server logs: click Logs button."
        )
        self._console.show()
        self._console.raise_()
        self._populate_assets()
        self._on_selection_change(self._asset_list.currentItem(), None)

    # ── post-process (checkpoint resume) ─────────────────────────────────────

    def _on_post_process(self):
        item = self._asset_list.currentItem()
        if not item:
            return

        asset_id: str = item.data(Qt.UserRole)
        no_lods      = self._no_lods_check.isChecked()
        no_collision = self._no_collision_check.isChecked()

        cmd = [
            sys.executable, "-u", str(WITNESS_PY),
            "generate", asset_id,
            "--skip-generate",
        ]
        if no_lods:
            cmd.append("--no-lods")
        if no_collision:
            cmd.append("--no-collision")

        self._console.show()
        self._console.append(f"\n{'─' * 60}")
        self._console.append(f"  Post-processing: {asset_id}  (skipping Hunyuan + bake)")
        self._console.append(f"{'─' * 60}")
        self._console.append(f"$ {' '.join(cmd)}\n")

        self._pipeline_running = True
        self._worker = PipelineWorker(cmd)
        self._worker.line_received.connect(self._console.append)
        self._worker.finished_ok.connect(self._on_done_ok)
        self._worker.finished_err.connect(self._on_done_err)
        self._worker.start()

        self._gen_btn.setEnabled(False)
        self._post_btn.setEnabled(False)
        self._post_btn.setText("⏳  Running…")
        self._status_lbl.setText(f"Post-processing {asset_id}…")
        self._status_lbl.setStyleSheet("color: #9cdcfe;")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
