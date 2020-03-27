import pathlib
import csv
from tqdm import tqdm

FILTER_MINIMUM_ACTIVE_NUMBERS = 2000

class DailyData():
    def __init__(self):
        self.confirmed = 0
        self.deaths = 0
        self.recovered = 0

    @property
    def active(self):
        return self.confirmed - self.deaths - self.recovered

class Country():
    def __init__(self, name):
        self.name = name
        self.full_name = self.name.strip()
        self.data = {}
        self.country_id = self.full_name
    
    def add_data(self, date, type, value):
        if date not in self.data:
            self.data[date] = DailyData()
        if value:
            value = int(value)
        else:
            value = 0
        if type == 'confirmed':
            self.data[date].confirmed += value
        elif type == 'recovered':
            self.data[date].recovered += value
        elif type == 'deaths':
            self.data[date].deaths += value
        else:
            raise ValueError(f'Unknown type: {type}')

    def get_data(self, date):
        if date in self.data:
            return self.data[date]
        return DailyData()

    @property
    def max_active(self):
        max_active = 0
        for day_data in self.data.values():
            max_active = max(max_active, day_data.active)
        return max_active

countries = {}

def get_country(name):
    name = name.replace('Mainland ', '')
    name = name.replace(' (Islamic Republic of)', '')
    if name == 'Republic of Korea' or name == 'Korea, South':
        name = 'South Korea'
    new_country = Country(name)
    country_id = new_country.country_id
    if country_id not in countries:
        countries[country_id] = new_country
    return countries[country_id]

all_dates = []

time_series_folder = pathlib.Path('.') / 'COVID-19' / 'csse_covid_19_data' / 'csse_covid_19_daily_reports'
for daily_report_file in tqdm(list(time_series_folder.glob('*.csv')), desc='Load'):
    with daily_report_file.open(newline='', encoding='utf-8-sig') as f:
        date = daily_report_file.stem
        all_dates.append(date)
        reader = csv.DictReader(f)
        for province in reader:
            try:
                country = get_country(province['Country/Region'])
            except KeyError:
                country = get_country(province['Country_Region'])
            country.add_data(date, 'confirmed', province['Confirmed'])
            country.add_data(date, 'deaths', province['Deaths'])
            country.add_data(date, 'recovered', province['Recovered'])

def convert_date(date_str):
    month, day, year = date_str.split('-')
    return f'{year}-{month}-{day}'

with pathlib.Path('report.txt').open('w', encoding='utf-16', newline='') as f:
    writer = csv.writer(f, dialect='excel-tab')
    country_list = list(country for country in countries.values() if country.max_active > FILTER_MINIMUM_ACTIVE_NUMBERS)
    header = ['Date'] + [country.full_name for country in country_list]
    writer.writerow(header)

    for date in sorted(all_dates):
        row = [convert_date(date)]
        for country in country_list:
            data_num = country.get_data(date).active
            data_str = str(data_num).replace('.', ',')
            row.append(data_str)
        writer.writerow(row)
