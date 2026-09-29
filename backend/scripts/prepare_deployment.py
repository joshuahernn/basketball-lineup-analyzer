"""Initialize a dedicated deployment database without replacing existing data."""

import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from django.core.management import call_command
from django.db import connection, transaction

from app.dbmodels.models import Game, Player, Possession, Team
from scripts.ingest_raw_data import (
    ingest_games,
    ingest_players,
    ingest_possessions,
    ingest_teams,
)


def prepare_deployment():
    with connection.cursor() as cursor:
        cursor.execute('CREATE SCHEMA IF NOT EXISTS app')

    call_command('migrate', interactive=False)

    with transaction.atomic():
        # Serialize initialization if two deployment instances start together.
        with connection.cursor() as cursor:
            cursor.execute('SELECT pg_advisory_xact_lock(748215)')

        if any(model.objects.exists() for model in (Team, Game, Player, Possession)):
            print('Existing basketball data retained.')
            return

        ingest_teams()
        ingest_games()
        ingest_players()
        ingest_possessions()
        print('Demo basketball data initialized.')


if __name__ == '__main__':
    prepare_deployment()
