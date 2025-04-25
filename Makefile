dev:
	uv run python manage.py runserver

poster:
	uv run python manage.py runserver runposter


migrate-all:
	uv run python manage.py makemigrations
	uv run python manage.py migrate
	uv run python manage.py makemigrations integrations 
	uv run python manage.py migrate integrations 
	uv run python manage.py makemigrations socialsched 
	uv run python manage.py migrate socialsched


purge-migration-dirs:
	rm -rf integrations/migrations
	rm -rf socialsched/migrations


purge-db:
	make purge-migration-dirs
	rm data/db.sqlite


prep-prod:
	make migrate-all
	uv run python manage.py collectstatic --noinput
	rm -rf staticfiles/django-browser-reload


start:
	docker compose up -d --build --force-recreate --remove-orphans

stop:
	docker compose down

build:
	docker compose build

applogs:
	docker compose logs app poster -ft

appexec:
	docker compose exec app bash