local_run:
	streamlit run own_your_data/home.py


check:
	pre-commit install --hook-type commit-msg --hook-type pre-push && \
	pre-commit run --all-files


demo_csv:
	python own_your_data/demo/generate_csv.py

