import bs4
import requests
import os
import sys
import re
import argparse
import logging
import pandas as pd
from itertools import product

base_url = 'https://www.racing-reference.info/season-stats/{year}/{series}/'
output_format = '{series}_{year}_season_v1.csv'

# presumably for Winston, Busch, and Craftsman, which were the title sponsors at the time the website was launched
series_map = {'cup': 'W', 'xfinity': 'B', 'trucks': 'C' }

download_years = [x for x in range(2000,2021)]
laps_re = re.compile(r'([0-9]+) laps\*? on a [0-9]*\.[0-9]+ mile.*((track)|(course)) \(([0-9]+\.[0-9]+)')

def get_scheduled_distance(url):
    # 200 laps on a 2.500 mile paved track (500.0 miles)
    page = requests.get(url)
    soup = bs4.BeautifulSoup(page.content, 'html.parser')
    m = laps_re.search(soup.text)
    laps = m.group(1) 
    distance = m.group(5)
    return laps, distance
    

def retrieve_season_data(url):
    num_columns = 17
    # there's an extra column after Winner for whatever reason, just drop it for code simplicity
    column_names = ['RaceNumber', 'Date', 'Track', 'Cars', 'Winner', 'Drop', 'WinnerStart', 'WinnerMake', 'TrackLength', 'TrackSurface',
                    'MilesRun', 'Purse', 'PoleSpeed', 'NumCautions', 'LapsUnderCaution', 
                    'AvgSpeed', 'LeadChanges', 'ScheduledLaps', 'ScheduledMiles', 'DetailsUrl']

    data = pd.DataFrame(columns = column_names)

    page = requests.get(url)

    soup = bs4.BeautifulSoup(page.content, 'html.parser')
    all_rows = soup.find_all('div', {'class': 'table-row'})
    for row in all_rows:
        cells = row.find_all('div', {'role': 'cell'}) 

        # current season has fewer cells for races that haven't happened yet
        if len(cells) != num_columns:
            continue

        race_details = cells[0]
        race_details_link = race_details.find('a')
        details_url = race_details_link['href']
        scheduled_laps, scheduled_miles = get_scheduled_distance(details_url)

        row_data = {}
        for i in range(num_columns):
            row_data[column_names[i]] = cells[i].text

        # todo: scheduled distance isn't realy "raw", should move this to another processing step
        row_data['ScheduledLaps'] = scheduled_laps
        row_data['ScheduledMiles'] = scheduled_miles
        row_data['DetailsUrl'] = details_url

        data = data.append(row_data, ignore_index=True)

    data.drop(columns='Drop', inplace=True)

    return data


def download_seasons(years, series_names, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    for pair in product(years, series_names):
        year = pair[0]
        series = pair[1]
        file_path = os.path.join(output_dir, output_format.format(year=year, series=series))
        
        if os.path.exists(file_path):
            logging.info('File %s exists, skipping', file_path)
            continue

        logging.info('Beginning download for year %s, series %s', year, series)

        url = base_url.format(year=year, series=series_map[series])

        try:
            result = retrieve_season_data(url)
        except Exception as ex: # at some point be a little finer grained handling exceptions
            logging.exception(ex)
            return False

        result['Year'] = year

        logging.info('Saving file %s', file_path)

        try:
            result.to_csv(file_path, index=False)
        except Exception as ex:
            logging.exception(ex)
            return False

    return True

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--start', type=int, help='start year to download', required=True)
    parser.add_argument('-e', '--end', type=int, help='end year to download. Exclude to download only start year')
    parser.add_argument('--series', help='comma separated series to download (cup, xfinity, trucks)', required=True)
    parser.add_argument('-o', '--output', help='where to place output files', required=True)
    parser.add_argument('-l', '--log', help='log file directory', required=True)

    args = parser.parse_args()

    os.makedirs(args.log, exist_ok=True)
    log_file = os.path.join(args.log, f'racing-reference-season-downloader_{os.getpid()}.log')
    log_format = '%(asctime)-15s %(levelname)s %(name)-8s %(message)s'
    logging.basicConfig(filename=log_file, format=log_format, level=logging.DEBUG)

    if args.end is not None:
        years = [x for x in range(args.start, args.end + 1)]
    else:
        years = [args.start]

    logging.debug('Configured years: %s', ','.join([str(x) for x in years]))
    
    series = args.series.split(',')

    logging.debug('Configured series: %s', ','.join(series))

    logging.info('Beginning download')
    success = download_seasons(years, series, args.output)

    logging.info('Finished download')

    if not success:
        sys.exit(1)

    sys.exit(0)
