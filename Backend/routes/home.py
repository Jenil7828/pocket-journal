import time
from .logging_utils import log_request, log_response
from flask import render_template


def register(app, deps):
    @app.route("/", methods=["GET"])
    def home():
        start_time = time.time()
        log_request()
        log_response(200, start_time)
        return render_template("home.html")

