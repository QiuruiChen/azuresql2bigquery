#! /bin/bash
sudo gsutil cp /home/rachel/*.log gs://bucket_that_saved_logging_files/
sudo rm -rf /home/rachel/*.log
