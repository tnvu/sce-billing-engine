import csv
import datetime
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Sequence

@dataclass(frozen=True)
class IntervalReading:
    start: datetime.time
    duration: datetime.timedelta
    delivered_kwh: float
    received_kwh: float


@dataclass(frozen=True)
class IntervalBlock:
    start: datetime.date
    duration: datetime.timedelta
    readings: Sequence[IntervalReading]

    def delivered_kwh(self, start=datetime.time.min, end=datetime.time.max) -> float:
        kwh = 0.0
        for reading in self.readings:
            if start <= reading.start < end:
                kwh += reading.delivered_kwh
        return kwh

    def received_kwh(self, start=datetime.time.min, end=datetime.time.max) -> float:
        kwh = 0.0
        for reading in self.readings:
            if start <= reading.start < end:
                kwh += reading.received_kwh
        return kwh


@dataclass(frozen=True)
class GreenButtonData:
    interval_blocks: dict[datetime.date, IntervalBlock] = \
        field(default_factory=dict)

    def get_interval_blocks(self,
                            start: datetime.date = datetime.date.min,
                            end: datetime.date =datetime.date.max
                            ) -> Sequence[IntervalBlock]:
        results = []
        date = start
        while date <= end:
            results.append(self.interval_blocks[date])
            date += datetime.timedelta(days=1)
        return results

    @staticmethod
    def from_csv(filename, skiplines=0) -> "GreenButtonData":
        f = open(filename, 'r', encoding='utf-8')
        for _ in range(skiplines):
            next(f)

        accumaltor = defaultdict(list)
        csv_reader = csv.reader(f)
        for row in csv_reader:
            row = [x.strip() for x in row]
            if not any(row): continue
            date = datetime.datetime.strptime(row[0], "%m/%d/%Y").date()
            start = datetime.datetime.strptime(row[1], "%m/%d/%Y %I:%M%p")
            end = datetime.datetime.strptime(row[2], "%m/%d/%Y %I:%M%p")
            delivered_kwh = float(row[3])
            received_kwh = float(row[4])
            duration = end - start
            reading = IntervalReading(
                start.time(), end - start, delivered_kwh, received_kwh)
            accumaltor[date].append(reading)

        final_blocks: dict[datetime.date, IntervalBlock] = defaultdict()
        for date, readings in accumaltor.items():
            sorted_readings = sorted(readings, key=lambda x: x.start)
            end = datetime.datetime.combine(datetime.date.min, sorted_readings[-1].start)
            end += sorted_readings[-1].duration
            start = datetime.datetime.combine(datetime.date.min, sorted_readings[0].start)
            duration = end - start
            final_blocks[date] = IntervalBlock(date, duration, sorted_readings)
        return GreenButtonData(final_blocks)