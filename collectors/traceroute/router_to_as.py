import argparse
import sqlite3
from ipaddress import ip_address
import ujson

class Router2AS(object):
    """
    Import IXP IP address files and map router IP addresses to ASNs
    """
    def __init__(self):
        self._ipdb = {}

    def _add_record(self, ipaddr, asn):
        try: # Ignore blank string or incomplete IP address
            self._ipdb[ip_address(ipaddr)] = asn
        except ValueError:
            pass
            # For debugging only:
            # if ipaddr not in (None, ""):
            #     print("IP address detected invalid for:", ipaddr)

    def load_from_ixpdb(self, ixpdb):
        """
        Load IXPDB file and record IP address to ASN mappings.

        Args:
            ixpdb (str): path to IXPDB JSON data.
        """
        with open(ixpdb, encoding="utf8") as f:
            data = ujson.load(f)

        # Put data in local storage
        for asn in data:
            for address in asn['ip_addresses']:
                self._add_record(address, asn['asn'])

    def load_from_peeringdb(self, peeringdb):
        """
        Load PeeringDB file to map IP addresses at IXPs to ASNs.

        Args:
            peeringdb (str): path to PeeringDB JSON/SQLite data.
        """
        if peeringdb.endswith('json'):
            with open(peeringdb) as f:
                data = ujson.load(f)

            # print(data['netixlan']['data'][100]['asn'])
            # print(data['netixlan']['data'][100]['ipaddr4'])
            # print(data['netixlan']['data'][100]['ipaddr6'])

            for network in data['netixlan']['data']:
                self._add_record(network['ipaddr4'], network['asn'])
                self._add_record(network['ipaddr6'], network['asn'])

        #todo: implement SQLite PeeringDB lookup
        else:
            raise TypeError('PeeringDB file must JSON or SQLite format.')

    def lookup(self, router_ip):
        if ip_address(router_ip) in self._ipdb:
            return self._ipdb[ip_address(router_ip)]
        else:
            return None
    
    def export(self, output):
        """
        Export router IP to ASN mapping.

        Args:
            output (str): destination .json file
        """
        with open(output, 'w', encoding='utf-8') as f:
            f.write(ujson.dumps(self._ipdb))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Map traceroute IP addresses to ASNs')
    parser.add_argument('-xdb', '--ixpdb',
                        help='IXPDB file',
                        required=False)
    parser.add_argument('-pdb', '--peeringdb',
                        help='PeeringDB file',
                        required=True)
    parser.add_argument('-o', '--output',
                    help='Destination .json file',
                    required=True)
    args = parser.parse_args()

    router_to_as = Router2AS()
    router_to_as.load_from_peeringdb(args.peeringdb)
    if args.ixpdb:
        router_to_as.load_from_ixpdb(args.ixpdb) # Replaces PeeringDB values
    router_to_as.export(args.output)