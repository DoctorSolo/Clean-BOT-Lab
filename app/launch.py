"""Abre a interface gráfica automaticamente no navegador."""
import threading
import time
import webbrowser
import uvicorn

PORT = 8765

def open_browser():
    time.sleep(1.3)
    webbrowser.open(f"http://127.0.0.1:{PORT}")

if __name__ == "__main__":
    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run("app.main:app", host="127.0.0.1", port=PORT, log_level="warning", reload=False)
