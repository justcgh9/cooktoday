import sys
import os

from streamlit.testing.v1 import AppTest
from pytest import fixture


@fixture
def app_client():
    app = AppTest.from_file("app.py")
    yield app


@fixture(autouse=True)
def mock_requests_package(mocker):
    sys.modules["requests"] = mocker.MagicMock()


@fixture(autouse=True)
def envs():
    os.environ["TESTING"] = "true"
