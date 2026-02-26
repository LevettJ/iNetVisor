"""
Convert our BGP paths to AS-Rank format.
@author Joshua Levett
"""

import argparse

class FormatToASRank(object):
    """
    Convert data to a format supported by AS-Rank.
    """
    def __init__(self):
        """
        Convert data to a format supported by AS-Rank.
        """
        self.paths = set()
    
    def parse_paths(self, paths):
        """
        Parse paths and extract adjacencies.

        Args:
            paths (list): list of lines in exported cleaned paths file.
        """
        for record in paths:
            path = record.strip().split('/')[0]
            self.paths.add(path)
    
    def export(self, output_file):
        """
        Write unique adjacencies to a file.

        Args:
            output_file (str): path to output file.
        """
        paths_list = list(self.paths)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(paths_list))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Export unique adjacent ASes in the path.')
    parser.add_argument('-in', '--input',
                        help='File containing a list of files with paths',
                        required=True)
    parser.add_argument('-o', '--output',
                        help='File to save asrank format to',
                        required=True)
    args = parser.parse_args()

    with open(args.input, 'r', encoding='utf-8') as f:
        list_of_files = f.readlines()
    asrank_format = FormatToASRank()
    for file in list_of_files:
        with open(file.rstrip(), 'r', encoding='utf-8') as f:
            paths = f.readlines()
            asrank_format.parse_paths(paths)
    asrank_format.export(args.output)
