## executing sql in auzreSQL and streaming result into bigquery

- RUN run.sh to create pipeline: ![](assets/markdown-img-paste-20201119154157816.png)

- In `startup-script.sh` and `shutdown-script.sh` customize your parameters
    - startup.sh:
        1. read sql text files from GCS bucket
        2. executing sql in AzureSQL
        3. streaming results into bigquery

    - shutdown-script.sh:
        1. uploading logging files into GCS bucket
