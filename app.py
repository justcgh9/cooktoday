import streamlit as st
import random
from PIL import Image
from datetime import datetime
import base64
import io
from streamlit_local_storage import LocalStorage
from src.what_to_cook.api_client import MealDBClient
from src.what_to_cook.data_manager import (
    save_all,
    load_all,
    save_favorites,
    load_favorites,
    load_custom_recipes,
    save_custom_recipes,
    process_meal,
    generate_custom_recipe_id,
)

localS = LocalStorage()


def main():
    st.set_page_config(page_title="What to Cook Today", layout="wide")

    if "initialized" not in st.session_state:
        st.session_state.update(
            {
                "initialized": True,
                "favorites": load_favorites(localS),
                "custom_recipes": load_custom_recipes(localS),
                "all_meals": load_all(localS),
                "last_api_fetch": None,
            }
        )

    if not st.session_state.all_meals or (
        st.session_state.last_api_fetch
        and (datetime.now() - st.session_state.last_api_fetch).seconds > 3600
    ):
        try:
            client = MealDBClient()
            raw_meals = client.fetch_all_meals()
            processed = [process_meal(m) for m in raw_meals]
            st.session_state.all_meals = [m for m in processed if m is not None]
            st.session_state.last_api_fetch = datetime.now()
            save_all(st.session_state.all_meals, localS)
        except Exception as e:
            st.error(f"Failed to load recipes: {str(e)}")
            st.session_state.all_meals = []

    all_recipes = st.session_state.all_meals + st.session_state.custom_recipes

    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to", ["Home", "Browse", "Favorites", "Custom Recipes"])

    if "current_recipe" not in st.session_state:
        st.session_state.current_recipe = None
    if "filtered_recipes" not in st.session_state:
        st.session_state.filtered_recipes = []

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

    if "current_recipe" not in st.session_state:
        st.session_state.current_recipe = None

    st.subheader("Filters")
    col1, col2 = st.columns(2)
    with col1:
        include = st.multiselect(
            "Include ingredients",
            sorted({i for r in recipes for i in r["ingredients"]}),
        )
    with col2:
        exclude = st.multiselect(
            "Exclude ingredients",
            sorted({i for r in recipes for i in r["ingredients"]}),
        )

    filtered = [
        r
        for r in recipes
        if (not include or all(i in r["ingredients"] for i in include))
        and (not exclude or not any(e in r["ingredients"] for e in exclude))
    ]
    st.session_state.filtered_recipes = filtered

    if st.button("🎲 Get Random Recipe"):
        if st.session_state.filtered_recipes:
            st.session_state.current_recipe = random.choice(
                st.session_state.filtered_recipes
            )
        else:
            st.error("No recipes match the filters")

    if st.session_state.current_recipe:
        show_recipe(
            st.session_state.current_recipe,
            any(
                r["id"] == st.session_state.current_recipe["id"]
                for r in st.session_state.favorites
            ),
        )

        if st.button("🔀 Try Another Recipe"):
            st.session_state.current_recipe = random.choice(
                st.session_state.filtered_recipes
            )
            st.rerun()


def render_browse(recipes: list):
    st.title("Browse Recipes")
    search = st.text_input("Search recipes")

    filtered = [
        r
        for r in recipes
        if not search
        or search.lower() in r["name"].lower()
        or any(search.lower() in ing for ing in r["ingredients"])
    ]

    for recipe in filtered:
        show_recipe(
            recipe, any(r["id"] == recipe["id"] for r in st.session_state.favorites)
        )


def render_favorites():
    st.title("❤️ Favorites")
    if not st.session_state.favorites:
        st.info("No favorite recipes yet!")
        return

    for recipe in st.session_state.favorites:
        show_recipe(recipe, is_favorite=True)


def render_custom_recipes():
    st.title("📝 Custom Recipes")

    with st.form("custom_recipe"):
        name = st.text_input("Recipe Name")
        ingredients = st.text_area("Ingredients (one per line)")
        instructions = st.text_area("Instructions")
        image_file = st.file_uploader("Upload Image", type=["png", "jpg", "jpeg"])

        if st.form_submit_button("Save Recipe"):
            new_recipe = create_custom_recipe(
                name, ingredients, instructions, image_file
            )
            st.session_state.custom_recipes.append(new_recipe)
            save_custom_recipes(st.session_state.custom_recipes, localS)
            st.rerun()

    for recipe in st.session_state.custom_recipes:
        show_recipe(
            recipe, any(r["id"] == recipe["id"] for r in st.session_state.favorites)
        )


def show_recipe(recipe: dict, is_favorite=False):
    st.subheader(recipe["name"])

    if recipe.get("image_url"):
        if recipe["source"] == "custom" and recipe["image_url"].startswith("data:"):
            st.image(recipe["image_url"])
        else:
            st.image(recipe["image_url"])

    st.markdown(f"**Category:** {recipe.get('category', 'N/A')}")
    st.markdown(f"**Cuisine:** {recipe.get('area', 'N/A')}")

    with st.expander("Ingredients"):
        for i, ingredient in enumerate(recipe["ingredients"]):
            measures = (
                f": {recipe['measures'][i]}"
                if "measures" in recipe and recipe["measures"][i] != ""
                else ""
            )
            st.write(f"- {ingredient.capitalize()}{measures}")

    with st.expander("Instructions"):
        st.write(recipe.get("instructions", "No instructions provided"))

    if not is_favorite:
        current_fav_status = any(
            r["id"] == recipe["id"] for r in st.session_state.get("favorites", [])
        )

        btn_key = f"fav_{recipe['id']}_{current_fav_status}"

        if st.button(
            "❤️ Add to Favorites"
            if not current_fav_status
            else "★ Remove from Favorites",
            key=btn_key,
        ):
            print("got here")
            if current_fav_status:
                st.session_state.favorites = [
                    r for r in st.session_state.favorites if r["id"] != recipe["id"]
                ]
            else:
                print("and here")
                st.session_state.favorites.append(recipe)

            print("and after that here")
            print(f"Favorite updated for {recipe['id']}")
            st.toast("Favorites updated!", icon="✅")

            save_favorites(st.session_state.favorites, localS)


def create_custom_recipe(
    name: str, ingredients: str, instructions: str, image_file
) -> dict:
    ingredients_list = [i.strip().lower() for i in ingredients.split("\n") if i.strip()]

    image_data = None
    if image_file:
        img = Image.open(image_file)
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        image_data = base64.b64encode(buffered.getvalue()).decode("utf-8")

    return {
        "id": generate_custom_recipe_id(),
        "name": name,
        "ingredients": ingredients_list,
        "instructions": instructions,
        "image_url": f"data:image/png;base64,{image_data}" if image_data else None,
        "source": "custom",
        "category": "Custom",
        "area": "Personal",
    }


if __name__ == "__main__":
    main()
