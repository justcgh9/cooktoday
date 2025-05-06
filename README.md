# cooktoday

To start the project use the following commands

```bash
poetry install
poetry run streamlit run app.py
```


# To run tests

### Unit

```
poetry run pytest --cov=src --cov=app --cov-report=term-missing
```

Cur value: 73%

### Fuzzing

```
poetry run pytest --cov=app --cov=src --cov-branch tests/test_fuzzing.py
```

Cur value: 83%
