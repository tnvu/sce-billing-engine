import argparse
import datetime
import pprint
import yaml

from green_button import GreenButtonData
from tariff_engine import TOUDStandardPlan

arg_parser = argparse.ArgumentParser()
arg_parser.add_argument('green_button_file')
arg_parser.add_argument('start')
arg_parser.add_argument('end')
arg_parser.add_argument('--skiplines', type=int, default=0)
arg_parser.add_argument('--tariff_yaml', type=str, default='config/tariff.yaml')
args = arg_parser.parse_args()

def main():
    tariff_yaml = yaml.safe_load(open(args.tariff_yaml, 'r'))
    billing_engine = TOUDStandardPlan(tariffs=tariff_yaml, plan="TOU_D_5_8PM", medical_baseline_units=1, discount_program="CARE")
    green_button_data = GreenButtonData.from_csv(
        args.green_button_file, skiplines=args.skiplines)
    start = datetime.datetime.strptime(args.start, "%m/%d/%y")
    end = datetime.datetime.strptime(args.end, "%m/%d/%y")

    total = billing_engine.calculate_bill(
        green_button_data.get_interval_blocks(start.date(), end.date()))
    print(f"TOTAL={total:.2f}")

if __name__ == '__main__':
    main()
