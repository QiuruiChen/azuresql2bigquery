#! /usr/bin/python3
import pyodbc
import google
from google.cloud import bigquery
import time
import argparse
import os
from os import listdir
from os.path import isfile, join
import logging
from datetime import datetime

filname = str(datetime.today().strftime('%Y-%m-%d-%H:%M:%S'))+".log"

def preproc_bq(row,tablename,datasetname_bq,records_amount,logging):
    try:
        client, table = None,None
        colnames = [ele[0] for ele in list(row[0].cursor_description)]
        datatypes = [str(ele[1]) for ele in list(row[0].cursor_description)]
        nullmodel =  [str(ele[6]) for ele in list(row[0].cursor_description)]

        # mapping field names into bigquery format
        datatype_mappings = {"<class 'int'>":"INT64","<class 'datetime.datetime'>":"DATETIME",
                             "<class 'datetime.date'>":"DATE","<class 'str'>":"STRING",
                             "<class 'bool'>":"BOOL","<class 'bytearray'>":"BYTES",
                             "<class 'datetime.time'>":"TIME","<class 'float'>":"FLOAT64",
                             "<class 'decimal.Decimal'>":'NUMERIC'}

        null_mapings = {"False":"Required","True":"Nullable"}

        datatype_bq = [datatype_mappings[ele] for ele in datatypes]
        model_bq = [null_mapings[ele] for ele in nullmodel]


        # # Construct a BigQuery client object.
        client = bigquery.Client()

        # TODO(developer): Set table_id to the ID of the table to fetch.
        dataset_id = "{}.{}".format(client.project,datasetname_bq)
        # dataset_id = "{}.{}".format(SERVER.split('.')[0],DATASETNAME_BQ)
        table_id = '{}.{}'.format(dataset_id,tablename)

        try:
            # Construct a full Dataset object to send to the API.
            dataset = bigquery.Dataset(dataset_id)
            dataset.location = "europe-west2"
            dataset = client.create_dataset(dataset)  # Make an API request.
            logging.info("Created dataset {}.{}".format(client.project, dataset.dataset_id))
        except google.api_core.exceptions.Conflict:
            pass

        try:
            query_job = client.query("SELECT COUNT(*) FROM "+datasetname_bq+'.'+tablename)
            results = query_job.result()  # Waits for job to complete.
            ori_data_amount = [res for res in results][0][0]

            if ori_data_amount == records_amount:
                insert_data = False
                logging.info("This table does not change...")
            else:
                print("%d data in the origianl table, %d data in the currrent table" % (ori_data_amount, records_amount))

                # delete tables
                client.delete_table(table_id, not_found_ok=True)  # Make an API request.
                logging.info("Deleted table '{}'.".format(tablename))

                try:
                    schema = [bigquery.SchemaField(colnames[idx],datatype_bq[idx],mode =model_bq[idx]) for idx,val in enumerate(datatype_bq)]
                    table = bigquery.Table(table_id, schema=schema)
                    table = client.create_table(table)  # Make an API request.
                    logging.info("Created table {}.{}.{}".format(table.project, table.dataset_id, table.table_id))
                except google.api_core.exceptions.Conflict:
                    pass

                insert_data = True

        except:
            # this table does not exist, so create this table
            try:
                schema = [bigquery.SchemaField(colnames[idx],datatype_bq[idx],mode =model_bq[idx]) for idx,val in enumerate(datatype_bq)]
                table = bigquery.Table(table_id, schema=schema)
                table = client.create_table(table)  # Make an API request.
                logging.info("Created table {}.{}.{}".format(table.project, table.dataset_id, table.table_id))
            except google.api_core.exceptions.Conflict:
                pass

            insert_data = True

        return insert_data, client, table

    except Exception as e:
        logging.critical(e, exc_info=True)  # log exception info at CRITICAL log level



def _get_ranges(Number,unit):
    Number = Number -1
    step = int(Number / unit)
    range_list = [(idx*unit,(idx+1)*unit-1) for idx in list(range(step))]
    if (Number % unit):
        range_list += [(step*unit,Number)]
    return range_list

def insert_data2bq(row,client,table,logging):
    try:
        logging.info("%d records are inserted" % len(row))
        if len(row) < 5001:
            while True:
                errors = client.insert_rows(table, row)  # Make an API request.
                if errors == []:
                    break
        else:
            rg_list = _get_ranges(len(row),5000)
            for (start_idx, end_idx) in rg_list:
                while True:
                    errors = client.insert_rows(table, row[start_idx:end_idx])  # Make an API request.
                    if errors == []:
                        break #inserted successfully
                    else:
                        logging.info("inserted errors:"+str(errors))
                        time.sleep(5)
                        logging.info("sleeping 5 seconds, trying again....")

    except Exception as e:
        logging.critical(e, exc_info=True)  # log exception info at CRITICAL log level


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, filename=filname, filemode="a+",
                        format="%(asctime)-15s %(levelname)-8s %(message)s")

    parser = argparse.ArgumentParser()

    # parameters for connecting Azure SQL
    parser.add_argument('-un','--username',
                    type=str,
                    default='your_username')
    parser.add_argument('-dnazure','--databasenameazure',
                    type=str,
                    default='azure databse name')
    parser.add_argument('-sv','--server',
                    type=str,
                    default='sever name')
    parser.add_argument('-ru','--ROWSUNIT',
                    type=int,
                    help='#Maximum rows per second: 1,000,000',
                    default=100000)
    parser.add_argument('-ps','--password',
                type=str,
                default='your_database_password')
    parser.add_argument('-dv','--driver',
                type=int,
                default='{ODBC Driver 17 for SQL Server}')
    parser.add_argument('-fd','--filedire',
                        type=str,
                        help='sql file directory',
                        default='path_to_your_sqlfiles_directory')
    parser.add_argument('-dnbigquery','--datasetnamebigquery',
                        type=str,
                        help='dataset name in bq',
                        default='datbase name in bq')
    parser.add_argument('-gp','--googleappcredentials',
                        type=str,
                        default='path_to_your_local_google_application_credentials')
    args = parser.parse_args()

    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = args.googleappcredentials
    logging.info("file directory that contains sql scripts is:"+str(args.filedire))
    file_names = [f for f in listdir(args.filedire) if isfile(join(args.filedire, f))]


    cnxn = pyodbc.connect('DRIVER='+args.driver+';SERVER='+args.server+';PORT=1433;DATABASE='+args.databasename+';UID='+args.username+';PWD='+ args.password)
    cursor = cnxn.cursor()

    for file in file_names:
        logging.info("Processing file " + str(file))
        File_object = open(args.filedire+"/"+file,"r+")
        sql_content = File_object.readlines()
        sql_content = ''.join(sql_content)
        cursor.execute(sql_content)

        TABLENAME = file.split('.')[0]
        rows = cursor.fetchall()
        logging.info("Inserting data into bigquery...")
        insert_data, client, table = preproc_bq(rows,TABLENAME,args.datasetname,len(rows),logging)

        if insert_data == True :
            insert_data2bq(rows,client,table,logging)

