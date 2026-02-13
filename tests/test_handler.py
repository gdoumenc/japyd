import pytest
from flask import Flask
from flask_pydantic import validate
from werkzeug.exceptions import UnprocessableEntity

from japyd import JsonApiApp, TopLevel


class TestHandler:

    def test_simple(self):
        app = Flask(__name__)

        @app.route("/")
        @validate(exclude_none=True)
        def get():
            raise UnprocessableEntity("exception test")

        @app.errorhandler(Exception)
        def handle_bad_request(e):
            return "bad request!", 400

        JsonApiApp(app)

        response = app.test_client().get("/")
        assert response.status_code == 400
        assert "application/vnd.api+json" in response.headers["Content-Type"]
        top = TopLevel.model_validate(response.json)

        assert top.errors
        assert len(top.errors) == 1
        assert top.errors[0].title == "422 Unprocessable Entity: exception test"
        assert top.errors[0].detail == "bad request!"

    def test_raise(self):
        app = Flask(__name__)

        @app.route("/")
        @validate(exclude_none=True)
        def get():
            raise UnprocessableEntity("exception test")

        @app.errorhandler(Exception)
        def handle_bad_request(e):
            raise e

        JsonApiApp(app)

        response = app.test_client().get("/")
        assert response.status_code == 500
        assert "application/vnd.api+json" in response.headers["Content-Type"]
        top = TopLevel.model_validate(response.json)

        assert top.errors
        assert len(top.errors) == 1
        assert top.errors[0].title == "UnprocessableEntity"
        assert (
            top.errors[0].detail
            == "Error in the application exception handler: 422 Unprocessable Entity: exception test"
        )
