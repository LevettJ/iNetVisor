import requests
import argparse
import datetime
import ujson
import time
from ipaddress import ip_address
import pyasn

class Collect(object):

    ATLAS_BASE = 'https://atlas.ripe.net'
    STAT_BASE = 'https://stat.ripe.net'

    def __init__(self, asndb_file=None):
        self.traceroutes = []
        self._export = []
        self._mappings = {}
        self._asndb = None
        if asndb_file is not None:
            self._asndb = pyasn.pyasn(asndb_file)

    def get_traceroute_measurements(self, input_data):
        """
        Get traceroute measurements from the specified timeframe.

        Args:
            input_data (str): path to Atlas Daily Dump data file
        """
        with open(input_data, 'r', encoding='utf8') as f:
            raw_data = f.read().splitlines()

        for data in raw_data:
            data = ujson.loads(data)
            self.traceroutes.append(data)
        
    def _extract_paths(self, mapped=False):
        """
        Extract paths in export format.
        """
        for traceroute in self.traceroutes:
            # Skip incomplete data
            if 'src_addr' not in traceroute:
                continue
            if 'dst_addr' not in traceroute:
                continue
            if 'timestamp' not in traceroute:
                continue

            path = {
                'pid': traceroute['prb_id'],
                'src': traceroute['src_addr'],
                'dst': traceroute['dst_addr'],
                'ts': traceroute['timestamp'],
                'rt': []
            }

            if 'result' not in traceroute:
                continue # No hop data in traceroute
            for hop in traceroute['result']:
                hid = hop['hop']
                packets = []
                if 'result' not in hop:
                    continue
                for packet in hop['result']:
                    fpacket = {
                        'ip': None,
                        'ttl': None,
                        'rtt': None
                    }            
                    if 'from' in packet:
                        fpacket['ip'] = packet['from']
                        fpacket['ttl'] = packet['ttl']
                        if 'rtt' in packet:
                            fpacket['rtt'] = packet['rtt']
                        if mapped:
                            if self.get_asn(packet['from']) is not None:
                                fpacket['asn'] = self.get_asn(packet['from'])

                    packets.append(fpacket)

                path['rt'].append({
                    'hop': hid,
                    'packets': packets
                })
            self._export.append(path)
    
    def get_asn(self, ipaddr):
        """
        Returns ASN of IP address.

        Args:
            ipaddr (str): IP address in string format

        Returns:
            int: ASN (or None)
        """
        if ip_address(ipaddr) in self._mappings:
            return self._mappings[ip_address(ipaddr)]
        else:
            return self._asndb.lookup(str(ipaddr))[0]

    def load_router2as_mappings(self, router2as):
        """
        Load router2as mappings from file.

        Args:
            router2as (str): Path to router2as JSON file
        """
        with open(router2as, encoding="utf-8") as f:
            mappings = ujson.load(f)

        for mapping in mappings:
            self._mappings[ip_address(mapping)] = mappings[mapping]

    def _get_asn_from_ripestat(self, ipaddr):
        """
        Returns and stores IP address to ASN mapping from RIPEstat.

        Args:
            ipaddr (ip_address): Router IP address

        Returns:
            int: ASN
        """
        headers = {'content-type': 'application/json'}
        params = {
            'resource': str(ipaddr),
            }
        url = self.STAT_BASE + '/data/network-info/data.json'

        try:
            raw_data = requests.get(url, headers=headers, params=params, timeout=10).content
            data = ujson.loads(raw_data)['data']
        except:
            time.sleep(10)
            try:
                raw_data = requests.get(url, headers=headers, params=params, timeout=10).content
                data = ujson.loads(raw_data)['data']
            except:
                return None

        try:
            self._mappings[ip_address(ipaddr)] = int(data['asns'][0])
            return int(data['asns'][0])
        except:
            return None

    def export(self, output, mapped=False):
        """
        Export path data to JSON file.

        Args:
            output (str): destination .json file
        """

        self._extract_paths(mapped)
        with open(output, 'w', encoding='utf-8') as f:
            f.write(ujson.dumps(self._export))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Convert daily dump data to required format.')
    parser.add_argument('-in', '--input',
                        help='Input daily dump file',
                        required=True)
    parser.add_argument('-o', '--output',
                        help='Destination .json file',
                        required=True)
    parser.add_argument('-r2as', '--router2as',
                        help='Router IP to ASN mapping',
                        required=False)
    parser.add_argument('-asndb', '--pyasndb',
                        help='pyasn ASNDB file',
                        required=False)
    args = parser.parse_args()

    traceObject = Collect(args.pyasndb)
    MAPPED = False
    if args.router2as is not None:
        traceObject.load_router2as_mappings(args.router2as)
        MAPPED = True
    traceObject.get_traceroute_measurements(args.input)
    traceObject.export(args.output, mapped=MAPPED)
