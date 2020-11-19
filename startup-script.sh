#! /bin/bash
sudo rm -rf /home/rachel/sqlScripts
sudo mkdir /home/rachel/sqlScripts
sudo gcloud auth activate-service-account --key-file=Your_google_credential_path
sudo gsutil cp gs://bucket_that_saved_sql_scripts/* /home/rachel/sqlScripts
sudo python3 /home/rachel/run_scripts.py --username=azure_db_username \
--databasenameazure=azure_db_name \
--server=azure_db_server \
--driver=azure_db_driver \
--filedire=/home/rachel/sqlScripts \
--datasetnamebigquery=databsename_in_bigquery \
--googleappcredentials=google_credential_path
