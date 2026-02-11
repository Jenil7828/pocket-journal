from flask import render_template


def register(app, deps):
    @app.route("/", methods=["GET"])
    def home():
        return render_template("home.html")

