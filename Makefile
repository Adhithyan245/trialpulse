.PHONY: test web demo docker

test:
	.venv/Scripts/python -m pytest -q

web:
	cd web && npm ci && npm run build

demo:
	python -m uvicorn trialpulse.api.app:app --port 8000

docker:
	docker build -t trialpulse . && docker run -p 8000:8000 trialpulse
