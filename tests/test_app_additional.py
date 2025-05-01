import io

import pytest
from unittest.mock import MagicMock, patch
from pytest import fixture, mark
from PIL import Image


app = None


@pytest.fixture(autouse=True)
def setup_imports():
    with (
        patch("streamlit.session_state", new_callable=MagicMock),
        patch("streamlit_local_storage.LocalStorage") as mock_local_storage,
    ):
        mock_storage_instance = MagicMock()
        mock_local_storage.return_value = mock_storage_instance

        global app
        import app

        yield


@pytest.fixture
def mock_session_state():
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
    for k, v in state.items():
        setattr(mock, k, v)
    return mock


@pytest.fixture
def sample_recipes():
    return [
        {
            "id": "1",
            "name": "Recipe 1",
            "ingredients": ["salt", "pepper"],
            "source": "api",
        },
        {"id": "2", "name": "Recipe 2", "ingredients": ["sugar"], "source": "custom"},
    ]


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
def test_render_home(mocked_streamlit):
    from app import render_home

    render_home([{"ingredients": ["test"], "name": "cool", "id": "test"}])

    mocked_streamlit.title.assert_called_with("What to Cook Today 🍳")
    mocked_streamlit.subheader.assert_called_with("cool")


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


def test_render_home_filtering_with_salt(
    mock_session_state, sample_recipes, mocked_save_favorites
):
    col1 = MagicMock()
    col2 = MagicMock()
    col1.__enter__.return_value = col1
    col2.__enter__.return_value = col2

    with (
        patch("app.st.session_state", mock_session_state),
        patch("app.st.columns", return_value=(col1, col2)),
        patch("app.st.multiselect") as mock_multiselect,
        patch("app.st.button"),
        patch("app.st.error"),
    ):
        mock_multiselect.side_effect = [["salt"], []]

        mock_session_state["all_meals"] = sample_recipes
        app.render_home(sample_recipes)

        assert len(mock_session_state.filtered_recipes) == 1
        assert all(
            "salt" in r["ingredients"] for r in mock_session_state.filtered_recipes
        )


def test_show_recipe_favorite_toggle(mock_session_state):
    recipe = {
        "id": "123",
        "name": "Test Recipe",
        "ingredients": ["salt"],
        "measures": [""],
        "category": "Test",
        "area": "Test",
        "instructions": "Test",
        "source": "api",
        "image_url": None,
    }

    with (
        patch("app.st.session_state", mock_session_state),
        patch("app.st.subheader"),
        patch("app.st.markdown"),
        patch("app.st.image"),
        patch("app.st.expander"),
        patch("app.st.button"),
        patch("app.st.toast"),
        patch("app.save_favorites") as mock_save,
    ):
        app.show_recipe(recipe, False)
        mock_session_state["favorites"].append(recipe)
        mock_save.assert_called_once()


def test_show_recipe(mocked_streamlit, mocked_save_favorites):
    from app import show_recipe

    show_recipe({"ingredients": ["test"], "name": "cool", "id": "test"})

    mocked_streamlit.subheader.assert_called_with("cool")


def test_show_recipe_with_image(mocked_streamlit, mocked_save_favorites):
    from app import show_recipe

    show_recipe({"ingredients": ["test"], "name": "cool", "id": "test", "image_url": "test", "source": "test"})

    mocked_streamlit.subheader.assert_called_with("cool")
    mocked_streamlit.image.assert_called_with("test")