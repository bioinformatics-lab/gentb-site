
import logging
LOGGER = logging.getLogger('apps.dropbox')

from django.core.management.base import BaseCommand, CommandError
from apps.uploads.models import DropboxUploadFile, ManualUploadFile

class Command(BaseCommand):
    help = """Regular run of new dropbox links:

      manage.py dropbox_retrieval

    """
    def handle(self, **options):
        for d_file in DropboxUploadFile.objects.filter(retrieval_start__isnull=True):
            print " + Downloading: %s" % d_file.url
            d_file.download_now()
            if d_file.retrieval_error:
                print " ! Error downloading"

        for d_file in ManualUploadFile.objects.filter(retrieval_start__isnull=True):
            print " + Downloading: %s" % d_file.url
            d_file.download_now()
            if d_file.retrieval_error:
                print " ! Error downloading"


