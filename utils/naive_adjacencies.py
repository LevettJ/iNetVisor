"""
Extract 'naive' adjacencies from BGP paths.
@author Joshua Levett
"""
import argparse
import csv

class NaiveAdjacency(object):
    """
    Naive adjacency processor
    """
    def __init__(self):
        """
        Naive adjacency processor
        """
        self.adjacencies = set()
    
    def parse_paths(self, paths):
        """
        Parse paths and extract adjacencies.

        Args:
            paths (list): list of lines in exported cleaned paths file.
        """
        for record in paths:
            path = record.strip().split('/')[0]
            path = path.split('|')
            self._parse_adjacencies(path)

    def _parse_adjacencies(self, path):
        """
        Iterate through path and add adjacent ASes to the set.

        Args:
            path (list): pre-cleaned as_path list.
        """
        for i in range(0, len(path)-1):
            self.adjacencies.add(tuple(sorted([path[i], path[i+1]])))
    
    def export(self, output_file):
        """
        Write unique adjacencies to a file.

        Args:
            output_file (str): path to output file.
        """
        adjacency_list = list(self.adjacencies)
        with open(output_file, 'w', encoding='utf-8') as f:
            for adjacency in adjacency_list:
                f.write(str(adjacency[0] + ',' + adjacency[1] + '\n'))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Export unique adjacent ASes in the path.')
    parser.add_argument('-in', '--input',
                        help='File containing a list of files with paths',
                        required=True)
    parser.add_argument('-o', '--output',
                        help='File to save adjacencies',
                        required=True)
    args = parser.parse_args()

    with open(args.input, 'r', encoding='utf-8') as f:
        list_of_files = f.readlines()
    naive_adjacency = NaiveAdjacency()
    for file in list_of_files:
        with open(file.rstrip(), 'r', encoding='utf-8') as f:
            paths = f.readlines()
            naive_adjacency.parse_paths(paths)
    naive_adjacency.export(args.output)
