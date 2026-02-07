import os
from app import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORTFOLIO_SERVICE_PORT", 5003))
    debug = os.getenv("FLASK_DEBUG", "True") == "True"
    
    print(f"🚀 PORTFOLIO-SERVICE démarré sur http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port, debug=debug)