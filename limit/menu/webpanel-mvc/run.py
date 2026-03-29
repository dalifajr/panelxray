from mvc_app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(
        host=app.config["WEB_PANEL_HOST"],
        port=app.config["WEB_PANEL_PORT"],
    )
