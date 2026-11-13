"""Shared light and dark appearance for the application and guide."""


def application_stylesheet(dark):
    bg, fg, panel = (
        ("#171b20", "#edf1ec", "#23292f") if dark else ("#f8f9f6", "#26352f", "#ffffff")
    )
    muted, border = ("#a0aaa9", "#374047") if dark else ("#74817a", "#e2e7e0")
    accent = "#b8d2bc" if dark else "#214f3b"
    accent_fg = "#192b20" if dark else "#ffffff"
    return f"""
        QMainWindow, QWidget {{ background:{bg}; color:{fg}; font-family:'Segoe UI'; font-size:13px; }}
        QLabel {{ background:transparent; }}
        QLabel#brand {{ font-size:19px; font-weight:600; letter-spacing:-0.4px; }}
        QLabel#brandmark {{ font-size:23px; font-weight:600; background:{accent}; color:{accent_fg}; border-radius:13px; }}
        QLabel#title {{ font-size:29px; font-weight:600; letter-spacing:-0.7px; }}
        QLabel#subtitle {{ font-size:14px; color:{muted}; }}
        QLabel#muted {{ color:{muted}; font-size:12px; }}
        QLabel#eyebrow {{ color:{muted}; font-size:10px; font-weight:600; letter-spacing:1.3px; }}
        QLabel#distance {{ font-size:62px; font-weight:300; letter-spacing:-2px; }}
        QLabel#unit {{ font-size:22px; color:{muted}; }}
        QLabel#metric {{ font-size:13px; font-weight:600; }}
        QLabel#section {{ font-size:17px; font-weight:600; }}
        QLabel#step {{ color:{accent}; font-size:18px; font-weight:600; }}
        QLabel#state {{ background:{panel}; border:1px solid {border}; border-radius:14px; padding:8px 14px; font-size:11px; font-weight:600; color:{muted}; }}
        QLabel#state[recording="true"] {{ color:#28885f; border-color:#79ad8d; }}
        QFrame#result {{ background:{panel}; border:1px solid {border}; border-radius:18px; }}
        QFrame#banner {{ background:{panel}; border:1px solid {border}; border-radius:12px; }}
        QFrame#divider {{ background:{border}; }}
        QLabel#message {{ background:{panel}; border:1px solid {border}; border-radius:8px; padding:10px; }}
        QPushButton {{ background:{panel}; border:1px solid {border}; border-radius:10px; padding:11px 17px; font-weight:600; }}
        QPushButton:hover {{ border-color:{muted}; }}
        QPushButton:pressed {{ background:{border}; }}
        QPushButton:focus {{ border:1px solid #6b9bc1; }}
        QPushButton:disabled {{ color:{muted}; background:{bg}; border-color:{border}; }}
        QPushButton#primary {{ background:{accent}; color:{accent_fg}; border:1px solid {accent}; }}
        QPushButton#nav {{ border:none; background:transparent; color:{muted}; padding:10px 17px; }}
        QPushButton#nav:checked {{ color:{fg}; background:{panel}; }}
        QPushButton[small="true"] {{ padding:5px 10px; font-size:11px; }}
        QComboBox, QDoubleSpinBox, QLineEdit {{ background:{panel}; border:1px solid {border}; border-radius:8px; padding:9px; min-height:19px; }}
        QComboBox QAbstractItemView {{ background:{panel}; color:{fg}; selection-background-color:{border}; }}
        QPlainTextEdit {{ background:{panel}; border:1px solid {border}; border-radius:8px; padding:8px; font-family:Consolas; font-size:11px; }}
        QCheckBox {{ spacing:10px; }}
    """
