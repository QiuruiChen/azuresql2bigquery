#!/usr/bin/env bash

# following the instruction:
#Scheduling compute instances with Cloud Scheduler
# https://cloud.google.com/scheduler/docs/start-and-stop-compute-engine-instances-on-a-schedule

PROJECT_ID=$(gcloud config list project --format "value(core.project)")
SERVICE_ACCOUNT=your_service_account
ZONE=europe-west4-a
VM_NAME=dev-instance

#Set up the Compute Engine instance
gcloud compute instances create $VM_NAME \
    --service-account $SERVICE_ACCOUNT \
    --network default \
    --zone $ZONE \
    --image-family ubuntu-1804-lts \
    --image-project ubuntu-os-cloud \
    --labels=env=dev

gcloud compute instances add-metadata $VM_NAME \
    --metadata-from-file startup-script=startup-script.sh

#Set up the Cloud Functions functions with Pub/Sub
#Create and deploy the functions
#Create the Pub/Sub topics.
gcloud pubsub topics create start-instance-event
gcloud pubsub topics create stop-instance-event

git clone https://github.com/GoogleCloudPlatform/nodejs-docs-samples.git
cd nodejs-docs-samples/functions/scheduleinstance/
#Create the start and stop functions.
gcloud functions deploy startInstancePubSub \
    --trigger-topic start-instance-event \
    --service-account \
    --runtime nodejs8

gcloud functions deploy stopInstancePubSub \
    --trigger-topic stop-instance-event \
    --service-account $SERVICE_ACCOUNT \
    --runtime nodejs8

# (Optional) Verify the functions work
# Stop the instance
gcloud functions call stopInstancePubSub \
    --data '{"data":"eyJ6b25lIjoidXMtd2VzdDEtYiIsICJsYWJlbCI6ImVudj1kZXYifQo="}'
#Start the instance
gcloud functions call startInstancePubSub \
    --data '{"data":"eyJ6b25lIjoidXMtd2VzdDEtYiIsICJsYWJlbCI6ImVudj1kZXYifQo="}'


## Set up the Cloud Scheduler jobs to call Pub/Sub
## Create the VM start jobs
gcloud beta scheduler jobs create pubsub startup-dev-instances \
    --schedule '0 8 * * 0' \
    --topic start-instance-event \
    --message-body '{"zone":"europe-west4-a", "label":"env=dev"}' \
    --time-zone 'Europe/Amsterdam'

## Create the VM stop job.
gcloud beta scheduler jobs create pubsub shutdown-dev-instances \
    --schedule '0 18 * * 0' \
    --topic stop-instance-event \
    --message-body '{"zone":"europe-west4-a", "label":"env=dev"}' \
    --time-zone 'Europe/Amsterdam'

## start VM
gcloud compute instances start $VM_NAME  --zone=$ZONE
## transfer files into /home/rachel directory
gcloud compute scp --project=$PROJECT_ID  --zone=$ZONE --recurse driverInstall.sh $VM_NAME:~/
gcloud compute scp --project=$PROJECT_ID  --zone=$ZONE --recurse run_scripts.py $VM_NAME:~/
## connecting to VM, install packages that needed for connecting azure SQL, then exit ssh
gcloud compute ssh --project=$PROJECT_ID --zone=$ZONE  $VM_NAME -- 'bash driverInstall.sh && exit'

## addig shutdown script into VM
gcloud compute instances add-metadata $VM_NAME \
    --metadata-from-file shutdown-script=shutdown-script.sh

# check the shutdown script
sudo google_metadata_script_runner --script-type shutdown --debug
## go con cloud scheduler console page and click run now to test schedulers
## check the VM state
#gcloud compute instances describe dev-instance \
#    --zone europe-west4-b \
#    | grep status

## adding startup script into VM
gcloud compute instances add-metadata $VM_NAME \
    --metadata-from-file startup-script=startup-script.sh
