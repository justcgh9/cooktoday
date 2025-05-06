import io
import os

from pytest import fixture, mark
from PIL import Image
from unittest.mock import patch, MagicMock


@fixture(autouse=True)
def envs():
    os.environ["TESTING"] = "true"


@fixture(autouse=True)
def mocked_get_local_storage(mocker):
    return mocker.patch("app.get_local_storage")


@fixture(autouse=True)
def mocked_streamlit(mocker, columns):
    mock = mocker.patch("app.st")
    mock.columns.return_value = columns
    return mock


@fixture
def columns(mocker):
    return [mocker.MagicMock(), mocker.MagicMock()]


@fixture
def image():
    img = Image.new("RGB", (10, 10), color="red")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


@fixture
def mocked_save_favorites(mocker):
    return mocker.patch("app.save_favorites")


@fixture
def mocked_show_recipe(mocker):
    return mocker.patch("app.show_recipe")


@fixture
def mock_st():
    state = {
        "favorites": [],
        "custom_recipes": [],
        "all_meals": [],
        "last_api_fetch": None,
        "filtered_recipes": [],
        "current_recipe": None,
    }
    mock = MagicMock()
    mock.__getitem__.side_effect = state.__getitem__
    mock.__setitem__.side_effect = state.__setitem__
    mock.__contains__.side_effect = state.__contains__

    def update_handler(new_values):
        state.update(new_values)

    mock.update.side_effect = update_handler

    for k, v in state.items():
        setattr(mock, k, v)
    return mock


def test_create_custom_recipe_with_image(image):
    from app import create_custom_recipe

    recipe = create_custom_recipe(
        name="My Dish",
        ingredients="rice\nchicken\n",
        instructions="Cook everything.",
        image_file=image,
    )

    assert recipe["name"] == "My Dish"
    assert recipe["ingredients"] == ["rice", "chicken"]
    assert recipe["instructions"] == "Cook everything."
    assert recipe["image_url"].startswith("data:image/png;base64,")


def test_create_custom_recipe_without_image():
    from app import create_custom_recipe

    recipe = create_custom_recipe(
        name="Dry Dish",
        ingredients="beans",
        instructions="Boil beans.",
        image_file=None,
    )

    assert recipe["image_url"] is None


@mark.usefixtures("mocked_save_favorites")
def test_render_home(mocked_streamlit, mock_st):
    from app import render_home

    with (
        patch("app.st.session_state", mock_st)
    ):
        recipe = {"ingredients": ["test"], "name": "cool", "id": "test"}
        mock_st.all_meals = [recipe]

        render_home()

        mocked_streamlit.title.assert_called_with("What to Cook Today 🍳")
        mocked_streamlit.subheader.assert_called_with("Filters")


@mark.usefixtures("mocked_save_favorites")
def test_render_browse(mocked_streamlit, mocked_show_recipe):
    from app import render_browse

    mocked_streamlit.text_input.return_value = "cool"

    render_browse([{"ingredients": ["test"], "name": "cool", "id": "test"}])

    mocked_streamlit.title.assert_called_with("Browse Recipes")
    mocked_show_recipe.assert_called_with(
        {"ingredients": ["test"], "name": "cool", "id": "test"}, False
    )


def test_render_empty_favorites(mocked_streamlit):
    from app import render_favorites

    render_favorites()

    mocked_streamlit.title.assert_called_with("❤️ Favorites")


def test_show_recipe(mocked_streamlit, mocked_save_favorites):
    from app import show_recipe

    show_recipe({"ingredients": ["test"], "name": "cool", "id": "test"})

    mocked_streamlit.subheader.assert_called_with("cool")


def test_show_recipe_with_image(mocked_streamlit, mocked_save_favorites):
    from app import show_recipe

    show_recipe(
        {
            "ingredients": ["test"],
            "name": "cool",
            "id": "test",
            "image_url": "test",
            "source": "test",
        }
    )

    mocked_streamlit.subheader.assert_called_with("cool")
    mocked_streamlit.image.assert_called_with("test")
