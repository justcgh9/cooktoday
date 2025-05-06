from pytest import fixture

from src.what_to_cook.api_client import MealDBClient


@fixture
def client():
    return MealDBClient()


@fixture
def mocked_client_url(mocker):
    return mocker.patch.object(MealDBClient, "BASE_URL", "test")


@fixture
def mocked_requests(mocker):
    return mocker.patch("src.what_to_cook.api_client.requests")


def test_fetch_meals_by_first_letter(client, mocked_requests, mocked_client_url):
    client.fetch_meals_by_first_letter("l")
    mocked_requests.get.assert_called_with("testsearch.php?f=l", timeout=5)


def test_fetch_empty_meals(client, mocked_requests, mocked_client_url):
    client.fetch_all_meals()
    mocked_requests.get.call_count == 26


def test_fetch_all_meals(client, mocked_requests, mocked_client_url):
    mocked_requests.get.return_value.json.return_value = {"meals": [{"idMeal": "test"}]}
    response = client.fetch_all_meals()
    assert response == [{"idMeal": "test"}]


def test_get_meal_details(client, mocked_requests, mocked_client_url):
    client.get_meal_details(1)
    mocked_requests.get.assert_called_with("testlookup.php?i=1", timeout=10)
