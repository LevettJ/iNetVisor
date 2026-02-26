"""
Separate clean and undesirable paths.
@author Joshua Levett
"""
import argparse
import json
import sqlite3
import gc

class CleanPaths(object):
    """
    Clean and export BGP paths
    """

    def __init__(self):
        """
        Clean and export BGP paths
        """
        # Route servers
        self.route_servers = set()

        # Removed or fixed paths
        self.prepended_paths = []
        self.route_server_paths = []
        self.looped_paths = []
        self.bogon_paths = []
        
        # Clean paths
        self.clean_paths = []

    def set_route_servers_from_peeringdb(self, peeringdb):
        """
        Load PeeringDB file to form a list of route servers

        Args:
            peeringdb (str): path to PeeringDB JSON/SQLite data.
        """
        # Based on the original ProbLink tool by Yuchen Jin (https://github.com/YuchenJin/ProbLink).
        if peeringdb.endswith('json'):
            with open(peeringdb) as f:
                data = json.load(f)
            for i in data['net']['data']:
                if i['info_type'] == 'Route Server':
                    self.route_servers.add(str(i['asn']))
        elif peeringdb.endswith('sqlite'):
            conn = sqlite3.connect(peeringdb)
            c = conn.cursor()
            for row in c.execute("SELECT asn, info_type FROM 'peeringdb_network'"):
                asn, info_type = row
                if info_type == 'Route Server':
                    self.route_servers.add(str(asn))
        else:
            raise TypeError('PeeringDB file must JSON or SQLite format.')

    def parse_paths(self, paths):
        """
        Parse a list of paths and separate clean and undesirable paths.

        Args:
            paths (list): list of paths.
        """
        for record in paths:
            path, meta = record.strip().split('/')
            path = path.split('|')

            # Ignore empty paths
            if path[0]=='':
                continue

            # Clean path
            path = self.remove_prepending(path, meta)
            path = self.remove_route_servers(path, meta)

            # Remove path if invalid
            if self.is_looped_path(path, meta) or self.contains_bogons(path, meta):
                continue
            
            # Store cleaned path
            self.clean_paths.append(self._format_path(path, meta))

    def export(self, outputdir, postfix=''):
        """
        Write clean and undesirable paths to a directory

        Args:
            outputdir (str): path to folder to write to, without trailing slash.
            postfix (str) (optional): string to append on filename, useful to avoid high-memory use-cases.
        """
        with open(outputdir + '/clean_paths' + postfix + '.txt', 'a', encoding='utf-8') as f:
            f.write('\n'.join(self.clean_paths))
            f.flush()
        
        with open(outputdir + '/formerly_prepended_paths' + postfix + '.txt', 'a', encoding='utf-8') as f:
            f.write('\n'.join(self.prepended_paths))
            f.flush()
        
        with open(outputdir + '/formerly_route_server_paths' + postfix + '.txt', 'a', encoding='utf-8') as f:
            f.write('\n'.join(self.route_server_paths))
            f.flush()
        
        with open(outputdir + '/removed_looped_paths' + postfix + '.txt', 'a', encoding='utf-8') as f:
            f.write('\n'.join(self.looped_paths))
            f.flush()

        with open(outputdir + '/removed_bogon_paths' + postfix + '.txt', 'a', encoding='utf-8') as f:
            f.write('\n'.join(self.bogon_paths))
            f.flush()

    def _format_path(self, path, meta):
        """
        Create a path string with path and metadata

        Args:
            path (list): the BGP as_path.
            meta (str): IP version and timestamp with pipe separation (e.g. v4|1704110400.0).

        Returns:
            str: formatted string P|A|T|H/IPver|timestamp
        """
        return str('|'.join(path) + '/' + meta)

    def remove_prepending(self, path, meta):
        """
        Remove prepending in the as_path.

        Args:
            path (list): the BGP as_path.
            meta (str): IP version and timestamp with pipe separation (e.g. v4|1704110400.0).

        Returns:
            list: the BGP as_path without prepending.
        """
        old_path = path
        path = [v for i, v in enumerate(path) if i==0 or v!=path[i-1]]
        if old_path != path:
            self.prepended_paths.append(self._format_path(old_path, meta))
        return path

    def remove_route_servers(self, path, meta):
        """
        Remove route servers from as_path.

        Args:
            path (list): the BGP as_path.
            meta (str): IP version and timestamp with pipe separation (e.g. v4|1704110400.0).

        Returns:
            list: the BGP as_path with route servers removed.
        """
        old_path = path
        for asn in path:
            if asn in self.route_servers:
                path.remove(asn)
        if old_path != path:
            self.route_server_paths.append(self._format_path(old_path, meta))
        return path

    def is_looped_path(self, path, meta):
        """
        Detect as_paths with loops.

        Args:
            path (list): the BGP as_path.
            meta (str): IP version and timestamp with pipe separation (e.g. v4|1704110400.0).

        Returns:
            bool: True if path contains a loop; false otherwise.
        """
        if len(set(path)) != len(path):
            self.looped_paths.append(self._format_path(path, meta))
            return True
        return False
    
    def contains_bogons(self, path, meta):
        """
        Detect paths containing bogon ASNs

        Args:
            path (list): the BGP as_path.
            meta (str): IP version and timestamp with pipe separation (e.g. v4|1704110400.0).

        Returns:
            bool: True if path contains a bogon; false otherwise.
        """

        def has_bogon():
            self.bogon_paths.append(self._format_path(path, meta))
            return True

        for asn in path:
            asn = int(asn)

            # Reserved ASNs
            if asn == 0: # Reserved by RFC7607
                return has_bogon()
            if asn == 112: # Reserved by RFC7534
                return has_bogon()
            if asn == 23456: # Reserved by RFC6793
                # AS_TRANS provides backwards compatibility for non-16bit BGP speakers
                # Modern devices support 32bit ASNs so 23456 in the as_path is likely
                # a misconfiguration or software issue (see more in bgpfilterguide.nlnog.net)
                return has_bogon()
            if 64496 <= asn <= 64511 or 65536 <= asn <= 65551: # Reserved by RFC5398
                return has_bogon()
            if 64512 <= asn <= 65534 or 4200000000 <= asn <= 4294967294	: # Reserved by RFC6996
                return has_bogon()
            if asn == 65535 or asn == 4294967295: # Reserved by RFC7300
                return has_bogon()

            # IANA unallocated ASNs (as of July 2024)
            if 153914 <= asn <= 196607:
                return has_bogon()
            if 216476 <= asn <= 262143:
                return has_bogon()
            if 274845 <= asn <= 327679:
                return has_bogon()
            if 329728 <= asn <= 393215:
                return has_bogon()
            if 402333 <= asn <= 4199999999:
                return has_bogon()

        return False

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Separate clean and undesirable paths.')
    parser.add_argument('-in', '--input',
                        help='File containing a list of files with paths',
                        required=True)
    parser.add_argument('-pdb', '--peeringdb',
                        help='PeeringDB file',
                        required=True)
    parser.add_argument('-o', '--outputdir',
                        help='Directory to save tool outputs',
                        required=True)
    args = parser.parse_args()

    with open(args.input, 'r', encoding='utf-8') as f:
        list_of_files = f.readlines()

    for i, file in enumerate(list_of_files):
        with open(file.rstrip(), 'r', encoding='utf-8') as f:
            paths = f.readlines()
            cleaner = CleanPaths()
            cleaner.set_route_servers_from_peeringdb(args.peeringdb)
            cleaner.parse_paths(paths)
            cleaner.export(args.outputdir, str(i))
            # Force deletion of cleaner object for memory efficiency.
            f.flush()
            del cleaner
        gc.collect()
        