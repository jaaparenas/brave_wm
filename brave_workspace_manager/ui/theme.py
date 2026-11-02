"""Visual theme: dark palette and stylesheet of the application."""

from __future__ import annotations

ACCENT = "#4f8cff"
ACCENT_HOVER = "#6ea0ff"
BACKGROUND = "#161920"
SURFACE = "#1e222b"
SURFACE_ALT = "#252a35"
INPUT = "#11141a"
BORDER = "#2d3441"
TEXT = "#e7eaf0"
TEXT_MUTED = "#9aa4b5"
SUCCESS = "#51cf66"
WARNING = "#ffd43b"
DANGER = "#ff6b6b"

STYLESHEET = f"""
QWidget {{
    background-color: {BACKGROUND};
    color: {TEXT};
    font-size: 13px;
}}
QMainWindow::separator {{
    background: {BORDER};
    width: 1px;
    height: 1px;
}}
QFrame#Card {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 10px;
}}
QLabel {{ background: transparent; border: none; }}
QLabel#HeaderTitle {{
    font-size: 17px;
    font-weight: 600;
}}
QLabel#HeaderSubtitle, QLabel#Muted {{
    color: {TEXT_MUTED};
}}
QLabel#SummaryTitle {{
    font-size: 14px;
    font-weight: 600;
}}
QLabel#SummaryLabel {{
    color: {TEXT_MUTED};
}}
QLabel#SummaryValue {{
    font-weight: 600;
}}
QLabel#SummaryActive {{
    color: {ACCENT};
    font-weight: 600;
}}
QLabel#StatusOk {{ color: {SUCCESS}; }}
QLabel#StatusOff {{ color: {TEXT_MUTED}; }}
QLabel#StatusWarn {{ color: {WARNING}; }}

QPushButton {{
    background-color: {SURFACE_ALT};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 6px 14px;
    color: {TEXT};
}}
QPushButton:hover {{ background-color: {BORDER}; }}
QPushButton:pressed {{ background-color: {INPUT}; }}
QPushButton:disabled {{ color: {TEXT_MUTED}; border-color: {BORDER}; }}
QPushButton#Primary {{
    background-color: {ACCENT};
    border: 1px solid {ACCENT};
    font-weight: 600;
}}
QPushButton#Primary:hover {{ background-color: {ACCENT_HOVER}; }}
QPushButton#Danger {{ color: {DANGER}; }}

QLineEdit, QComboBox, QSpinBox {{
    background-color: {INPUT};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 6px 10px;
    selection-background-color: {ACCENT};
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{ border-color: {ACCENT}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    selection-background-color: {ACCENT};
}}

QTabWidget::pane {{ border: none; }}
QTabBar::tab {{
    background: transparent;
    padding: 8px 16px;
    border-bottom: 2px solid transparent;
}}
QTabBar::tab:selected {{ border-bottom: 2px solid {ACCENT}; color: {TEXT}; }}

QTableWidget, QTreeWidget, QListWidget {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 10px;
    gridline-color: {BORDER};
}}
QHeaderView::section {{
    background-color: {SURFACE_ALT};
    border: none;
    border-bottom: 1px solid {BORDER};
    padding: 6px;
    color: {TEXT_MUTED};
    font-weight: 600;
}}
QTableWidget::item, QTreeWidget::item, QListWidget::item {{ padding: 4px; }}
QTableWidget::item:selected, QTreeWidget::item:selected, QListWidget::item:selected {{
    background-color: {ACCENT};
    color: #ffffff;
}}

QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle {{ background: {BORDER}; border-radius: 5px; min-height: 30px; min-width: 30px; }}
QScrollBar::handle:hover {{ background: {ACCENT}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

QStatusBar {{ background: {SURFACE}; color: {TEXT_MUTED}; }}
QStatusBar::item {{ border: none; }}
QMenu {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 4px;
}}
QMenu::item {{ padding: 6px 22px 6px 14px; border-radius: 6px; }}
QMenu::item:selected {{ background-color: {ACCENT}; }}
QMenu::separator {{ height: 1px; background: {BORDER}; margin: 4px 8px; }}

QCheckBox {{ spacing: 8px; }}
QCheckBox::indicator {{
    width: 16px; height: 16px;
    border: 1px solid {BORDER};
    border-radius: 4px;
    background: {INPUT};
}}
QCheckBox::indicator:checked {{ background: {ACCENT}; border-color: {ACCENT}; }}

QToolTip {{
    background-color: {SURFACE_ALT};
    color: {TEXT};
    border: 1px solid {BORDER};
    padding: 4px;
}}
"""
