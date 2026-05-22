import os

from app import create_app


config_name = os.getenv("LOCAL_APP_ENV") or "development"
app = create_app(config_name)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = app.config.get("DEBUG", False)
    app.run(host="0.0.0.0", port=port, debug=debug)
