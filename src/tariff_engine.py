import datetime
from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Sequence

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

ENUM_VALIDATORS = {
    'Season'    : Season,
    'TOUPeriod' : TOUPeriod,
    'DayType'   : DayType
}

class ResidentialPlan(ABC):
    def __init__(self, tariffs: dict, plan: str, **kwargs):
        super().__init__(**kwargs)
        self.tariffs = tariffs
        self.plan = tariffs[plan]
        self.rates_table = self.parse_table(self.plan['rates_table'])

    @abstractmethod
    def calculate_bill(self, billing_period: Sequence[IntervalBlock]) -> float:
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


class ScheduleTOUDPlan(ResidentialPlan):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tou_periods = self.parse_table(self.plan['tou_periods'])
        for row in self.tou_periods:
            for k in ('start', 'end'):
                if row[k] == 24: row[k] = datetime.time.max
                else:            row[k] = datetime.time(row[k])
                
class TOUDStandardPlan(ScheduleTOUDPlan):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.allocations = self.parse_table(self.plan['allocations'])

    def calculate_bill(self, billing_period: Sequence[IntervalBlock]) -> float:
        return 0.0