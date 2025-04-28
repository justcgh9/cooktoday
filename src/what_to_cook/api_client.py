from typing import Dict
import requests

class MealDBClient:
    BASE_URL = "https://www.themealdb.com/api/json/v1/1/"

    def fetch_meals_by_first_letter(self, letter: str) -> list:
        url = f"{self.BASE_URL}search.php?f={letter}"
        response = requests.get(url)
        return response.json().get('meals', []) if response.ok else []

    def fetch_all_meals(self) -> list:
        all_meals = []
        for letter in 'abcdefghijklmnopqrstuvwxyz':
            if len(all_meals) > 30:
                break
            meals = self.fetch_meals_by_first_letter(letter)
            if meals is not None:
                all_meals.extend(meals)
                
        seen_ids = set()
        unique_meals = []
        for meal in all_meals:
            if meal['idMeal'] not in seen_ids:
                seen_ids.add(meal['idMeal'])
                unique_meals.append(meal)
        
        return unique_meals

    def fetch_random_meal(self) -> dict:
        url = f"{self.BASE_URL}random.php"
        response = requests.get(url)
        return response.json().get('meals', [{}])[0] if response.ok else {}
    
    def get_meal_details(self, meal_id: str) -> Dict:
        """Get full details for a meal"""
        try:
            response = requests.get(f"{self.BASE_URL}lookup.php?i={meal_id}", timeout=10)
            if response.status_code == 200:
                return response.json()['meals'][0]
            return {}
        except Exception as e:
            print(f"Error fetching details for meal {meal_id}: {str(e)}")
            return {}