import csv
import datetime
import json
import pathlib

from tqdm import tqdm

FILTER_MINIMUM_DEATHS = 1000


class DailyData:
    def __init__(self):
        self.confirmed = 0
        self.deaths = 0
        self.recovered = 0

    @property
    def active(self):
        return self.confirmed - self.deaths - self.recovered


class Country:
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
        if type == "confirmed":
            self.data[date].confirmed += value
        elif type == "recovered":
            self.data[date].recovered += value
        elif type == "deaths":
            self.data[date].deaths += value
        else:
            raise ValueError(f"Unknown type: {type}")

    def get_data(self, date):
        if date in self.data:
            return self.data[date]
        return DailyData()

    def get_diff(self, date):
        actual = self.get_data(date)
        previous = self.get_data(date - datetime.timedelta(days=7))
        diff_data = DailyData()
        diff_data.confirmed = actual.confirmed - previous.confirmed
        diff_data.deaths = actual.deaths - previous.deaths
        diff_data.recovered = actual.recovered - previous.recovered
        return diff_data

    @property
    def deaths(self):
        return list(self.data.values())[-1].deaths

    @property
    def last_week_deaths(self):
        last_deaths = list(self.data.values())[-1].deaths
        try:
            one_week_deaths = list(self.data.values())[-7].deaths
        except IndexError:
            one_week_deaths = 0
        return last_deaths - one_week_deaths


countries = {}


def get_country(name):
    name = name.replace("Mainland ", "")
    name = name.replace(" (Islamic Republic of)", "")
    if name == "Republic of Korea" or name == "Korea, South":
        name = "South Korea"
    new_country = Country(name)
    country_id = new_country.country_id
    if country_id not in countries:
        countries[country_id] = new_country
    return countries[country_id]


def convert_date(date_str):
    month, day, year = date_str.split("-")
    date = datetime.date(int(year), int(month), int(day))
    return date


all_dates = []

time_series_folder = (
    pathlib.Path(".")
    / "COVID-19"
    / "csse_covid_19_data"
    / "csse_covid_19_daily_reports"
)
for daily_report_file in tqdm(list(time_series_folder.glob("*.csv")), desc="Load"):
    with daily_report_file.open(newline="", encoding="utf-8-sig") as f:
        date = convert_date(daily_report_file.stem)
        all_dates.append(date)
        reader = csv.DictReader(f)
        for province in reader:
            try:
                country = get_country(province["Country/Region"])
            except KeyError:
                country = get_country(province["Country_Region"])
            country.add_data(date, "confirmed", province["Confirmed"])
            country.add_data(date, "deaths", province["Deaths"])
            country.add_data(date, "recovered", province["Recovered"])

all_dates = sorted(all_dates)

with pathlib.Path("report.txt").open("w", encoding="utf-16", newline="") as f:
    writer = csv.writer(f, dialect="excel-tab")
    country_list = list(
        country for country in countries.values() if country.last_week_deaths > 200
    )
    country_list = sorted(
        country_list, key=lambda country: country.deaths, reverse=True
    )

    header = ["Date"] + [country.full_name for country in country_list]
    writer.writerow(header)

    for date in all_dates:
        row = [date]
        for country in country_list:
            data_num = country.get_data(date).active
            data_str = str(data_num).replace(".", ",")
            row.append(data_str)
        writer.writerow(row)


def write_highcharts(name, calc_fn, dates=all_dates):
    highcharts_series = []
    for country in country_list:
        serie = {"name": country.full_name, "data": []}
        for date in dates:
            serie["data"].append(calc_fn(country, date))
        highcharts_series.append(serie)
    write_report(name, dates, highcharts_series)


def write_country(report_name, calc_fn):
    dates = all_dates
    country_name = "Hungary"
    country = get_country(country_name)
    serie = {"name": country.full_name, "data": []}
    for date in dates:
        serie["data"].append(calc_fn(country, date))
    write_report(f"{country_name} {report_name}", dates, [serie])


def write_report(name, dates, highcharts_series):
    template_text = pathlib.Path("template.html").read_text()
    html_text = template_text.replace(
        "[/*xAxis*/]", json.dumps([date.strftime("%m.%d.") for date in dates])
    )
    html_text = html_text.replace("[/*series*/]", json.dumps(highcharts_series))
    html_text = html_text.replace("{TITLE}", name)
    pathlib.Path(f"{name} report.html").write_text(html_text)


write_highcharts("deaths", lambda country, date: country.get_data(date).deaths)
write_highcharts("active", lambda country, date: country.get_data(date).active)
write_highcharts(
    "confirmed diff", lambda country, date: country.get_diff(date).confirmed
)
write_highcharts("deaths diff", lambda country, date: country.get_diff(date).deaths)
write_highcharts(
    "recovered diff", lambda country, date: country.get_diff(date).recovered
)

write_country("active", lambda country, date: country.get_data(date).active)
write_country("confirmed diff", lambda country, date: country.get_diff(date).confirmed)
write_country("deaths diff", lambda country, date: country.get_diff(date).deaths)
