import os
from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import transaction
from version_tracker.models import AppVersion, FinalVersion
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Automatic versioning based on file changes'

    # تنظیمات ثابت
    MONITORED_APPS = {'RCMS', 'hse', 'Reservations', 'facility', 'core', 'accounts', 'version_tracker'}

    def handle(self, *args, **kwargs):
        logger.info("Starting version update process...")
        updates = self.update_app_versions()
        if updates:
            self.stdout.write(self.style.SUCCESS(f"Versions updated: {updates}"))
            logger.info(f"Versions updated: {updates}")
        else:
            self.stdout.write("No changes detected.")
            logger.info("No changes detected.")

        self.stdout.write("Updating final version...")
        with transaction.atomic():
            FinalVersion.calculate_final_version()
        self.stdout.write(self.style.SUCCESS("Final version updated successfully!"))
        logger.info("Final version updated successfully!")

    def update_app_versions(self):
        updates = {}
        for app_config in apps.get_app_configs():
            if app_config.name not in self.MONITORED_APPS:
                logger.debug(f"Skipping app: {app_config.name} (not in monitored apps)")
                continue

            app_name = app_config.name
            app_path = app_config.path
            logger.info(f"Checking {app_name} for changes...")
            new_version = AppVersion.update_version(app_path, app_name)
            if new_version:
                updates[app_name] = new_version.version_number

        return updates