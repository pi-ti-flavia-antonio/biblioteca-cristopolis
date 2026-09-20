import threading

import webview

from app import create_app

app = create_app()


def run_flask():
    app.run(port=5000)


if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    webview.create_window(
        "Biblioteca Municipal de Cristópolis",
        "http://127.0.0.1:5000",
        width=1200,
        height=800,
        min_size=(900, 600),
    )
    webview.start()
