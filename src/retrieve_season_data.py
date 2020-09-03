import bs4
import requests
import os
import re
import pandas as pd

base_url = 'https://www.racing-reference.info/season-stats/{year}/W/'
download_years = [x for x in range(2000,2021)]
laps_re = re.compile(r'([0-9]+) laps\*? on a [0-9]*\.[0-9]+.*\(([0-9]+\.[0-9])')

def get_scheduled_distance(url):
    # 200 laps on a 2.500 mile paved track (500.0 miles)
    page = requests.get(url)
    soup = bs4.BeautifulSoup(page.content, 'html.parser')
    m = laps_re.search(soup.text)
    laps = m.group(1) 
    distance = m.group(2)
    return laps, distance
    

def get_data_for_year(year, url):
    print('Retrieving data for year {year}'.format(year=year))
    num_columns = 17
    # there's an extra column after Winner for whatever reason, just drop it for code simplicity
    column_names = ['RaceNumber', 'Date', 'Track', 'Cars', 'Winner', 'Drop', 'WinnerStart', 'WinnerMake', 'TrackLength', 'TrackSurface',
                    'MilesRun', 'Purse', 'PoleSpeed', 'NumCautions', 'LapsUnderCaution', 
                    'AvgSpeed', 'LeadChanges', 'ScheduledLaps', 'ScheduledMiles']

    data = pd.DataFrame(columns = column_names)

    page_url = url.format(year=year)
    page = requests.get(page_url)

    soup = bs4.BeautifulSoup(page.content, 'html.parser')
    all_rows = soup.find_all('div', {'class': 'table-row'})
    for row in all_rows:
        cells = row.find_all('div', {'role': 'cell'}) 

        # current season has fewer cells for races that haven't happened yet
        if len(cells) != num_columns:
            continue

        race_details = cells[0]
        race_details_link = race_details.find('a')
        scheduled_laps, scheduled_miles = get_scheduled_distance(race_details_link['href'])

        row_data = {}
        for i in range(num_columns):
            row_data[column_names[i]] = cells[i].text

        row_data['ScheduledLaps'] = scheduled_laps
        row_data['ScheduledMiles'] = scheduled_miles

        data = data.append(row_data, ignore_index=True)

    data['Year'] = year
    data.drop(columns='Drop', inplace=True)

    return data


def download_data(years, url):
    return pd.concat([get_data_for_year(y, url) for y in years])

def download_season_data(output_filename):
    data = pd.concat([get_data_for_year(y, base_url) for y in download_years])
    data.to_csv(output_filename, index=False)


if __name__ == '__main__':
    download_season_data(os.path.join('data', 'season_data.csv'))
