# Football Analysis Notebooks

This repository contains Jupyter notebooks for analyzing football statistics data. 

## Data

There is a static set of data that is available [here](https://lswebworld.com/nfl.zip) for download. The information is structured in Apache Parquet files and sectioned 
into Player and Team statistics.

There also contains some information related to Game information and the Schedule.

## Notebooks

The solution contains notebooks for the following:

- fantasy.ipynb: Allows graphing of fantasy football scoring trends based on your league's scoring.
- power-ranking.ipynb: Work in progress for identifying features for Team power rankings.

## Helpers

The Helpers package contains some functions used for data preparation and retrieving files from Minio.