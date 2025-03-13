.PHONY: local_run check demo_file test serve_desktop docs

local_run:
	streamlit run own_your_data/app.py

check:
	pre-commit install --hook-type commit-msg --hook-type pre-push && \
	pre-commit run --all-files


demo_file:
	python own_your_data/demo/generate_csv.py

test:
	pytest own_your_data/tests -v --durations 5 --cov own_your_data

serve_desktop:
	npm run dump && npm run serve

docs:
	mkdocs serve
