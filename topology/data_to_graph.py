import networkx as nx
import argparse
import ujson
import requests
import csv

# Load adjacency data
def load_adjacencies(adjacencies_file):
    """
    Load inter-AS adjacencies from a file.

    Args:
        adjacencies_file (str): Text file of inter-AS adjacencies.

    Returns:
        list of tuple: ASes with direct connectivity.
    """
    with open(adjacencies_file, 'r') as f:
        adjacencies_raw = f.readlines()
        adjacencies = []
        for line in adjacencies_raw:
            adjacencies.append(tuple(sorted(int(x) for x in line.strip().split(','))))
        del adjacencies_raw
    return adjacencies

# Transform adjacencies to a graph
def adjacencies_to_graph(adjacencies):
    """
    Construct AS topology graph from adjacencies.

    Args:
        adjacencies (list of tuple): ASes with direct connectivity.

    Returns:
        networkx Graph: Undirected Graph object.
    """
    G = nx.Graph()
    for peering in adjacencies:
        nx.add_star(G, list(peering))
    return G.copy()

# Label edges
def import_as_rel(G, as_rel_data):
    """
    Load AS relationship data

    Args:
        G (networkx Graph): Graph object to load relationships for
        as_rel_data (str): Path to AS relationships data (in CAIDA AS Relationships format)

    Raises:
        Exception: Failed to import.
    """
    try:
        with open(as_rel_data) as f:
            for line in f:
                line = line.strip()

                # Handle comment/label lines
                if line[0] == "#":
                    continue
                
                # Handle data lines
                line = line.split('|')
                if len(line) < 4:
                    # Expecting src|dst|dir|ref
                    # Skip if format not met
                    continue

                src = int(line[0])
                dst = int(line[1])
                
                # Provider-to-Customer relationships
                if line[2] == "-1":
                    direction = str(src) + "|" + str(dst) + "|" + "-1"
                    G.add_edge(src, dst, dir=direction, ref=line[3])
                elif line[2] == "0":
                    G.add_edge(src, dst, dir=0, ref=line[3])
                else:
                    raise Exception("Invalid relationship in AS relationships file")
    except:
        raise Exception("Failed to import AS relationship data")
    
# Load hegemony values
# This is calculated by IHR tooling in format: timebin,originasn,asn,hege
def load_hegemony(filename):
    hegemony = {}
    with open(filename, 'r') as f:
        hege_data = f.readlines()[1:]
    for line in hege_data:
        line = line.strip().split(',')
        if int(line[2]) in hegemony:
            # Max value over time period
            hegemony[int(line[2])] = max(hegemony[int(line[2])], float(line[3]))
        else:
            hegemony[int(line[2])] = float(line[3])
    return hegemony

def load_peeringdb_asns(filename):
    pdb = {}
    with open(filename, 'r', encoding='utf-8') as f:
        pdb_data = ujson.load(f)
    nets = pdb_data['net']['data']
    ixlans = pdb_data['netixlan']['data']
    for net in nets:
        asn = int(net.get('asn'))
        if asn is None:
            continue
        pdb_name = net.get('name', '')
        pdb_type = net.get('info_types', '')
        if isinstance(pdb_type, list):
            # Take first type in list as primary
            pdb_type = pdb_type[0] if pdb_type else ''

        # Identify all IXPs present at
        pops = []
        for ixlan in ixlans:
            if ixlan['net_id'] == net.get('id'):
                pops.append(ixlan['ix_id'])

        pdb[asn] = {
            'pdb_name': pdb_name,
            'pdb_type': pdb_type,
            'ix_set': net.get('ix_set', []),
            'pops': pops
        }
    return pdb

def load_peeringdb_ixps(filename):
    pdb = {}
    with open(filename, 'r', encoding='utf-8') as f:
        pdb_data = ujson.load(f)
    ixps = pdb_data['ix']['data']
    for ix in ixps:
        pdb[int(ix.get('id'))] = {
            'name': ix.get('name'),
            'country': ix.get('country', ''),
            'region': ix.get('region_continent', ''),
            'net_count': ix.get('net_count', '')
        }
    return pdb

# From bgp.tools
def load_bgptools_tags(tags_list_file, tags_folder):
    bgptools_tags = {}

    with open(tags_list_file, 'r') as f:
        tags_list = f.readlines()

    #perso,1441

    if tags_folder[-1] != '/':
        tags_folder += '/'

    for tag in tags_list:
        tag = tag.split(',')[0]
        with open(tags_folder + tag + '.csv', 'r') as f:
            for line in f:
                if line.startswith('<'):
                    # File not in correct format.
                    break
                line = line.split(',')[0]
                if int(line[2:]) in bgptools_tags:
                    bgptools_tags[int(line[2:])].append(tag)
                else:
                    bgptools_tags[int(line[2:])] = [tag]

    return bgptools_tags

def load_countries_and_colours(filename):
    # ['country', 'alpha-2 code', 'latitude (average)', 'longitude (average)']
    countries = {}
    with open(filename, 'r') as f:
        country_data = csv.reader(f, delimiter=',', quotechar='"')
        next(country_data)
    
        for row in country_data:
            countries[row[1]] = {
                'name': row[0],
                'latitude': row[2],
                'longitude': row[3],
                'colour': row[4]
            }
    return countries

def get_country_asns(country_code):
    """
    Get all resources registered in a country, from the country code.
    """
    HEADERS = {'content-type': 'application/json'}
    PARAMS = {'resource': country_code, 'time': '2025-11-07'}
    url = 'https://stat.ripe.net/data/country-resource-list/data.json'

    # Get Data
    resources = requests.get(url, headers=HEADERS, params=PARAMS).content

    return [int(asn) for asn in ujson.loads(resources)['data']['resources']['asn']]

def get_registered_countries_for_asns(countries):
    # ASN <-> COUNTRY MAPPING
    get_asn_country = {}

    for country in countries.keys():
        country_asns = get_country_asns(country)

        for asn in country_asns:
            get_asn_country[asn] = country

    with open('../data/working/asn_to_country.json', 'w') as f:
        writer = ujson.dumps(get_asn_country)
        f.write(writer)

    return get_asn_country

def load_registered_countries_for_asns(file):
    with open(file, 'r') as f:
        data = ujson.load(f)
    return data

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Convert Internet data to topology graph')
    parser.add_argument('-a', '--adjacencies',
                        help='Adjacencies .txt file',
                        required=True)
    parser.add_argument('-r', '--relationships',
                        help='AS relationships .txt file',
                        required=False)
    parser.add_argument('-c', '--countries',
                        help='Countries and country colour data',
                        required=False)
    parser.add_argument('--asnregs',
                        help='ASN-to-country mapping .json',
                        required=False)
    parser.add_argument('-h4', '--hegemony4',
                        help='AS hegemony values for IPv4',
                        required=False)
    parser.add_argument('-h6', '--hegemony6',
                        help='AS hegemony values for IPv6',
                        required=False)
    parser.add_argument('-p', '--peeringdb',
                        help='PeeringDB .json file',
                        required=False)
    parser.add_argument('-b', '--bgptools',
                        help='bgp.tools tags.txt and tag folder path',
                        required=False,
                        nargs=2)
    parser.add_argument('-o', '--output',
                        help='Destination .graphml file',
                        required=True)
    
    args = parser.parse_args()

    print("Loading adjacencies")
    G = adjacencies_to_graph(load_adjacencies(args.adjacencies))
    
    if args.relationships is not None:
        print('Loading relationships')
        import_as_rel(G, args.relationships)

    if args.countries is not None:
        print('Loading countries')
        countries = load_countries_and_colours(args.countries)

        if args.asnregs is not None:
            print('Loading asn-to-country mappings')
            get_asn_country = load_registered_countries_for_asns(args.asnregs)
        else:
            print('Fetching asn-to-country mappings (this may take some time)')
            get_asn_country = get_registered_countries_for_asns(countries)

    # Dict ASN:value
    if args.hegemony4 is not None:
        print('Loading AS IPv4 hegemony')
        hege_v4 = load_hegemony(args.hegemony4)
    if args.hegemony6 is not None:
        print('Loading AS IPv6 hegemony')
        hege_v6 = load_hegemony(args.hegemony6)

    if args.peeringdb is not None:
        print('Loading PeeringDB data')
        pdb_as = load_peeringdb_asns(args.peeringdb)
        pdb_ix = load_peeringdb_ixps(args.peeringdb)

    if args.bgptools is not None:
        print('Loading bgp.tools data')
        if len(args.bgptools) < 2:
            raise ValueError
        bgptools_tags = load_bgptools_tags(args.bgptools[0], args.bgptools[1])
    
    print('Mapping attributes to ASNs')

    # Add metadata
    attributes = {}
    for asn in G.nodes():
        attributes[asn] = {}

        if args.countries is not None:
            attributes[asn]['country_registered'] = get_asn_country.get(asn, '') # type: ignore

            if attributes[asn]['country_registered'] != '': # type: ignore
                attributes[asn]['country_registered_name'] = countries[attributes[asn]['country_registered']].get('name')
                attributes[asn]['country_registered_colour'] = countries[attributes[asn]['country_registered']].get('colour')
                attributes[asn]['country_registered_latitude'] = countries[attributes[asn]['country_registered']].get('latitude')
                attributes[asn]['country_registered_longitude'] = countries[attributes[asn]['country_registered']].get('longitude')
            else:
                attributes[asn]['country_registered_name'] = 'N/A (Legacy ASN)'
                attributes[asn]['country_registered_colour'] = '#000000'
                attributes[asn]['country_registered_latitude'] = '0'
                attributes[asn]['country_registered_longitude'] = '0'
        
        if args.hegemony4 is not None:
            attributes[asn]['hegemony_v4'] = hege_v4.get(asn, 0)
        
        if args.hegemony6 is not None:
            attributes[asn]['hegemony_v6'] = hege_v6.get(asn, 0)

        if args.peeringdb is not None:
            if asn in pdb_as:
                attributes[asn]['peeringdb_name'] = pdb_as[asn].get('pdb_name', '')
                attributes[asn]['peeringdb_type'] = pdb_as[asn].get('pdb_type', '')

                peeringdb_ixps = '' if len(pdb_as[asn].get('pops','')) == 0 else '|'
                country_operating = '' if len(pdb_as[asn].get('pops','')) == 0 else '|'
                for pop in pdb_as[asn].get('pops'):
                    peeringdb_ixps += pdb_ix[pop].get('name') + '|'
                    country_operating += pdb_ix[pop].get('country') + '|'
                
                attributes[asn]['peeringdb_ixps'] = peeringdb_ixps
                attributes[asn]['country_operating'] = country_operating
            else:
                attributes[asn]['peeringdb_name'] = ''
                attributes[asn]['peeringdb_type'] = ''
                attributes[asn]['peeringdb_ixps'] = ''
                attributes[asn]['country_operating'] = ''

        if args.bgptools is not None:
            attributes[asn]['bgptools_tags'] = '|'.join(bgptools_tags.get(asn, []))
            if len(attributes[asn]['bgptools_tags']) > 0:
                attributes[asn]['bgptools_tags'] = '|' + attributes[asn]['bgptools_tags'] + '|'
    
    print('Attributes data compiled')

    print('Exporting attributes to .json')
    with open('../data/working/asn_attributes.json', 'w') as f:
        writer = ujson.dumps(attributes)
        f.write(writer)
    
    print('Adding to graph')

    for node in G.nodes():
        G.nodes[node].update(attributes[node])

    #nx.set_node_attributes(G, attributes)
        
    print('Exporting graph')
    nx.write_graphml(G, args.output, encoding='utf-8', prettyprint=True)
