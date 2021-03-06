import argparse
import logging
import os

from datetime import datetime
from inspect import isclass

from hdfaccess.file import hdf_file
from hdfaccess.utils import strip_hdf

from analysis_engine.api_handler import APIError, get_api_handler
from analysis_engine.dependency_graph import dependencies3, graph_nodes
from analysis_engine.node import Node, NodeManager
from analysis_engine import settings


logger = logging.getLogger(__name__)


def get_aircraft_info(tail_number):
    '''
    Fetch aircraft info from settings.API_HANDLER or from LOCAL_API_HANDLER
    if there is an API_ERROR raised.
    
    :param tail_number: Aircraft tail registration
    :type tail_number: string
    :returns: Aircraft information key:value pairs
    :rtype: dict
    '''
    # Fetch aircraft info through the API.
    api_handler = get_api_handler(settings.API_HANDLER)
    
    try:
        aircraft_info = api_handler.get_aircraft(tail_number)
    except APIError:
        if settings.API_HANDLER == settings.LOCAL_API_HANDLER:
            raise
        # Fallback to the local API handler.
        logger.info(
            "Aircraft '%s' could not be found with '%s' API handler. "
            "Falling back to '%s'.", tail_number, settings.API_HANDLER,
            settings.LOCAL_API_HANDLER)
        api_handler = get_api_handler(settings.LOCAL_API_HANDLER)
        aircraft_info = api_handler.get_aircraft(tail_number)
    logger.info("Using aircraft_info provided by '%s' '%s'.",
                api_handler.__class__.__name__, aircraft_info)        
    return aircraft_info


def get_derived_nodes(module_names):
    '''
    Create a key:value pair of each node_name to Node class for all Nodes
    within modules provided.
    
    sample module_names = ['path_to.module', 'analysis_engine.flight_phase',..]
    
    :param module_names: Module names to import as locations on PYTHON PATH
    :type module_names: List of Strings
    :returns: Module name to Classes
    :rtype: Dict
    '''
    def isclassandsubclass(value, classinfo):
        return isclass(value) and issubclass(value, classinfo)

    nodes = {}
    for name in module_names:
        #Ref:
        #http://code.activestate.com/recipes/223972-import-package-modules-at-runtime/
        # You may notice something odd about the call to __import__(): why is
        # the last parameter a list whose only member is an empty string? This
        # hack stems from a quirk about __import__(): if the last parameter is
        # empty, loading class "A.B.C.D" actually only loads "A". If the last
        # parameter is defined, regardless of what its value is, we end up
        # loading "A.B.C"
        ##abstract_nodes = ['Node', 'Derived Parameter Node', 'Key Point Value Node', 'Flight Phase Node'
        ##print 'importing', name
        module = __import__(name, globals(), locals(), [''])
        for c in vars(module).values():
            if isclassandsubclass(c, Node) \
                    and c.__module__ != 'analysis_engine.node':
                try:
                    #TODO: Alert when dupe node_name found which overrides previous
                    ##name = c.get_name()
                    ##if name in nodes:
                        ### alert about overide happening or raise out?
                    ##nodes[name] = c
                    nodes[c.get_name()] = c
                except TypeError:
                    #TODO: Handle the expected error of top level classes
                    # Can't instantiate abstract class DerivedParameterNode
                    # - but don't know how to detect if we're at that level without resorting to 'if c.get_name() in 'derived parameter node',..
                    logger.exception('Failed to import class: %s' % c.get_name())
    return nodes


def derived_trimmer(hdf_path, node_names, dest):
    '''
    Trims an HDF file of parameters which are not dependencies of nodes in
    node_names.
    
    :param hdf_path: file path of hdf file.
    :type hdf_path: str
    :param node_names: A list of Node names which are required.
    :type node_names: list of str
    :param dest: destination path for trimmed output file
    :type dest: str
    :return: parameters in stripped hdf file
    :rtype: [str]
    '''
    params = []
    with hdf_file(hdf_path) as hdf:
        derived_nodes = get_derived_nodes(settings.NODE_MODULES)
        node_mgr = NodeManager(
            datetime.now(), hdf.duration, hdf.valid_param_names(), [],
            derived_nodes, {}, {})
        _graph = graph_nodes(node_mgr)
        for node_name in node_names:
            deps = dependencies3(_graph, node_name, node_mgr)
            params.extend(filter(lambda d: d in node_mgr.hdf_keys, deps))
    return strip_hdf(hdf_path, params, dest) 


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    subparser = parser.add_subparsers(dest='command',
                                      description="Utility command, currently "
                                      "only 'trimmer' is supported",
                                      help='Additional help')
    trimmer_parser = subparser.add_parser('trimmer')
    trimmer_parser.add_argument('input_file_path', help='Input hdf filename.')  
    trimmer_parser.add_argument('output_file_path', help='Output hdf filename.')
    trimmer_parser.add_argument('nodes', nargs='+',
                                help='Keep dependencies of the specified nodes '
                                'within the output hdf file. All other '
                                'parameters will be stripped.')
    
    args = parser.parse_args()
    if args.command == 'trimmer':
        if not os.path.isfile(args.input_file_path):
            parser.error("Input file path '%s' does not exist." %
                         args.input_file_path)
        if os.path.exists(args.output_file_path):
            parser.error("Output file path '%s' already exists." %
                         args.output_file_path)
        output_parameters = derived_trimmer(args.input_file_path, args.nodes,
                                            args.output_file_path)
        if output_parameters:
            print 'The following parameters are in the output hdf file:'
            for name in output_parameters:
                print ' * %s' % name
        else:
            print 'No matching parameters were found in the hdf file.'            
    else:
        parser.error("'%s' is not a known command." % args.command)


def _get_names(module_locations, fetch_names=True, fetch_dependencies=False):
    '''
    Get the names of Nodes and dependencies.
    
    :param module_locations: list of locations to fetch modules from
    :type module_locations: list of strings
    :param fetch_names: Return name of parameters etc. created by class
    :type fetch_names: Bool
    :param fetch_dependencies: Return names of the arguments in derive methods
    :type fetch_dependencies: Bool
    '''
    nodes = get_derived_nodes(module_locations)
    names = []
    for node in nodes.values():
        if fetch_names:
            if hasattr(node, 'names'):
                # FormattedNameNode (KPV/KTI) can have many names
                names.extend(node.names())
            else:
                names.append(node.get_name())
        if fetch_dependencies:
            names.extend(node.get_dependency_names())
    return sorted(names)
    
    
def list_parameters():
    '''
    Return an ordered list of parameters.
    '''
    # Exclude all KPV, KTI, Section, Attribute, etc:
    exclude = _get_names([
        'analysis_engine.approaches',
        'analysis_engine.flight_attribute',
        'analysis_engine.flight_phase',
        'analysis_engine.key_point_values',
        'analysis_engine.key_time_instances',
    ], fetch_names=True, fetch_dependencies=False)
    # Remove excluded names leaving parameters:
    parameters = set(list_everything()) - set(exclude)
    return sorted(parameters)


def list_derived_parameters():
    '''
    Return an ordered list of the derived parameters which have been coded.
    '''
    return _get_names([
        'analysis_engine.derived_parameters',
        'analysis_engine.multistate_parameters',
    ])


def list_lfl_parameter_dependencies():
    '''
    Return an ordered list of the non-derived parameters.
    
    This should be mostly LFL parameters.
    
    Note: A few Attributes will be in here too!
    '''
    parameters = set(list_parameters()) - set(list_derived_parameters())
    return sorted(parameters)


def list_everything():
    '''
    Return an ordered list of all parameters both derived and required.
    '''
    return _get_names(settings.NODE_MODULES, True, True)


def list_kpvs():
    '''
    Return an ordered list of the key point values which have been coded.
    '''
    return _get_names(['analysis_engine.key_point_values'])


def list_ktis():
    '''
    Return an ordered list of the key time instances which have been coded.
    '''
    return _get_names(['analysis_engine.key_time_instances'])


def list_flight_attributes():
    '''
    Return an ordered list of the flight attributes which have been coded.
    '''
    return _get_names(['analysis_engine.flight_attribute'])


def list_flight_phases():
    '''
    Return an ordered list of the flight phases which have been coded.
    '''
    return _get_names(['analysis_engine.flight_phase'])
