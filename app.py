import streamlit as st
import random
from PIL import Image
from datetime import datetime
import base64
import io
from src.what_to_cook.api_client import MealDBClient
from src.what_to_cook.data_manager import (
    load_favorites, save_favorites,
    load_custom_recipes, save_custom_recipes,
    process_meal, generate_custom_recipe_id
)

def main():
    st.set_page_config(page_title="What to Cook Today", layout="wide")
    # st.session_state.favorites = []
    
    # Initialize session state
    if 'initialized' not in st.session_state:
        st.session_state.update({
            'initialized': True,
            'favorites': load_favorites(),
            'custom_recipes': load_custom_recipes(),
            'all_meals': [],
            'last_api_fetch': None
        })
    
    # Fetch meals if empty or older than 1 hour
    if not st.session_state.all_meals or (
        st.session_state.last_api_fetch and 
        (datetime.now() - st.session_state.last_api_fetch).seconds > 3600
    ):
        try:
            client = MealDBClient()
            raw_meals = client.fetch_all_meals()
            print("Fetched meals", len(raw_meals))
            processed = [process_meal(m) for m in raw_meals]
            print("Processed meals")
            st.session_state.all_meals = [m for m in processed if m is not None]
            st.session_state.last_api_fetch = datetime.now()
        except Exception as e:
            st.error(f"Failed to load recipes: {str(e)}")
            st.session_state.all_meals = []
    
    all_recipes = st.session_state.all_meals + st.session_state.custom_recipes

    # Navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to", ["Home", "Browse", "Favorites", "Custom Recipes"])

    if page == "Home":
        render_home(all_recipes)
    elif page == "Browse":
        render_browse(all_recipes)
    elif page == "Favorites":
        render_favorites()
    elif page == "Custom Recipes":
        render_custom_recipes()

def render_home(recipes: list):
    st.title("What to Cook Today 🍳")
    
    # Filters
    st.subheader("Filters")
    col1, col2 = st.columns(2)
    with col1:
        include = st.multiselect("Include ingredients", sorted({i for r in recipes for i in r['ingredients']}))
    with col2:
        exclude = st.multiselect("Exclude ingredients", sorted({i for r in recipes for i in r['ingredients']}))

    if st.button("🎲 Get Random Recipe"):
        filtered = [
            r for r in recipes
            if (not include or all(i in r['ingredients'] for i in include))
            and (not exclude or not any(e in r['ingredients'] for e in exclude))
        ]
        if filtered:
            recipe = random.choice(filtered)
            show_recipe(recipe, any(r['id'] == recipe['id'] for r in st.session_state.favorites))
        else:
            st.error("No recipes match the filters. Try adjusting your ingredients.")

def render_browse(recipes: list):
    st.title("Browse Recipes")
    search = st.text_input("Search recipes")
    
    filtered = [
        r for r in recipes
        if not search or 
        search.lower() in r['name'].lower() or
        any(search.lower() in ing for ing in r['ingredients'])
    ]
    
    for recipe in filtered:
        with st.expander(recipe['name']):
            show_recipe(recipe, any(r['id'] == recipe['id'] for r in st.session_state.favorites))

def render_favorites():
    st.title("❤️ Favorites")
    if not st.session_state.favorites:
        st.info("No favorite recipes yet!")
        return
    
    for recipe in st.session_state.favorites:
        with st.expander(recipe['name']):
            show_recipe(recipe, is_favorite=True)

def render_custom_recipes():
    st.title("📝 Custom Recipes")
    
    # Add new recipe form
    with st.form("custom_recipe"):
        name = st.text_input("Recipe Name")
        ingredients = st.text_area("Ingredients (one per line)")
        instructions = st.text_area("Instructions")
        image_file = st.file_uploader("Upload Image", type=["png", "jpg", "jpeg"])
        
        if st.form_submit_button("Save Recipe"):
            new_recipe = create_custom_recipe(name, ingredients, instructions, image_file)
            st.session_state.custom_recipes.append(new_recipe)
            save_custom_recipes(st.session_state.custom_recipes)
            st.rerun()

    # Display existing
    for recipe in st.session_state.custom_recipes:
        with st.expander(recipe['name']):
            show_recipe(recipe, any(r['id'] == recipe['id'] for r in st.session_state.favorites))

def show_recipe(recipe: dict, is_favorite=False):
    st.subheader(recipe['name'])
    # Image display
    if recipe.get('image_url'):
        if recipe['source'] == 'custom' and recipe['image_url'].startswith('data:'):
            st.image(recipe['image_url'])
        else:
            st.image(recipe['image_url'])
    
    st.markdown(f"**Category:** {recipe.get('category', 'N/A')}")
    st.markdown(f"**Cuisine:** {recipe.get('area', 'N/A')}")
    
    with st.expander("Ingredients"):
        for ingredient in recipe['ingredients']:
            st.write(f"- {ingredient.capitalize()}")
    
    with st.expander("Instructions"):
        st.write(recipe.get('instructions', 'No instructions provided'))
    
    # Favorite button
    if not is_favorite:
        is_fav = any(r['id'] == recipe['id'] for r in st.session_state.favorites)
        btn_label = "❤️ Add to Favorites" if not is_fav else "★ Already Favorited"
        if st.button(btn_label, key=f"fav_{recipe['id']}", on_click=new_fav_button_on_click_handler(is_fav, recipe)):
            pass
            
def new_fav_button_on_click_handler(is_fav: bool, recipe: dict):
    def fav_button_on_click_handler():
        if is_fav:
            st.session_state.favorites.append(recipe)
            save_favorites(st.session_state.favorites)
    return fav_button_on_click_handler

def create_custom_recipe(name: str, ingredients: str, instructions: str, image_file) -> dict:
    ingredients_list = [i.strip().lower() for i in ingredients.split('\n') if i.strip()]
    
    # Handle image
    image_data = None
    if image_file:
        img = Image.open(image_file)
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        image_data = base64.b64encode(buffered.getvalue()).decode("utf-8")
    
    return {
        'id': generate_custom_recipe_id(),
        'name': name,
        'ingredients': ingredients_list,
        'instructions': instructions,
        'image_url': f"data:image/png;base64,{image_data}" if image_data else None,
        'source': 'custom',
        'category': 'Custom',
        'area': 'Personal'
    }

if __name__ == "__main__":
    main()