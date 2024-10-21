local_run:
	rm -rf ./own_your_data/own_your_data.db && streamlit run own_your_data/app.py


check:
	pre-commit install --hook-type commit-msg --hook-type pre-push && \
	pre-commit run --all-files


demo_file:
	python own_your_data/demo/generate_csv.py

test:
	pytest -v --durations 5 --cov own_your_data