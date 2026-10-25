import datetime
from abc import ABC, abstractmethod
from collections import defaultdict
from enum import StrEnum
from typing import Mapping, Sequence

from green_button import IntervalBlock

class Season(StrEnum):
    SUMMER = "SUMMER"
    WINTER = "WINTER"

class TOUPeriod(StrEnum):
    ON_PEAK        = "ON_PEAK"
    MID_PEAK       = "MID_PEAK"
    OFF_PEAK       = "OFF_PEAK"
    SUPER_OFF_PEAK = "SUPER_OFF_PEAK"

class DayType(StrEnum):
    WEEKDAY         = "WEEKDAY"
    WEEKEND_HOLIDAY = "WEEKEND_HOLIDAY"

class DiscountProgram(StrEnum):
    CARE = "CARE"
    FERA = "FERA"

ENUM_VALIDATORS = {
    'Season'          : Season,
    'TOUPeriod'       : TOUPeriod,
    'DayType'         : DayType,
    'DiscountProgram' : DiscountProgram
}

class ResidentialPlan(ABC):
    def __init__(self,
                 tariffs: dict,
                 plan: str,
                 medical_baseline_units = 0,
                 discount_program: str = "",
                 **kwargs):
        super().__init__(**kwargs)
        self.tariffs = tariffs
        self.plan = tariffs[plan]
        self.medical_baseline_units = medical_baseline_units
        self.discount_program = DiscountProgram(discount_program) \
            if discount_program else None

        self.rates_table = self.parse_table(self.plan['rates_table'])

    def get_row(self, name: str, season=None, tou_period=None):
        rows = [r for r in self.rates_table if r['name'] == name]
        if season is not None:
            rows = [r for r in rows if r['Season'] == season]
        if tou_period is not None:
            rows = [r for r in rows if r['TOUPeriod'] == tou_period]
        if len(rows) != 1:
            raise KeyError(f"Number of rows != 1: {rows}")
        result = rows[0]
        return result

    def get_base_services_charge_rate(self):
        row = self.get_row('base_services_charge')
        rate = row['Total']
        if self.discount_program == DiscountProgram.CARE:
            rate -= 0.209 # CARE surcharge
            rate -= 0.069 # Base Services Charge Surcharge
            rate *= (1 + self.tariffs['CARE_discount'])
            rate -= 0.168 # Base Services Charge Discount
        return rate

    @abstractmethod
    def calculate_bill(self,
                       billing_period: Sequence[IntervalBlock]) -> float:
        pass

    @staticmethod
    def parse_table(raw_table):
        raw_header = raw_table['header']
        raw_rows = raw_table['rows']

        validated_table = []
        mapped_table = [dict(zip(raw_header, row)) for row in raw_rows]
        for row in mapped_table:
            validated_row = {}
            for k, v in row.items():
                if v is None: continue
                elif k in ENUM_VALIDATORS:
                    validated_row[k] = ENUM_VALIDATORS[k](v)
                else:
                    validated_row[k] = v
            validated_table.append(validated_row)
        return validated_table

    @staticmethod
    def get_season(date: datetime.date):
        if 6 <= date.month <= 9:
            return Season.SUMMER
        return Season.WINTER

class ScheduleTOUDPlan(ResidentialPlan):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tou_periods = self.parse_table(self.plan['tou_periods'])
        for row in self.tou_periods:
            for k in ('start', 'end'):
                if row[k] == 24: row[k] = datetime.time.max
                else:            row[k] = datetime.time(row[k])

    def get_tou_periods(self, date: datetime.date):
        day_type = self.get_day_type(date)
        season = self.get_season(date)
        results = [row for row in self.tou_periods
                   if row['DayType'] == day_type and row['Season'] == season]
        return results

    __holidays : dict[int, list[datetime.date]] = defaultdict()
    @classmethod
    def holidays(cls, year: int) -> list[datetime.date]:
        if year in cls.__holidays: return cls.__holidays[year]

        one_day = datetime.timedelta(days=1)
        holidays: list[datetime.date] = [
            datetime.date(year, 1, 1),   # New Year's Day
            datetime.date(year, 7, 4),   # Independence Day
            datetime.date(year, 11, 11), # Veteran's Day
            datetime.date(year, 12, 25)  # Christmas Day
            ]

        # President's Day - 3rd Monday in Feb
        first_monday = datetime.date(year, 2, 1)
        while first_monday.weekday() != 0: first_monday += one_day
        holidays.append(first_monday + datetime.timedelta(days=14))

        # Memorial Day - last Monday in May
        memorial_day = datetime.date(year, 5, 31)
        while memorial_day.weekday() != 0: memorial_day -= one_day
        holidays.append(memorial_day)

        # Labor Day - 1st Monday in Sep
        first_monday = datetime.date(year, 9, 1)
        while first_monday.weekday() != 0: first_monday += one_day
        holidays.append(first_monday)

        # Thanksgiving Day - 4th Thursday in Nov
        first_thursday = datetime.date(year, 11, 1)
        while first_thursday.weekday() != 3: first_thursday += one_day
        holidays.append(first_thursday + datetime.timedelta(days=21))

        # Move Sunday holidays to Monday
        holidays = [d + one_day if d.weekday() == 6 else d for d in holidays]

        cls.__holidays[year] = holidays
        return holidays

    @classmethod
    def get_day_type(cls, date: datetime.date):
        if date.weekday() in (5, 6) or date in cls.holidays(date.year):
            return DayType.WEEKEND_HOLIDAY
        return DayType.WEEKDAY


                
class TOUDStandardPlan(ScheduleTOUDPlan):
    def __init__(self, region: int, **kwargs):
        super().__init__(**kwargs)
        self.region = region
        self.allocations = self.parse_table(self.plan['allocations'])

    def get_allocation(self, date, alloc_type='baseline_basic') -> float:
        season = self.get_season(date)
        alloc = None
        for row in self.allocations:
            if row['Season'] == season and row['region'] == self.region:
                alloc = row[alloc_type]
        if alloc is None:
            raise KeyError(f"Unable to find allocation for DATE={date}, "
                           f"SEASON={season}, ALLOC_TYPE={alloc_type}")
        alloc += self.medical_baseline_units * \
            self.tariffs['MEDICAL_BASELINE_ALLOCATION']
        return alloc

    def get_baseline_credit_rate(self, date):
        row = self.get_row('baseline_credit')
        rate = row['Total']
        return rate

    def get_energy_charge_delivery_rate(self, season, tou_period):
        energy_charge_delivery_row = self.get_row(
            'energy_charge_delivery', season, tou_period)
        rate = energy_charge_delivery_row['Total']
        if self.discount_program == DiscountProgram.CARE:
            rate -= energy_charge_delivery_row['WFC'] # Wildfire Fund Non-Bypassable Charge
        else:
            rate += self.get_row('fixed_recovery_charge')['Total']
            rate += self.get_row('MCAM_charge')['Total']
        return rate

    def calculate_bill(self, billing_period: Sequence[IntervalBlock]
                       ) -> float:
        base_services_charge: Mapping[float, int] = defaultdict(lambda: 0)
        baseline_credit: Mapping[
            float, list[float]] = defaultdict(lambda: [0.0, 0.0])
        energy_charge_delivery: Mapping[
            tuple[Season, TOUPeriod, float], float
            ] = defaultdict(lambda: 0.0)
        
        for block in billing_period:
            date = block.start
            # Base Services Charge
            bsc_rate = self.get_base_services_charge_rate()
            base_services_charge[bsc_rate] += 1
            # Baseline Credit
            bc_rate = self.get_baseline_credit_rate(date)
            baseline_credit[bc_rate][0] += block.delivered_kwh()
            baseline_credit[bc_rate][1] += self.get_allocation(date)
            # Energy Charge Delivery
            for row in self.get_tou_periods(date):
                (season, tou_period, start, end) = (row['Season'], row['TOUPeriod'], row['start'], row['end'])
                rate = self.get_energy_charge_delivery_rate(season, tou_period)
                energy_charge_delivery[(season, tou_period, rate)] += block.delivered_kwh(start, end)

        total_base_services_charge = 0.0
        for rate, num_days in base_services_charge.items():
            total_base_services_charge += rate * num_days
        total_baseline_credit = 0.0
        for rate, (usage, alloc) in baseline_credit.items():
            total_baseline_credit += rate * min(usage, alloc)
        total_energy_charge_delivery: Mapping[
            tuple[Season, TOUPeriod],
            list[float]] = defaultdict(lambda: [0, 0])
        for (season, tou_period, rate), kwh in energy_charge_delivery.items():
            total_energy_charge_delivery[(season, tou_period)][0] += kwh
            total_energy_charge_delivery[(season, tou_period)][1] += rate * kwh
        total = sum([total_base_services_charge,
                     total_baseline_credit,
                     sum([v[1] for v in total_energy_charge_delivery.values()])
                     ])            
        return total