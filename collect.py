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
    def __init__(self, country, date):
        self.country = country
        self.date = date
        self.confirmed = 0
        self.deaths = 0
        self.recovered = 0

    @property
    def active(self):
        return self.confirmed - self.deaths - self.recovered

    def __str__(self):
        return f"{str(self.country)} {self.date:%Y-%m-%d} {self.confirmed}/{self.deaths}/{self.recovered}"
    
    def __repr__(self):
        return f"DailyData({self})"

    @property
    def mortality(self):
        if not self.confirmed:
            return 0
        return self.deaths / self.confirmed


class Country:
    def __init__(self, name, population):
        self.name = name
        self.data = {}
        self.population = population

    def add_data(self, date, type, value):
        if date not in self.data:
            self.data[date] = DailyData(self, date)
        if value:
            value = int(float(value))
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
        return DailyData(self, date)

    def get_diff(self, date):
        actual = self.get_data(date)
        previous = self.get_data(date - datetime.timedelta(days=7))
        diff_data = DailyData(self, date)
        diff_data.confirmed = actual.confirmed - previous.confirmed
        diff_data.deaths = actual.deaths - previous.deaths
        diff_data.recovered = actual.recovered - previous.recovered
        return diff_data

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"Country({self})"

    @property
    def _last_daily_data(self):
        return max(self.data.values(), key=lambda dd: dd.date)

    @property
    def deaths(self):
        return self._last_daily_data.deaths

    @property
    def last_week_deaths(self):
        try:
            last_date = self._last_daily_data.date
            one_week_deaths = self.data[last_date - datetime.timedelta(days=7)].deaths
        except KeyError:
            one_week_deaths = 0
        return self.deaths - one_week_deaths


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
            name = "Czech Republic"
        if name == "United Kingdom":
            name = "UK"
        if name == "Russian Federation":
            name = "Russia"
        if name == "Viet Nam":
            name = "Vietnam"
        if name not in self._countries:
            self._countries[name] = Country(name, self._population[name])
        return self._countries[name]

    def filtered_country_list(self):
        country_list = []
        for country in self._countries.values():
            if country.population < 9_000_000:
                continue
            if country.last_week_deaths < 400 and country.deaths < 10_000:
                continue
            logger.debug(
                f"Country check: {country.name:20} {country.population:12d} "
                f"{country.deaths:8d} {country.last_week_deaths:7d}"
            )
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
        logger.verbose("Loading population")
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
    countries = COUNTRIES.filtered_country_list()
    _write_report(countries, f"Global {name}", calculate_ratio, calc_fn)


def write_central_eu(name, calculate_ratio, calc_fn):
    selected_countries = (
        "Hungary",
        "Austria",
        "Bosnia and Herzegovina",
        "Croatia",
        "Czech Republic",
        "Romania",
        "Serbia",
        "Slovakia",
        "Slovenia",
        "Ukraine",
    )
    countries = [COUNTRIES.get(name) for name in selected_countries]
    _write_report(countries, f"Central EU {name}", calculate_ratio, calc_fn)


def write_country(country_name, report_name, calc_fn):
    countries = [COUNTRIES.get(country_name)]
    _write_report(countries, f"{country_name} {report_name}", False, calc_fn)


def _write_report(countries, name, calculate_ratio, calc_fn):
    highcharts_series = []
    for country in countries:
        serie = {"name": country.name, "data": []}
        if country.name == "World":
            serie["yAxis"] = 1
            serie["dashStyle"] = "ShortDot"
        previous_value = 0
        for date in COUNTRIES.all_dates:
            value = calc_fn(country, date)
            if calculate_ratio:
                value = value / country.population * 1_000_000
                value = min(16000, value)  # Exceptionally high values

            change_ratio = 0.4
            value = (
                change_ratio * value
                + (1 - change_ratio) * previous_value
            )
            serie["data"].append(value)
            previous_value = value
        highcharts_series.append(serie)
    if calculate_ratio:
        report_name = f"{name} ratio"
    elif "percent" in name:
        report_name = name
    else:
        report_name = f"{name} abs"
    dates = COUNTRIES.all_dates
    template_text = pathlib.Path("template.html").read_text()
    html_text = template_text.replace(
        "[/*xAxis*/]", json.dumps([date.strftime("%m.%d.") for date in dates])
    )
    html_text = html_text.replace("[/*series*/]", json.dumps(highcharts_series))
    html_text = html_text.replace("{TITLE}", report_name)
    (OUT_DIR / f"{report_name} report.html").write_text(html_text)


########################################################################################

logger.info("Create stats for COVID-19")
OUT_DIR.mkdir(exist_ok=True)
COUNTRIES = Countries()
COUNTRIES.load_data()

logger.verbose("Write global")
write_highcharts("deaths", False, lambda country, date: country.get_data(date).deaths)
write_highcharts("deaths", True, lambda country, date: country.get_data(date).deaths)
write_highcharts(
    "confirmed percent", False, lambda country, date: country.get_data(date).confirmed / country.population * 100
)
write_highcharts(
    "confirmed diff", True, lambda country, date: country.get_diff(date).confirmed
)
write_highcharts(
    "deaths diff", True, lambda country, date: country.get_diff(date).deaths
)

logger.verbose("Write World")
write_country(
    "World", "mortality", lambda country, date: country.get_data(date).mortality * 100
)
write_country(
    "World", "mortality diff", lambda country, date: country.get_diff(date).mortality * 100
)

logger.verbose("Write Central EU")
write_central_eu("deaths", False, lambda country, date: country.get_data(date).deaths)
write_central_eu("deaths", True, lambda country, date: country.get_data(date).deaths)
write_central_eu(
    "confirmed", False, lambda country, date: country.get_data(date).confirmed
)
write_central_eu(
    "confirmed percent", False, lambda country, date: country.get_data(date).confirmed / country.population * 100
)
write_central_eu(
    "confirmed diff", True, lambda country, date: country.get_diff(date).confirmed
)
write_central_eu(
    "deaths diff", True, lambda country, date: country.get_diff(date).deaths
)

