import argparse
import datetime
import pprint
import yaml

from green_button import GreenButtonData
from tariff_engine import TOUDStandardPlan

arg_parser = argparse.ArgumentParser()
arg_parser.add_argument('--tariff_yaml', default='config/tariff.yaml')
arg_parser.add_argument('--plan', default='TOU_D_4_9PM')
arg_parser.add_argument('--medical_baseline_units', type=int, default=0)
arg_parser.add_argument('--discount_program')
arg_parser.add_argument('--region', type=int, required=True)
arg_parser.add_argument('green_button_file')
arg_parser.add_argument('--skiplines', type=int, default=0)
arg_parser.add_argument('--start')
arg_parser.add_argument('--end')
args = arg_parser.parse_args()

def main():
    tariff_yaml = yaml.safe_load(open(args.tariff_yaml, 'r'))
    billing_engine = TOUDStandardPlan(
        tariffs=tariff_yaml,
        plan=args.plan,
        medical_baseline_units=args.medical_baseline_units,
        discount_program=args.discount_program,
        region=args.region)

    green_button_data = GreenButtonData.from_csv(
        args.green_button_file, skiplines=args.skiplines)
    start = datetime.datetime.strptime(args.start, "%m/%d/%y")
    end = datetime.datetime.strptime(args.end, "%m/%d/%y")

    total = billing_engine.calculate_bill(
        green_button_data.get_interval_blocks(start.date(), end.date()))
    print(f"TOTAL={total:.2f}")

if __name__ == '__main__':
    main()
