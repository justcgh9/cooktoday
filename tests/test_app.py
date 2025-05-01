import pytest
from unittest.mock import MagicMock, patch

app = None

@pytest.fixture(autouse=True)
def setup_imports():
    with patch('streamlit.session_state', new_callable=MagicMock), \
         patch('streamlit_local_storage.LocalStorage') as mock_local_storage:
        
        mock_storage_instance = MagicMock()
        mock_storage_instance.getItem.side_effect = lambda key: "[]"
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
        "current_recipe": None
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
        {"id": "1", "name": "Recipe 1", "ingredients": ["salt", "pepper"], "source": "api"},
        {"id": "2", "name": "Recipe 2", "ingredients": ["sugar"], "source": "custom"}
    ]

def test_main_initialization(mock_session_state):
    with patch('app.st.session_state', mock_session_state), \
         patch('app.load_all', return_value=[]), \
         patch('app.MealDBClient') as mock_client:
        
        mock_client.return_value.fetch_all_meals.return_value = []
        app.main()
        assert mock_session_state["initialized"] == True

def test_render_home_filtering_with_salt(mock_session_state, sample_recipes):
    col1 = MagicMock()
    col2 = MagicMock()
    col1.__enter__.return_value = col1
    col2.__enter__.return_value = col2

    with patch('app.st.session_state', mock_session_state), \
         patch('app.st.columns', return_value=(col1, col2)), \
         patch('app.st.multiselect') as mock_multiselect, \
         patch('app.st.button'), \
         patch('app.st.error'):

        mock_multiselect.side_effect = [["salt"], []]

        mock_session_state["all_meals"] = sample_recipes
        app.render_home(sample_recipes)
        
        assert len(mock_session_state.filtered_recipes) == 1
        assert all("salt" in r["ingredients"] 
                for r in mock_session_state.filtered_recipes)

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
        "image_url": None
    }
    
    with patch('app.st.session_state', mock_session_state), \
         patch('app.st.subheader'), \
         patch('app.st.markdown'), \
         patch('app.st.image'), \
         patch('app.st.expander'), \
         patch('app.st.button'), \
         patch('app.st.toast'), \
         patch('app.save_favorites') as mock_save:
        
        app.show_recipe(recipe, False)

        mock_session_state["favorites"].append(recipe)
        mock_save.assert_called_once()

def test_create_custom_recipe():
    with patch('app.base64'), \
         patch('app.io.BytesIO'), \
         patch('app.Image.open'):
        
        recipe = app.create_custom_recipe(
            "Test", "Salt\nPepper", "Mix", None
        )
        assert recipe["name"] == "Test"
        assert recipe["ingredients"] == ["salt", "pepper"]


# test API Client
def test_api_client_fetch_meals():
    with patch('requests.get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"meals": [{"idMeal": "1"}]}
        
        client = app.MealDBClient()
        result = client.fetch_meals_by_first_letter('a')
        assert len(result) == 1
        assert result[0]["idMeal"] == "1"

def test_api_client_get_meal_details():
    with patch('requests.get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"meals": [{"idMeal": "123"}]}
        
        client = app.MealDBClient()
        result = client.get_meal_details("123")
        assert result["idMeal"] == "123"

# test Data Manager
def test_process_meal_invalid():
    assert app.process_meal({}) is None


# test App Error Cases
def test_main_with_api_failure(mock_session_state):
    with patch('app.st.session_state', mock_session_state), \
         patch('app.MealDBClient') as mock_client:
        
        mock_client.return_value.fetch_all_meals.side_effect = Exception("API error")
        app.main()
        assert len(mock_session_state["all_meals"]) == 0


def test_create_custom_recipe_with_image():
    mock_file = MagicMock()
    mock_file.read.return_value = b"fake image data"
    
    with patch('app.Image.open'), \
         patch('app.io.BytesIO'), \
         patch('app.base64.b64encode') as mock_b64:
        
        mock_b64.return_value.decode.return_value = "base64data"
        recipe = app.create_custom_recipe("Test", "Salt", "Mix", mock_file)
        assert recipe["image_url"] is not None
