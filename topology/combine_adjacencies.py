import argparse

# Merge adjacency files
def merge_adjacency_files(list_of_files, output_file):
    """
    Merge files containing AS adjacencies.

    Args:
        list_of_files (list): List of files in current folder, or relative paths.
        output_file (str): Destination file for combined adjacency list.
    """
    adjacencies = set()

    for file in list_of_files:
        with open(file, 'r') as f:
            data = f.readlines()
            print(data[0].strip())

            for line in data:
                line = line.strip().split(',')
                adjacencies.add(tuple(sorted([int(x) for x in line])))

    with open(output_file, 'w') as f:
        for adj in adjacencies:
            f.write(','.join(list([str(x) for x in adj])) + '\n')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Combine adjacency text files.')
    parser.add_argument('-f', '--files',
                        help='Adjacencies .txt file(s)',
                        nargs='*',
                        required=True)
    parser.add_argument('-o', '--output',
                        help='Output file',
                        required=True)
    args = parser.parse_args()

    merge_adjacency_files(args.files, args.output)