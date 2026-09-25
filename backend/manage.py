#!/usr/bin/env python
import os
import sys
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "autowallstein_project.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Make sure it is installed and available on your PYTHONPATH."
        ) from exc
    execute_from_command_line(sys.argv)
