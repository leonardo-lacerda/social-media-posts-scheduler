import time
from core.settings import log
from threading import Thread, Event
from django.core.management.base import BaseCommand
from integrations.post_management import post_scheduled_posts

stop_event = Event()


def runner():
    while not stop_event.is_set():
        try:
            post_scheduled_posts()
            time.sleep(5)
        except KeyboardInterrupt:
            break
        except Exception as err:
            log.exception(err)
            continue


class Command(BaseCommand):
    help = "Run Poster."

    def handle(self, *args, **options):

        poster = Thread(target=runner)

        try:
            log.info("Poster started!")
            poster.start()
            while poster.is_alive():
                poster.join(timeout=1)
        except KeyboardInterrupt:
            log.info("Stopping poster...")
            stop_event.set()
            poster.join()
            log.info("Poster stopped!")
