dev:
	python manage.py runserver

poster:
	python manage.py runposter


migrate-all:
	python manage.py makemigrations
	python manage.py migrate
	python manage.py makemigrations integrations 
	python manage.py migrate integrations 
	python manage.py makemigrations socialsched 
	python manage.py migrate socialsched


purge-migration-dirs:
	rm -rf integrations/migrations
	rm -rf socialsched/migrations


purge-db:
	make purge-migration-dirs
	rm data/db.sqlite


prep-prod:
	make migrate-all
	pdm export -o requirements.txt
	python manage.py collectstatic --noinput
	rm -rf staticfiles/django-browser-reload

web:
	waitress-serve --threads 2 --listen=*:8000 core.wsgi:application

start:
	docker compose up -d --force-recreate

stop:
	docker compose down

build:
	docker compose build

applogs:
	docker compose logs app poster -ft

appexec:
	docker compose exec app bash