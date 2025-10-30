from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from todo.models import Auth_names, Quotes


class Command(BaseCommand):
    help = "Import quotes from a text file with lines formatted as 'quote - author'"

    def add_arguments(self, parser):
        parser.add_argument(
            "file",
            nargs="?",
            type=str,
            help="Path to input text file; defaults to scripts/Quotes.txt under BASE_DIR",
        )

    def handle(self, *args, **options):
        file_arg = options.get("file")
        default_path = Path(settings.BASE_DIR) / "scripts" / "Quotes.txt"
        file_path = Path(file_arg) if file_arg else default_path

        if not file_path.exists():
            raise CommandError(f"Input file not found: {file_path}")

        created_count = 0
        skipped_count = 0

        with file_path.open("r", encoding="utf8") as f:
            for lineno, raw in enumerate(f, start=1):
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                # Split on the last hyphen to tolerate hyphens in quote text
                parts = [p.strip() for p in line.rsplit("-", 1)]
                if len(parts) != 2:
                    self.stdout.write(self.style.WARNING(f"Line {lineno}: malformed; skipping"))
                    skipped_count += 1
                    continue
                quote, author = parts
                if not quote or not author:
                    skipped_count += 1
                    continue
                auth_obj, _ = Auth_names.objects.get_or_create(name=author)
                obj, created = Quotes.objects.get_or_create(quote=quote, auth=auth_obj)
                created_count += int(created)

        self.stdout.write(self.style.SUCCESS(
            f"Imported {created_count} quotes, skipped {skipped_count}."
        ))
