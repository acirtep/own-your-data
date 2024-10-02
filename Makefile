local_run:
	streamlit run own_your_data/home.py


check:
	pre-commit install --hook-type commit-msg --hook-type pre-push && \
	pre-commit run --all-files


test_csv:
	python own_your_data/tests/generate_csv.py