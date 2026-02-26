"""
Obtain BGP route collector sources.
@author Joshua Levett
"""

import argparse
import datetime
import json
import bgpkit

def get_collectors(start, duration, output=False):
    """
    Get a list of public route collectors for the specified timeframe.

    Args:
        start (str): starting date (dd/mm/yyyy HH:MM:SS).
        duration (int): duration in seconds.
        output (bool, optional): destination filepath. Defaults to printing to terminal.
    """

    # Convert start and duration to UNIX time
    ts_start = int(datetime.datetime.strptime(start, '%d/%m/%Y %H:%M:%S').strftime('%s'))
    ts_end = ts_start + int(duration)

    # Initialise and query broker
    broker = bgpkit.Broker()
    collectors = broker.query(ts_start=ts_start, ts_end=ts_end)

    results = []

    # GET DATA FROM EACH COLLECTOR
    for collector in collectors:

        results.append({
            "id": collector.collector_id,
            "ts_start": collector.ts_start,
            "ts_end": collector.ts_end,
            "type": collector.data_type,
            "url": collector.url
        })

    if output:
        with open(output, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=4)

    else:
        print(output)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Get a list of route collectors.')
    parser.add_argument('-s', '--start',
                        help='Starting timestamp',
                        required=True)
    parser.add_argument('-d', '--duration',
                        help='Duration of collection period (seconds)',
                        required=True)
    parser.add_argument('-o', '--output',
                        help='File to save output',
                        required=False)
    args = parser.parse_args()

    get_collectors(args.start, args.duration, args.output)
