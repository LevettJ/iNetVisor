"""
Get a list of paths from a list of MRT files
@author Joshua Levett
"""

import argparse
import bgpkit

def get_paths(list_of_mrt, output):
    """_summary_

    Args:
        list_of_mrt (list): list of mrt urls
        output (str): destination to write paths
    """
    out = open(output, 'w', encoding='utf-8')

    for collector in list_of_mrt:
        parser = bgpkit.Parser(url=collector.strip()).parse_all()
        
        # Handle empty MRTs
        if len(parser) == 0:
            print("No data found in", collector)
            continue
        
        # Iterate through BGP records
        for elem in parser:

            # Ignore BGP withdrawals (relevant for BGP updates)
            # These contain no as_path fields, only withdrawn prefixes
            if elem['elem_type'] == 'W':
                continue

            path = elem['as_path']

            # Ignore aggregated paths
            if '{' in path or '(' in path:
                continue

            # Determine whether route is IPv4/v6
            if ':' in elem['prefix']:
                ipver = 'v6'
            else:
                ipver = 'v4'

            # Write to output file, metadata (IPv4/v6 + timestamp) separated with '/'
            out.write(path.replace(' ', '|') + '/' + ipver + '|' + str(elem['timestamp']) + '\n')
        
        # Write contents of MRT to file, clear unneeded memory
        out.flush()
        del parser
        
    out.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Get MRT files from specified locations and export as_paths')
    parser.add_argument('-in', '--input',
                        help='List of MRTs files',
                        required=True)
    parser.add_argument('-o', '--output',
                        help='File to save output',
                        required=True)
    args = parser.parse_args()

    with open(args.input, 'r', encoding='utf-8') as f:
        list_of_mrt = f.readlines()
        get_paths(list_of_mrt, args.output)
