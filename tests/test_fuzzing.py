import pytest
import random
import json
import io
from unittest.mock import MagicMock, patch
from PIL import Image
from faker import Faker

from src.what_to_cook.api_client import MealDBClient
from src.what_to_cook.data_manager import _safe_json_loads

fake = Faker()


app = None


@pytest.fixture(autouse=True)
def setup_imports():
    with (
        patch("streamlit.session_state", new_callable=MagicMock),
        patch("streamlit_local_storage.LocalStorage") as mock_local_storage,
    ):
        # Properly mock LocalStorage responses
        mock_storage = MagicMock()
        mock_storage.getItem.side_effect = lambda key: json.dumps([])
        mock_local_storage.return_value = mock_storage

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

    def update_handler(new_values):
        state.update(new_values)

    mock.update.side_effect = update_handler

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
            "measures": ["5 gram", "1 spoon"],
        },
        {
            "id": "2",
            "name": "Recipe 2",
            "ingredients": ["sugar"],
            "source": "custom",
            "measures": ["2 spoons"],
        },
    ]


# make random.sample safe for k > len(population)
_orig_sample = random.sample


def _safe_sample(population, k):
    n = len(population)
    if k < 0:
        k = 0
    elif k > n:
        k = n
    return _orig_sample(population, k)


random.sample = _safe_sample


# not tests
def generate_random_recipe():
    return {
        "id": fake.uuid4(),
        "name": fake.sentence(nb_words=3),
        "ingredients": [fake.word() for _ in range(random.randint(1, 5))],
        "measures": [
            fake.word() if random.random() > 0.5 else ""
            for _ in range(random.randint(1, 5))
        ],
        "category": fake.word(),
        "area": fake.country(),
        "instructions": fake.paragraph(),
        "image_url": fake.image_url() if random.random() > 0.5 else None,
        "source": random.choice(["api", "custom"]),
    }


def generate_random_image():
    img = Image.new(
        "RGB",
        (random.randint(10, 100), random.randint(10, 100)),
        color=(random.randint(0, 255),
               random.randint(0, 255),
               random.randint(0, 255)),
    )
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return buffered.getvalue()


# api_client
def test_api_client_fetch_all_meals_fuzzing():
    with patch("requests.get") as mock_get:
        for _ in range(20):
            if random.random() > 0.3:
                mock_get.return_value.status_code = 200
                mock_get.return_value.json.return_value = {
                    "meals": [{"idMeal": str(i)}
                              for i in range(random.randint(0, 5))]
                }
            else:
                mock_get.return_value.status_code = random.choice(
                    [400, 404, 500]
                )
                mock_get.return_value.json.return_value = {}

            client = MealDBClient()
            result = client.fetch_all_meals()
            assert isinstance(result, list)


def test_api_client_get_meal_details_fuzzing():
    with patch("requests.get") as mock_get:
        for _ in range(20):
            meal_id = random.randint(1, 1000)
            if random.random() > 0.3:
                mock_get.return_value.status_code = 200
                mock_get.return_value.json.return_value = {
                    "meals": [
                        {
                            "idMeal": str(meal_id),
                            "strMeal": fake.sentence(),
                            "strCategory": fake.word(),
                            **{
                                f"strIngredient{i}": fake.word()
                                if random.random() > 0.5
                                else ""
                                for i in range(1, 21)
                            },
                            **{
                                f"strMeasure{i}": fake.word()
                                if random.random() > 0.5
                                else ""
                                for i in range(1, 21)
                            },
                        }
                    ]
                }
            else:
                mock_get.return_value.status_code = random.choice(
                    [400, 404, 500]
                )
                mock_get.return_value.json.return_value = {}

            client = MealDBClient()
            result = client.get_meal_details(str(meal_id))
            assert isinstance(result, dict)


# data manager
def test_process_meal_invalid():
    assert app.process_meal({}) is None


def test_safe_json_loads_fuzzing():
    for _ in range(20):
        test_data = None
        if random.random() > 0.3:
            test_data = json.dumps(
                [generate_random_recipe() for _ in range(random.randint(0, 5))]
            )
        elif random.random() > 0.5:
            test_data = fake.text()
        else:
            test_data = None

        result = _safe_json_loads(test_data)
        assert isinstance(result, list)


# app components


def test_main_initialization(mock_session_state):
    with (
        patch("app.st.session_state", mock_session_state),
        patch("app.MealDBClient") as mock_client,
    ):
        mock_client.return_value.fetch_all_meals.return_value = []
        app.main()
        assert mock_session_state["initialized"] is True


def test_render_home_filtering_with_salt(mock_session_state, sample_recipes):
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
            "salt" in r["ingredients"]
            for r in mock_session_state.filtered_recipes
        )


def test_create_custom_recipe():
    with (
        patch("app.Image.open"),
        patch("app.io.BytesIO"),
        patch("app.base64.b64encode") as mock_b64,
    ):
        mock_b64.return_value.decode.return_value = "test"
        recipe = app.create_custom_recipe("Test", "Salt\nPepper", "Mix", None)
        assert recipe["name"] == "Test"
        assert recipe["ingredients"] == ["salt", "pepper"]


def test_render_home_fuzzing(mock_session_state):
    for _ in range(20):
        recipes = [generate_random_recipe()
                   for _ in range(random.randint(1, 10))]
        include = random.sample(
            list({i for r in recipes
                  for i in r["ingredients"]}), random.randint(0, 3)
        )
        exclude = random.sample(
            list({i for r in recipes
                  for i in r["ingredients"]}), random.randint(0, 3)
        )

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
            mock_multiselect.side_effect = [include, exclude]
            mock_session_state["all_meals"] = recipes
            app.render_home(recipes)

            filtered = mock_session_state.filtered_recipes
            assert all(
                (not include or all(i in r["ingredients"] for i in include))
                and (not exclude or
                     not any(e in r["ingredients"] for e in exclude))
                for r in filtered
            )


# edge cases
def test_main_edge_cases(mock_session_state):
    with (
        patch("app.st.session_state", mock_session_state),
        patch("app.load_all", return_value=[]),
        patch("app.MealDBClient") as mock_client,
    ):
        mock_client.return_value.fetch_all_meals.return_value = []
        app.main()
        assert mock_session_state["initialized"] is True

    with (
        patch("app.st.session_state", mock_session_state),
        patch("app.MealDBClient") as mock_client,
    ):
        mock_client.return_value.fetch_all_meals.side_effect = \
            Exception("API error")
        app.main()
        assert len(mock_session_state["all_meals"]) == 0


def test_render_favorites_edge_cases():
    with (
        patch("app.st.session_state", MagicMock(favorites=[])),
        patch("app.st.info") as mock_info,
    ):
        app.render_favorites()
        mock_info.assert_called_with("No favorite recipes yet!")

    # Test with favorites
    with (
        patch("app.st.session_state",
              MagicMock(favorites=[generate_random_recipe()])),
        patch("app.show_recipe") as mock_show,
    ):
        app.render_favorites()
        mock_show.assert_called()


# Performance and stress Tests


def test_stress_test_api_client():
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"meals": []}

        client = MealDBClient()

        for _ in range(100):
            result = client.fetch_all_meals()
            assert isinstance(result, list)
