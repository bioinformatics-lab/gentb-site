"""
Examine existing PredictDataset objects.

- Retrieve files from confirmed dropbox links
"""

from __future__ import print_function
import sys
from os.path import dirname, realpath

if __name__=='__main__':
    django_dir = dirname(dirname(dirname(realpath(__file__))))
    sys.path.append(django_dir)
    #os.environ['DJANGO_SETTINGS_MODULE'] = 'tb_website.settings.local'

    # Allows the working environ to get set-up, apps registered, etc
    #
    import django
    django.setup()


from apps.predict.models import PredictDataset

from apps.dropbox_helper.models import DropboxRetrievalLog
from apps.dropbox_helper.dropbox_retriever import DropboxRetriever

import logging
LOGGER = logging.getLogger('apps.dropbox_helper.dropbox_retrieval_runner')

class DropboxRetrievalRunner:

    def __init__(self, dbox_log):
        assert isinstance(dbox_log, DropboxRetrievalLog), "dbox_log must be an instance of DropboxRetrievalLog"

        LOGGER.debug("Initiate dropbox retrieval for: %s", dbox_log.dataset)
        LOGGER.debug(" - dropbox_url:  dropbox retrieval for: %s",\
            dbox_log.dataset.dropbox_url)

        self.dbox_log = dbox_log
        self.predict_dataset = self.dbox_log.dataset

        # Error messages
        self.err_found = False
        self.err_msg = None

        # Run retrieval_error
        self.run_dropbox_retrieval()

    def set_error_message(self, m):
        """
        Set internal error flag and store the message within this object
        """
        LOGGER.error("Error found during dropbox file retrieval: %s", m)

        self.err_found = True
        self.err_msg = m


    def record_retrieval_error(self, error_msg):

        self.set_error_message(error_msg)
        #msg = "There was an error retrieving the dropbox files."

        # Update dataset status
        #
        self.predict_dataset.set_status_file_retrieval_error()

        # Update dropbox log
        #
        self.dbox_log.retrieval_error = error_msg
        self.dbox_log.set_retrieval_end_time(self, files_retrieved=False)
        self.dbox_log.save()

    def run_dropbox_retrieval(self):

        if self.err_found:
            return False


        # Reset log attributes and mark the retrieval start time
        #
        self.dbox_log.set_retrieval_start_time(with_reset=True)
        self.dbox_log.save()

        # Update PredictDataset status to 'file retrieval started'
        #
        self.dbox_log.dataset.set_status_file_retrieval_started()

        dr = DropboxRetriever(self.predict_dataset.dropbox_url,
                        self.predict_dataset.file_directory,
                        file_patterns=self.predict_dataset.get_file_patterns())

        if dr.err_found:
            self.record_retrieval_error(dr.err_msg)
            return False

        # Get the metadata
        #
        if not dr.step1_retrieve_metadata():
            self.record_retrieval_error(dr.err_msg)
            return False

        # Does it have what we want?
        #
        if not dr.step2_check_file_matches():
            self.record_retrieval_error(dr.err_msg)
            return False

        # Download the files
        #
        if not dr.step3_retrieve_files():
            self.record_retrieval_error(dr.err_msg)
            return False

        # ----------------------
        # Success!
        # ----------------------
        self.predict_dataset.set_status_file_retrieval_complete()
        self.dbox_log.selected_files = dr.final_file_paths
        self.dbox_log.set_retrieval_end_time(files_retrieved=True)
        self.dbox_log.save()


    @staticmethod
    def retrieve_dataset_files(dataset_id):
        """
        Given a dataset id, retrieve the dropbox link files, REGARDLESS of previous attempts

        For running form the command line, output is print statments
        """
        # Get PredictDataset
        #
        try:
            dataset = PredictDataset.objects.get(pk=dataset_id)
        except PredictDataset.DoesNotExist:
            print ('Failed.  There is no "PredictDataset" with db id: {0}'.format(dataset_id))
            return False

        # Get DropboxRetrievalLog object
        #
        dbox_log = DropboxRetrievalLog.objects.filter(dataset=dataset).first()
        if dbox_log is None:
            print ('Failed.  There is no "DropboxRetrievalLog" for the PredictDataset')
            return False

        # Run it
        #
        dr = DropboxRetrievalRunner(dbox_log)


    @staticmethod
    def retrieve_new_dropbox_files(**kwargs):
        """
        Are there DropboxRetrievalLog objects
        where the download process hasn't started?

        Yes, start retrieving the files

        Alternate: **kwargs={ 'retry_files_with_errors' : True}
            Try to download files where the process encountered an error
        """
        LOGGER.debug("retrieve_new_dropbox_files")

        retry_files_with_errors = kwargs.get('retry_files_with_errors', True)
        if retry_files_with_errors is True:
            # Files where download encountered an error
            #
            qs_args = dict(retrieval_error__isnull=False)
        else:
            # Files where download process hasn't started
            #
            qs_args = dict(retrieval_start__isnull=True)

        # Get files that haven't been retrieved from dropbox urls
        #
        dbox_logs_to_check = DropboxRetrievalLog.objects.filter(**qs_args\
                            ).exclude(files_retrieved=True)

        cnt = dbox_logs_to_check.count()
        if cnt == 0:
            status_msg = 'All set.  Nothing to check'
            print(status_msg)
            LOGGER.debug(status_msg)
            return

        print('Checking {0} link(s)'.format(cnt))

        for dbox_log in dbox_logs_to_check:
            # Go get the files!
            print('Get files for: ', dbox_log)
            dr = DropboxRetrievalRunner(dbox_log)


if __name__=='__main__':
    args = sys.argv
    if len(args) == 1:
        # PredictDatasets where download not yet attempted
        #
        DropboxRetrievalRunner.retrieve_new_dropbox_files()

    elif len(args) == 2 and args[1] == '--retry':
        # PredictDatasets where download previously failed
        #
        retry_param= dict(retry_files_with_errors=True)
        DropboxRetrievalRunner.retrieve_new_dropbox_files(**retry_param)

    elif len(args) == 2 and args[1].isdigit():
        # Single PredictDataset specified by database id, regardless of status
        #
        DropboxRetrievalRunner.retrieve_dataset_files(dataset_id=args[1])

    else:
        print('-' * 40)
        print("""Regular run of new dropbox links:
    >python dropbox_retrieval_runner.py

Retry dropbox links with errors:
    >python dropbox_retrieval_runner.py --retry

Retrieve dropbox link files for a specifiec PredictDataset:
    >python dropbox_retrieval_runner.py (dataset id)
   e.g. >python dropbox_retrieval_runner.py 102
        """)
