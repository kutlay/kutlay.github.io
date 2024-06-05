---
title: Airflow - Daemonic processes are not allowed to have children
layout: post
category: errors
---

I am using the docker-compose.yml provided by Airflow to run <a href="https://airflow.apache.org/docs/apache-airflow/stable/howto/docker-compose/index.html" target="_BLANK">Airflow on Docker</a>. It is a fairly complete setup with a CeleryExecutor so you are not limited to 1 DAG run at a time.

Most of our data pipeline scripts use Python's `multiprocessing` to take advantage of the billion cores we have on our servers. I realized the docker-compose.yml provided by Airflow doesn't really work with `ProcessPoolExecutor` I am using from `concurrent.futures` (which is really just a wrapper for the multiprocessing library). This is because the default "celery worker" is using processes in the same way as `ProcessPoolExecutor` does.

If you Google the problem, you will see two things:

- People suggest using swapping `multiprocessing` with `billiard`: https://github.com/apache/airflow/issues/14896#issuecomment-908516288
- And people trying celery worker's `-P threads` option. https://github.com/apache/airflow/issues/14896#issuecomment-866768004

I like the second one more since first one means depending on a package I don't know.

In order to set the `-P threads` flag for your Airflow's celery workers, add the following to your  `docker-compose.yml`:

`AIRFLOW__CELERY__POOL: threads`

Do not try to add it to the `command:` in `airflow-worker` as I did, since that command becomes `airflow celery worker -P threads` which is not valid.

Problem solved!