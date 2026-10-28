import os

import requests
from django.core.exceptions import ImproperlyConfigured

API_BASE_URL = "https://api.spoonacular.com"
SPOONACULAR_ANALYZE_URL = f"{API_BASE_URL}/recipes/analyze"
RECIPE_PAGE_SIZE = 6


def _api_key():
    key = os.getenv("SPOONACULAR_API_KEY", "").strip()
    if not key:
        raise ImproperlyConfigured("SPOONACULAR_API_KEY is not configured.")
    return key


def analyze_with_spoonacular(*, title, ingredients, instructions="", servings=1):
    api_ingredients = (
        [line.strip() for line in ingredients.splitlines() if line.strip()]
        if isinstance(ingredients, str) else ingredients
    )
    response = requests.post(
        SPOONACULAR_ANALYZE_URL,
        params={"apiKey": _api_key(), "includeNutrition": "true"},
        json={
            "title": title,
            "servings": servings,
            "ingredients": api_ingredients,
            "instructions": instructions,
        },
        timeout=12,
    )
    response.raise_for_status()
    return response.json()


def search_spoonacular_recipes(*, query="", diet="", max_ready_time=None, offset=0):
    params = {
        "apiKey": _api_key(),
        "query": query,
        "number": RECIPE_PAGE_SIZE,
        "offset": offset,
        "addRecipeInformation": "true",
        "addRecipeNutrition": "true",
        "sort": "popularity",
    }
    if diet:
        params["diet"] = diet
    if max_ready_time:
        params["maxReadyTime"] = max_ready_time
    response = requests.get(f"{API_BASE_URL}/recipes/complexSearch", params=params, timeout=12)
    response.raise_for_status()
    return response.json()


def search_spoonacular_ingredients(query):
    response = requests.get(
        f"{API_BASE_URL}/food/ingredients/autocomplete",
        params={"apiKey": _api_key(), "query": query, "number": 8},
        timeout=8,
    )
    response.raise_for_status()
    return response.json()


def get_spoonacular_recipe(recipe_id):
    response = requests.get(
        f"{API_BASE_URL}/recipes/{int(recipe_id)}/information",
        params={"apiKey": _api_key(), "includeNutrition": "true"},
        timeout=12,
    )
    response.raise_for_status()
    return response.json()
