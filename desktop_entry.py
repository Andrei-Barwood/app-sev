"""Punto de entrada para el ejecutable de escritorio App SEV."""
from streamlit_desktop_app import start_desktop_app

if __name__ == "__main__":
    start_desktop_app(
        "app.py",
        title="App SEV — Sondeo Eléctrico Vertical",
        width=1280,
        height=900,
    )