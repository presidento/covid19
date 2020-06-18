import csv
import datetime
import json
import pathlib
import scripthelper

OUT_DIR = pathlib.Path(__file__).absolute().parent / "output"
TIME_SERIES_FOLDER = (
    pathlib.Path(__file__).absolute().parent
    / "COVID-19"
    / "csse_covid_19_data"
    / "csse_covid_19_daily_reports"
)

logger, ARGS = scripthelper.bootstrap_args()
scripthelper.setup_file_logging()

########################################################################################


class DailyData:
    def __init__(self):
        self.confirmed = 0
        self.deaths = 0
        self.recovered = 0

    @property
    def active(self):
        return self.confirmed - self.deaths - self.recovered


class Country:
    def __init__(self, name, population):
        self.name = name
        self.data = {}
        self.population = population

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


class Countries:
    def __init__(self):
        self._countries = {}
        self._population = {}
        self.all_dates = []

    def get(self, name):
        name = name.replace("*", "")
        name = name.replace("St.", "Saint")
        name = name.replace("Mainland ", "")
        name = name.replace(" (Islamic Republic of)", "")
        name = name.replace("Republic of", "")
        name = name.strip()
        if name == "Republic of Korea" or name == "Korea, South" or name == "Korea":
            name = "South Korea"
        if name == "Czechia":
            name = "Chech Republic"
        if name == "United Kingdom":
            name = "UK"
        if name == "Russian Federation":
            name = "Russia"
        if name not in self._countries:
            self._countries[name] = Country(name, self._population[name])
        return self._countries[name]

    def filtered_country_list(self):
        country_list = []
        for country in self._countries.values():
            if country.population < 9_000_000:
                continue
            if country.last_week_deaths < 200 and country.deaths < 5_000:
                continue
            country_list.append(country)
        country_list = sorted(
            country_list, key=lambda country: country.deaths, reverse=True
        )
        return country_list

    def load_data(self):
        self._load_population()
        self._parse_daily_files()

    def _parse_daily_files(self):
        logger.verbose("Loading daily data")
        all_dates = []
        world = self.get("World")
        skipped_country_regions = set()
        for daily_report_file in scripthelper.progressbar(
            list(TIME_SERIES_FOLDER.glob("*.csv")),
            desc="Load",
            disable=bool(ARGS.quiet),
        ):
            logger.debug(f"Loading daily data from {daily_report_file.stem}")
            with daily_report_file.open(newline="", encoding="utf-8-sig") as f:
                date = convert_date(daily_report_file.stem)
                all_dates.append(date)
                reader = csv.DictReader(f)
                for province in reader:
                    world.add_data(date, "confirmed", province["Confirmed"])
                    world.add_data(date, "deaths", province["Deaths"])
                    world.add_data(date, "recovered", province["Recovered"])
                    try:
                        country_region = province["Country/Region"]
                    except KeyError:
                        country_region = province["Country_Region"]
                    try:
                        country = self.get(country_region)
                    except KeyError:
                        if country_region not in skipped_country_regions:
                            skipped_country_regions.add(country_region)
                            logger.verbose(f"No population for {country_region}")
                        continue
                    country.add_data(date, "confirmed", province["Confirmed"])
                    country.add_data(date, "deaths", province["Deaths"])
                    country.add_data(date, "recovered", province["Recovered"])
        self.all_dates = sorted(all_dates)

    def _load_population(self):
        logger.verbose('Loading population')
        with open("population.txt") as f:
            next(f)
            for line in f:
                country, _, count = line.strip().partition("\t")
                if not count:
                    continue
                self._population[country] = int(count)


def convert_date(date_str):
    month, day, year = date_str.split("-")
    date = datetime.date(int(year), int(month), int(day))
    return date


def write_highcharts(name, calculate_ratio, calc_fn):
    highcharts_series = []
    for country in COUNTRIES.filtered_country_list():
        serie = {"name": country.name, "data": []}
        if country.name == "World":
            serie["yAxis"] = 1
            serie["dashStyle"] = "ShortDot"
        for date in COUNTRIES.all_dates:
            value = calc_fn(country, date)
            if calculate_ratio:
                value = value / country.population * 1_000_000
            serie["data"].append(value)
        highcharts_series.append(serie)
    if calculate_ratio:
        report_name = f"{name} ratio"
    else:
        report_name = f"{name} abs"
    write_report(report_name, COUNTRIES.all_dates, highcharts_series)


def write_country(report_name, calc_fn):
    dates = COUNTRIES.all_dates
    country_name = "Hungary"
    country = COUNTRIES.get(country_name)
    serie = {"name": country.name, "data": []}
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
    (OUT_DIR / f"{name} report.html").write_text(html_text)


########################################################################################

logger.info("Create stats for COVID-19")
OUT_DIR.mkdir(exist_ok=True)
COUNTRIES = Countries()
COUNTRIES.load_data()

logger.verbose("Write countries")
write_highcharts("deaths", False, lambda country, date: country.get_data(date).deaths)
write_highcharts("deaths", True, lambda country, date: country.get_data(date).deaths)
write_highcharts(
    "confirmed diff", True, lambda country, date: country.get_diff(date).confirmed
)
write_highcharts(
    "deaths diff", True, lambda country, date: country.get_diff(date).deaths
)

logger.verbose("Write Hungary")
write_country("active", lambda country, date: country.get_data(date).active)
write_country("confirmed diff", lambda country, date: country.get_diff(date).confirmed)
write_country("deaths diff", lambda country, date: country.get_diff(date).deaths)
