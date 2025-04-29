from streamlit_js_eval import get_cookie, set_cookie
import json
from uuid import uuid4
from src.what_to_cook.api_client import MealDBClient

def _safe_json_loads(data: str) -> list:
    try:
        return json.loads(data) if data else []
    except json.JSONDecodeError:
        return []

def load_favorites() -> list:
    return _safe_json_loads(get_cookie("favorites"))

def save_favorites(favorites: list) -> None:
    print("adding cookie", favorites)
    set_cookie("favorites", json.dumps(favorites), duration_days=365)

def load_custom_recipes() -> list:
    return _safe_json_loads(get_cookie("custom_recipes"))

def save_custom_recipes(recipes: list) -> None:
    set_cookie("custom_recipes", json.dumps(recipes), duration_days=365)

def process_meal(raw_meal: dict) -> dict:
    """Convert raw API response to our format"""
    if not raw_meal.get('idMeal'):
        return None
    
    # Get detailed information
    client = MealDBClient()
    details = client.get_meal_details(raw_meal['idMeal'])
    
    ingredients = []
    measures = []
    for i in range(1, 21):
        ingredient = details.get(f'strIngredient{i}', '')
        measure = details.get(f'strMeasure{i}', '')
        if ingredient:
            ingredients.append(f"{ingredient}".lower().capitalize())
            if measure:
                measures.append(f"{measure}")
            else:
                measures.append("")
    
    return {
        'id': details['idMeal'],
        'name': details['strMeal'],
        'category': details.get('strCategory', 'Unknown'),
        'area': details.get('strArea', 'Unknown'),
        'ingredients': ingredients,
        'measures': measures,
        'instructions': details.get('strInstructions', 'No instructions available'),
        'image_url': f"{details['strMealThumb']}/preview",
        'source': 'api'
    }

def generate_custom_recipe_id() -> str:
    return str(uuid4())