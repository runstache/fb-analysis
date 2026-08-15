"""
Data Helpers Module
"""

import os
from io import BytesIO

import pandas
from dotenv import load_dotenv
from minio import Minio
import json


class MinioHelper:
    """
    Class for Retrieving information from MinIO
    """

    client: Minio
    bucket: str

    @staticmethod
    def _load_credentials_(path:str) -> dict:
        """
        Loads the Credentials file
        :param path: Path to the file
        :return: Dictionary
        """
        with open(path, 'r') as creds_file:
            return json.load(creds_file)


    def __init__(self, bucket: str) -> None:
        """
        Constructor
        :param bucket: Minio Bucket
        """

        load_dotenv(override=True)

        # Create the Client for MinIO
        self.client = Minio(endpoint=os.getenv('MINIO_ENDPOINT'),
                            access_key=os.getenv('MINIO_KEY'),
                            secret_key=os.getenv('MINIO_SECRET'), cert_check=False, secure=False,
                            region='us-east-1')

        self.bucket = bucket

    def _get_files_(self, prefix: str) -> pandas.DataFrame | None:
        """
        Retrieves the Parquet Files for a given Year
        :param prefix: URL of the Parquet Location
        :return: Data Frame
        """
        frames = []
        stat_files = self.client.list_objects(bucket_name=self.bucket, prefix=prefix,
                                              recursive=True)


        for stat_file in stat_files:
            print(stat_file.object_name)
            response = self.client.get_object(self.bucket, stat_file.object_name)
            try:
                content = BytesIO(response.read())
                temp_frame = pandas.read_parquet(content, engine='pyarrow')
                frames.append(temp_frame)
            finally:
                response.close()
                response.release_conn()

        if frames:
            return pandas.concat(frames, ignore_index=True)
        return None

    def get_statistics(self, years: list[str], season: str, stat_type: str) -> pandas.DataFrame | None:
        """
        Retrieves the Parquet Files and Loads them to a DataFrame
        :param years: Collection of Years
        :param season: Season Type
        :param stat_type: Type of Statistics
        :return: DataFrame
        """

        frames = []
        for year in years:
            prefix = f"{stat_type}/{year}/{season}/"

            temp_frame = self._get_files_(prefix)
            if temp_frame is not None:
                frames.append(temp_frame)

        if frames:
            return pandas.concat(frames, ignore_index=True)

        return None
class CalcHelper:
    """
    Helper Class for calculating various statistics in a DataFrame
    """

    @staticmethod
    def calculate_points(frame: pandas.DataFrame, categories: dict) -> pandas.Series:
        """
        Adds the Points column to the DataFrame
        :param frame: Data Frame
        :param categories: Dictionary of Categories
        :return: Updated Frame
        """
        upd_frame = frame.copy()

        stat_keys = ['receptions', 'receivingyards', 'td', 'passingyards', 'rushingyards']
        for key in stat_keys:
            if key == 'td':
                upd_frame.loc[frame['statistic_code'] == 'td', 'points'] = \
                    upd_frame['statistic_value'] * categories.get('td', 0)
                continue

            upd_frame.loc[upd_frame['statistic_name'] == key, 'points'] = \
                upd_frame['statistic_value'] * categories.get(key, 0)
        upd_frame = upd_frame.fillna(0, axis='columns')
        return upd_frame.groupby(['player_name', 'player_url', 'year', 'week'])[
            'points'].sum().reset_index()

    @staticmethod
    def calculate_differential(left_frame: pandas.DataFrame,
                               right_frame: pandas.DataFrame, year: str) -> pandas.DataFrame:
        """
        Calculates the Scoring differentials from the Left and Right Frame.
        Adds the differential column to the left frame and returns it.
        :param left_frame: Current Year Frame
        :param right_frame: Previous Year Frame
        :param year: Year to keep
        :return: Current Year Frame with Scoring Differential
        """

        upd_frame = left_frame.merge(right_frame, how='left', suffixes=(None, '_r'),
                                     on=['player_url', 'week'])

        upd_frame['scoring_diff'] = upd_frame.apply(
            lambda row: 0 if row['points'] == 0 or row['points_r'] == 0 else row['points'] - row[
                'points_r'], axis=1)

        drop_columns = [x for x in upd_frame.columns if '_r' in x]
        upd_frame = upd_frame.drop(labels=drop_columns, axis=1)
        final_frame = upd_frame[upd_frame['year'] == int(year)]
        return final_frame

    @staticmethod
    def calculate_efficiency(frame: pandas.DataFrame):
        """
        Calculates the Offensive Efficiency Column
        :return: Data Frame
        """

        upd_frame = frame.copy()
        upd_frame['efficiency'] = upd_frame.apply(
            lambda row: (row['completions'] + row['rushingattempts']) / row['totaloffensiveplays'],
            axis=1)
        return upd_frame

    @staticmethod
    def add_points(frame: pandas.DataFrame, games_frame: pandas.DataFrame) -> pandas.DataFrame:
        """
        Adds the Points and Points against values to the Frame.
        :param frame: Stats Frame
        :param games_frame: Games Frame
        :return: Updates Stats Frame
        """

        upd_frame = frame.copy()

        upd_frame['points'] = upd_frame.apply(lambda row: games_frame.loc[
            (games_frame['home_team'] == row['team']) & (games_frame['year'] == row['year']) &
            (games_frame['week'] == row['week'])]['home_score'], axis=1)

        upd_frame['pointsagainst'] = upd_frame.apply(lambda row: games_frame.loc[
            (games_frame['home_team'] == row['team']) & (games_frame['year'] == row['year']) &
            (games_frame['week'] == row['week'])]['away_score'], axis=1)

        upd_frame['points'] = upd_frame.apply(lambda row: games_frame.loc[
            (games_frame['away_team'] == row['team']) & (games_frame['year'] == row['year']) &
            (games_frame['week'] == row['week'])]['away_score'], axis=1)

        upd_frame['pointsagainst'] = upd_frame.apply(lambda row: games_frame.loc[
            (games_frame['away_team'] == row['team']) & (games_frame['year'] == row['year']) &
            (games_frame['week'] == row['week'])]['home_score'], axis=1)

        return upd_frame

    @staticmethod
    def calculate_result(frame: pandas.DataFrame) -> pandas.DataFrame:
        """
        Calculates the Result Column.
        :param frame: Data Frame
        :return: Updated Frame
        """

        upd_frame = frame.copy()
        upd_frame['result'] = upd_frame.apply(
            lambda row: 'W' if row['points'] > row['pointsagainst'] else 'L', axis=1)
        return upd_frame
