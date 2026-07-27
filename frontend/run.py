"""
Entry point for the FNRG Preaching Flask application.
 
Run with:
    python run.py
 
The app will be available at http://127.0.0.1:5000
"""
 
from app import create_app
 
app = create_app()
 
if __name__ == "__main__":
    # debug=True gives auto-reload + interactive debugger while developing.
    # Turn this off (or set FLASK_DEBUG=0) before deploying anywhere real.
    app.run(host="0.0.0.0", port=5000, debug=True)