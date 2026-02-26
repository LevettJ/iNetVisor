import argparse
import ujson

class Trace2Adj(object):
    """
    Create AS adjacencies from traceroute file.
    """

    def __init__(self, file):
        """
        Traceroute to Adjacency tool.

        Args:
            file (str): path to traceroute data.
        """
        self.adjacencies = set()
        traceroutes = self.load_traceroute(file)
        self._process_adjacencies(traceroutes)

    def load_traceroute(self, file):
        """
        Load traceroute data from file.

        Args:
            file (str): path to file containing traceroutes.

        Returns:
            dict: Python dict of JSON data
        """
        with open(file, encoding="utf-8") as f:
            traceroutes = ujson.load(f)
        return traceroutes

    def _process_adjacencies(self, traceroutes):
        """
        Parse traceroutes to determine AS adjacencies.

        Args:
            traceroutes (dict): JSON format traceroutes.
        """
        for traceroute in traceroutes:
            # Calculate number of routes/indexes
            if 'rt' not in traceroute:
                continue # Some data does not have routes
            if len(traceroute['rt']) == 0:
                continue # Some routes have no data
            routes = len(traceroute['rt'][0]['packets'])
            for i in range(routes): # For each path in the traceroute
                previous = None
                for route in traceroute['rt']: # For each hop in the path
                    #DEBUG: print("i is", i, "| Len is", routes, "| Pack:", route['packets'])
                    if i > len(route['packets'])-1:
                        break # Timeout occured for some routes, data inconsistent
                    if 'asn' in route['packets'][i]:
                        current = route['packets'][i]['asn']
                        if previous is not None and current != previous:
                            # Only recognise adjacencies that are directly observed
                            self.adjacencies.add(tuple(sorted([current, previous])))
                        previous = current
                    else:
                        # Ignore where an ASN is unresolved or ICMP times out
                        previous = None

    def export(self, output_file):
        """
        Write unique adjacencies to a file.

        Args:
            output_file (str): path to output file.
        """
        adjacency_list = list(self.adjacencies)
        with open(output_file, 'w', encoding='utf-8') as f:
            for adjacency in adjacency_list:
                f.write(str(adjacency[0]) + ',' + str(adjacency[1]) + '\n')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Collect RIPE Atlas traceroute data')
    parser.add_argument('-in', '--input',
                        help='Input traceroute JSON file',
                        required=True)
    parser.add_argument('-o', '--output',
                        help='Destination adjacencies file',
                        required=True)
    args = parser.parse_args()

    trace = Trace2Adj(args.input)
    trace.export(args.output)