import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from app.helpers.nba_storage import import_nba_snapshot


class Command(BaseCommand):
    help = 'Validate and import a downloaded NBA game; retain other games and demo data.'

    def add_arguments(self, parser):
        default_directory = settings.BASE_DIR / 'raw_data/nba/2026-27/0022600002'

        parser.add_argument(
            'directory',
            nargs='?',
            type=Path,
            default=default_directory,
        )

        parser.add_argument(
            '--report',
            type=Path,
            help='Write the validation report to this local JSON file.',
        )

    def handle(self, *args, **options):
        directory = options['directory']
        report_path = options['report']

        try:
            result = import_nba_snapshot(directory)
        except (OSError, ValueError, KeyError) as error:
            raise CommandError(str(error)) from error

        if report_path:
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_json = json.dumps(result, indent=2) + '\n'
            report_path.write_text(report_json, encoding='utf-8')

        message = (
            f"Imported {result['source_game_id']}: {result['segments']} lineup segments, "
            f"{result['completed_possessions']} completed possessions."
        )

        self.stdout.write(self.style.SUCCESS(message))
