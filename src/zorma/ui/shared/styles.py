from __future__ import annotations

FONT_SIZES = {
    "xs": "11px",
    "sm": "12px",
    "base": "13px",
    "md": "14px",
    "lg": "16px",
    "xl": "20px",
    "2xl": "26px",
    "3xl": "28px",
}

SPACING = {
    "xs": 4,
    "sm": 8,
    "md": 12,
    "lg": 16,
    "xl": 20,
    "2xl": 24,
    "3xl": 32,
}

BORDER_RADIUS = {
    "sm": "6px",
    "md": "8px",
    "lg": "12px",
    "xl": "16px",
}

COLORS = {
    "bg": "#1e1e2e",
    "bg2": "#181825",
    "surface": "#242438",
    "sidebar": "#11111b",
    "card": "#1e1e2e",
    "card_hover": "#313244",
    "primary": "#89b4fa",
    "primary_hover": "#74c7ec",
    "accent": "#cba6f7",
    "accent_hover": "#b4b0e6",
    "success": "#a6e3a1",
    "success_hover": "#8bd389",
    "warning": "#f9e2af",
    "warning_hover": "#f0d68a",
    "error": "#f38ba8",
    "error_hover": "#e07a94",
    "text": "#e6e9ef",
    "text_muted": "#a6adc8",
    "text_bright": "#ffffff",
    "border": "#313244",
    "border_light": "#45475a",
    "border_accent": "#585b70",
    "scrollbar": "#45475a",
    "scrollbar_hover": "#585b70",
    "glass_bg": "rgba(24, 24, 37, 0.85)",
    "glass_border": "rgba(137, 180, 250, 0.15)",
    "shadow": "rgba(0, 0, 0, 0.3)",
    "overlay": "rgba(0, 0, 0, 0.5)",
}


def btn_primary() -> str:
    return f"""
        QPushButton {{
            background-color: {COLORS["primary"]};
            color: {COLORS["bg"]};
            border: none;
            border-radius: {BORDER_RADIUS["sm"]};
            padding: 10px 22px;
            font-weight: 700;
            font-size: {FONT_SIZES["base"]};
        }}
        QPushButton:hover {{
            background-color: {COLORS["primary_hover"]};
        }}
        QPushButton:pressed {{
            background-color: #6a8fd8;
        }}
        QPushButton:disabled {{
            background-color: {COLORS["border"]};
            color: {COLORS["text_muted"]};
        }}
    """


def btn_secondary() -> str:
    return f"""
        QPushButton {{
            background-color: {COLORS["bg2"]};
            color: {COLORS["text"]};
            border: 1px solid {COLORS["border"]};
            border-radius: {BORDER_RADIUS["sm"]};
            padding: 10px 22px;
            font-weight: 600;
            font-size: {FONT_SIZES["base"]};
        }}
        QPushButton:hover {{
            border-color: {COLORS["border_light"]};
            background-color: {COLORS["card_hover"]};
        }}
        QPushButton:pressed {{
            background-color: {COLORS["border"]};
        }}
    """


def btn_success() -> str:
    return f"""
        QPushButton {{
            background-color: {COLORS["success"]};
            color: {COLORS["bg"]};
            border: none;
            border-radius: {BORDER_RADIUS["sm"]};
            padding: 10px 22px;
            font-weight: 700;
            font-size: {FONT_SIZES["base"]};
        }}
        QPushButton:hover {{
            background-color: {COLORS["success_hover"]};
        }}
        QPushButton:disabled {{
            background-color: {COLORS["border"]};
            color: {COLORS["text_muted"]};
        }}
    """


def btn_error() -> str:
    return f"""
        QPushButton {{
            background-color: {COLORS["error"]};
            color: {COLORS["bg"]};
            border: none;
            border-radius: {BORDER_RADIUS["sm"]};
            padding: 10px 22px;
            font-weight: 700;
            font-size: {FONT_SIZES["base"]};
        }}
        QPushButton:hover {{
            background-color: {COLORS["error_hover"]};
        }}
    """


def btn_warning() -> str:
    return f"""
        QPushButton {{
            background-color: {COLORS["warning"]};
            color: {COLORS["bg"]};
            border: none;
            border-radius: {BORDER_RADIUS["sm"]};
            padding: 10px 22px;
            font-weight: 700;
            font-size: {FONT_SIZES["base"]};
        }}
        QPushButton:hover {{
            background-color: {COLORS["warning_hover"]};
        }}
        QPushButton:disabled {{
            background-color: {COLORS["border"]};
            color: {COLORS["text_muted"]};
        }}
    """


def btn_small(style: str = "secondary") -> str:
    base = {
        "secondary": btn_secondary(),
        "primary": btn_primary(),
    }.get(style, btn_secondary())
    return base.replace("padding: 10px 22px;", "padding: 6px 14px;font-size:12px;")


DARK_THEME = f"""
QMainWindow, QWidget {{
    background-color: {COLORS["bg"]};
    color: {COLORS["text"]};
    font-family: "Segoe UI", "SF Pro", "Ubuntu", sans-serif;
    font-size: 13px;
}}

QMainWindow::separator {{
    width: 0;
    height: 0;
}}

QPushButton {{
    {btn_primary()}
}}

QLineEdit, QComboBox, QSpinBox {{
    background-color: {COLORS["bg2"]};
    color: {COLORS["text"]};
    border: 1px solid {COLORS["border"]};
    border-radius: {BORDER_RADIUS["sm"]};
    padding: 10px 12px;
    font-size: {FONT_SIZES["base"]};
    selection-background-color: {COLORS["primary"]};
    selection-color: {COLORS["bg"]};
}}
QLineEdit:hover, QComboBox:hover, QSpinBox:hover {{
    border-color: {COLORS["border_light"]};
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
    border-color: {COLORS["primary"]};
    background-color: {COLORS["surface"]};
}}
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled {{
    background-color: {COLORS["card"]};
    color: {COLORS["text_muted"]};
    border-color: {COLORS["border"]};
}}

QComboBox::drop-down {{
    border: none;
    padding-right: 8px;
    width: 24px;
}}
QComboBox::down-arrow {{
    width: 10px;
    height: 10px;
}}
QComboBox QAbstractItemView {{
    background-color: {COLORS["bg2"]};
    color: {COLORS["text"]};
    selection-background-color: {COLORS["primary"]};
    selection-color: {COLORS["bg"]};
    border: 1px solid {COLORS["border"]};
    border-radius: {BORDER_RADIUS["sm"]};
    outline: none;
}}

QSpinBox::up-button, QSpinBox::down-button {{
    background-color: {COLORS["bg2"]};
    border: none;
    width: 22px;
    border-radius: 3px;
}}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
    background-color: {COLORS["card_hover"]};
}}
QSpinBox::up-arrow {{ width: 8px; height: 8px; }}
QSpinBox::down-arrow {{ width: 8px; height: 8px; }}

QCheckBox {{
    spacing: 10px;
    color: {COLORS["text"]};
    font-size: {FONT_SIZES["base"]};
}}
QCheckBox:hover {{
    color: {COLORS["text_bright"]};
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 2px solid {COLORS["border"]};
    border-radius: 5px;
    background-color: {COLORS["bg2"]};
}}
QCheckBox::indicator:hover {{
    border-color: {COLORS["primary"]};
    background-color: {COLORS["surface"]};
}}
QCheckBox::indicator:checked {{
    background-color: {COLORS["primary"]};
    border-color: {COLORS["primary"]};
}}
QCheckBox::indicator:disabled {{
    border-color: {COLORS["border"]};
    background-color: {COLORS["card"]};
}}

QRadioButton {{
    spacing: 8px;
    color: {COLORS["text"]};
}}
QRadioButton::indicator {{
    width: 18px;
    height: 18px;
    border: 2px solid {COLORS["border"]};
    border-radius: 10px;
    background-color: {COLORS["bg2"]};
}}
QRadioButton::indicator:hover {{
    border-color: {COLORS["primary"]};
}}
QRadioButton::indicator:checked {{
    background-color: {COLORS["primary"]};
    border-color: {COLORS["primary"]};
}}

QMenu {{
    background-color: {COLORS["bg2"]};
    color: {COLORS["text"]};
    border: 1px solid {COLORS["border"]};
    border-radius: {BORDER_RADIUS["md"]};
    padding: {SPACING["xs"]}px;
}}
QMenu::item {{
    padding: 8px 24px;
    border-radius: 4px;
}}
QMenu::item:selected {{
    background-color: {COLORS["card_hover"]};
    color: {COLORS["text_bright"]};
}}
QMenu::separator {{
    height: 1px;
    background-color: {COLORS["border"]};
    margin: 4px 10px;
}}

QToolTip {{
    background-color: {COLORS["bg2"]};
    color: {COLORS["text"]};
    border: 1px solid {COLORS["border_light"]};
    border-radius: 4px;
    padding: 6px 10px;
    font-size: {FONT_SIZES["sm"]};
}}

QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {COLORS["scrollbar"]};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {COLORS["scrollbar_hover"]};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 8px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: {COLORS["scrollbar"]};
    border-radius: 4px;
    min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {COLORS["scrollbar_hover"]};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

QTableWidget {{
    background-color: {COLORS["bg"]};
    color: {COLORS["text"]};
    border: 1px solid {COLORS["border"]};
    border-radius: {BORDER_RADIUS["md"]};
    gridline-color: {COLORS["border"]};
    selection-background-color: {COLORS["primary"]};
    selection-color: {COLORS["bg"]};
}}
QTableWidget::item {{
    padding: 10px 12px;
    border-bottom: 1px solid {COLORS["border"]};
}}
QTableWidget::item:hover {{
    background-color: {COLORS["card_hover"]};
}}
QTableWidget::item:selected {{
    background-color: {COLORS["primary"]};
    color: {COLORS["bg"]};
}}

QHeaderView::section {{
    background-color: {COLORS["bg2"]};
    color: {COLORS["text_muted"]};
    border: none;
    border-bottom: 2px solid {COLORS["border"]};
    border-right: 1px solid {COLORS["border"]};
    padding: 10px 12px;
    font-weight: 700;
    font-size: 12px;
    text-transform: uppercase;
}}
QHeaderView::section:last {{
    border-right: none;
}}

QProgressBar {{
    background-color: {COLORS["bg2"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 6px;
    text-align: center;
    color: {COLORS["text"]};
    height: 22px;
    font-size: 12px;
    font-weight: 600;
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {COLORS["primary"]},
        stop:1 {COLORS["accent"]});
    border-radius: 5px;
}}

QLabel {{
    color: {COLORS["text"]};
}}

QFrame#card {{
    background-color: {COLORS["card"]};
    border: 1px solid {COLORS["border"]};
    border-radius: {BORDER_RADIUS["lg"]};
}}
QFrame#card:hover {{
    border-color: {COLORS["border_light"]};
}}

QDialog {{
    background-color: {COLORS["bg"]};
}}
"""

LIGHT_THEME = ""
