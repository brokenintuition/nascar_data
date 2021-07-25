import os
import pandas as pd 
import argparse
import logging
from datetime import datetime

output_format = '{series}_seasons_v1.csv'

def apply_column_fixes(df):
    # pole speed has text 'NTT' whenever there was no qualifying (normally because of rain)
    # 2020 is a mess because of the pandemic causing no qualifying. Some have NTT, some have DFP, some are blank
    # Also add 2021 to the "mess" list
    df['PoleSpeed'] = pd.to_numeric(df['PoleSpeed'], errors='coerce')

    # after charter system was implemented, purse stopped being published,
    # will be NaN after the 2015 season
    df['Purse'] = pd.to_numeric(df['Purse'].apply(lambda x: x.replace(',', '')), errors='coerce')

    df['Date'] = pd.to_datetime(df['Date'], format='%m/%d/%y')
    df['StageAdjustCautions'] = df.apply(stage_adjust_cautions, axis=1)
    df['TrackType'] = df.apply(get_track_type, axis=1)

    # Keeping track of races that weren't scheduled distance - shortened could mean
    # StageAdjustCautions is incorrect, because race is official at earlier of half-distance or 
    # the end of stage 2. Rain could mean more cautions than normal due to weather
    # Overtime is likely interesting because of late race cautions
    df['IsShortened'] = df['ScheduledMiles'] > df['MilesRun']
    df['IsOvertime'] = df['ScheduledMiles'] < df['MilesRun']
    df['MilesPerCaution'] = df['MilesRun'] / df['NumCautions']
    df['StageAdjustMilesPerCaution'] = df['MilesRun'] / df['StageAdjustCautions']


def stage_adjust_cautions(row):
    stage_start = datetime(2017, 1, 1)
    base_cautions = row['NumCautions']
    race_date = row['Date']

    # stage cautions introduced for 2017 season, everything before that doesn't need adjustment
    if race_date < stage_start:
        return base_cautions
    
    # Coke 600 at Charlotte has 4 stages for some reason
    # potentially incorrect if race is rain-shortened
    if row['Track'] == 'Charlotte' and row['ScheduledMiles'] == 600:
        return base_cautions - 3

    # everything else has 3 stages (again, unless rain-shortened)
    return base_cautions - 2

def get_track_type(row):
    if row['TrackSurface'] == 'R':
        return 'Road'

    if row['TrackSurface'] == 'D':
        return 'Dirt'

    track_length = row['TrackLength']

    if track_length < 1:
        return 'Short'
    if track_length <= 2: # whether or not 2 mile tracks are 
        return 'Intermediate'
    return 'Superspeedway'

def combine_season_data(input_dir, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    result_by_series = {}
    for path in os.listdir(input_dir):
        series = path[0:path.index('_')]

        season_df = pd.read_csv(os.path.join(input_dir, path))

        if series in result_by_series:
            result_df = result_by_series[series]
            result_by_series[series] = result_df.append(season_df)
        else:
            result_by_series[series] = season_df

    for series, season_data in result_by_series.items():
        apply_column_fixes(season_data)
        output_file = os.path.join(output_dir, output_format.format(series=series))
        logging.info('Writing output file %s', output_file)
        season_data.to_csv(output_file, index=False)
        
        
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', help='where to pull season files from')
    parser.add_argument('-o', '--output', help='where to place output files', required=True)
    parser.add_argument('-l', '--log', help='log file directory', required=True)

    args = parser.parse_args()

    os.makedirs(args.log, exist_ok=True)
    log_file = os.path.join(args.log, f'racing-reference-season-cleaner_{os.getpid()}.log')
    log_format = '%(asctime)-15s %(levelname)s %(name)-8s %(message)s'
    logging.basicConfig(filename=log_file, format=log_format, level=logging.DEBUG)

    logging.info('Starting translation from %s', args.input)
    combine_season_data(args.input, args.output)

