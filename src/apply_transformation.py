import os
import pandas as pd 
from datetime import datetime

def apply_column_fixes(raw_filepath, output_filepath):
    df = pd.read_csv(raw_filepath)

    # pole speed has text 'NTT' whenever there was no qualifying (normally because of rain)
    # 2020 is a mess because of the pandemic causing no qualifying. Some have NTT, some have DFP, some are blank
    df['PoleSpeed'] = pd.to_numeric(df['PoleSpeed'], errors='coerce')

    # after charter system was implemented, purse stopped being published,
    # will be NaN after the 2015 season
    df['Purse'] = pd.to_numeric(df['Purse'].apply(lambda x: x.replace(',', '')), errors='coerce')

    df['Date'] = pd.to_datetime(df['Date'], format='%m/%d/%y')
    df['StageAdjustCautions'] = df.apply(stage_adjust_cautions, axis=1)

    df.to_csv(output_filepath)


def stage_adjust_cautions(row):
    stage_start = datetime(2017, 1, 1)
    base_cautions = row['NumCautions']
    race_date = row['Date']

    # stage cautions introduced for 2017 season, everything before that doesn't need adjustment
    if race_date < stage_start:
        return base_cautions
    
    # Coke 600 at Charlotte has 4 stages for some reason
    # potentially incorrect if race is rain-shortened
    if row['Track'] == 'Charlotte' and row['MilesRun'] > 500:
        return base_cautions - 3

    # everything else has 3 stages (again, unless rain-shortened)
    return base_cautions - 2


if __name__ == '__main__':
    input_path = os.path.join('data', 'season_data.csv')
    output_path = os.path.join('data', 'cleaned_season_data.csv')
    apply_column_fixes(input_path, output_path)
