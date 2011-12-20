import sys
import logging 
import networkx as nx # pip install networkx or /opt/epd/bin/easy_install networkx

from analysis import settings
from utilities.dict_helpers import dict_filter

not_windows = sys.platform not in ('win32', 'win64') # False for Windows :-(

"""
TODO:
=====
* Colour nodes by derived parameter type
* reverse digraph to get arrows poitning towards the root - use pre's rather than successors in tree traversal


"""


##def breadth_first_search_all_nodes(di_graph, root):
    ##"""
    ##only useful for us with a di_graph
    
    ##Returns all nodes traversed, not just new ones.
    
    ##Removed filter (as not required) 
    ##"""
    ##def bfs():
        ##"""
        ##Breadth-first search subfunction.
        ##"""
        ##while (queue != []):
            ##node = queue.pop(0)
            ##for other in di_graph[node]:
                ###if other not in spanning_tree:
                ##queue.append(other)
                ##ordering.append(other)
                ##spanning_tree[other] = node
    ##if filter(lambda e: e[0] == e[1], di_graph.edges()):
        ### If there is a recursive loop, raise an exception rather than looping
        ### until a MemoryError is eventually raised.
        ##raise ValueError("Traversal with fail with recursive dependencies in "
                         ##"the digraph.")
    ##queue = [root]            # Visiting queue
    ##spanning_tree = dict(root=None)    # Spanning tree
    ##ordering = [root]
    ##bfs()
    ####return spanning_tree, ordering
    ##return ordering


def dependencies3(di_graph, root, node_mgr):
    
    def traverse_tree(node):
        layer = []
        for dependency in di_graph.successors(node):
            # traverse again
            if traverse_tree(dependency):
                layer.append(dependency)
            
        if node in active_nodes:
            # node already discovered operational
            return True
        elif node_mgr.operational(node, layer):
            # node will work at this level
            if layer:
                new_nodes = [n for n in layer if n not in active_nodes]
                if new_nodes:
                    active_nodes.update(new_nodes)
                    ordering.extend(new_nodes) # add the new nodes
            return True # layer below works
        else:
            # node does not work
            return False
        
    ordering = [] # reverse
    active_nodes = set() # operational nodes visited for fast lookup
    if traverse_tree(root): # start recursion
        ordering.append(root)
    return ordering


# Display entire dependency graph, not taking into account which are active for a frame
def draw_graph(graph, name, horizontal=True):
    """
    Draws a graph to file with label and filename taken from name argument.
    
    Note: Graphviz binaries cannot be easily installed on Windows (you must
    build it from source), therefore you shouldn't bother trying to
    draw_graph unless you've done so!
    """
    file_path = 'graph_%s.png' % name.lower().replace(' ', '_')

    # Trying to get matplotlib to install nicely
    # Warning: pyplot does not render the graphs well!
    ##import matplotlib.pyplot as plt
    ##nx.draw(graph)
    ##plt.show()
    ##plt.savefig(file_path)
    try:
        ##import pygraphviz as pgv 
        # sudo apt-get install graphviz libgraphviz-dev
        # pip install pygraphviz
        #Note: nx.to_agraph performs pygraphviz import
        if horizontal:
            # set layout left to right before converting all nodes to new format
            graph.graph['graph'] = {'rankdir' : 'LR'}
        G = nx.to_agraph(graph)
    except ImportError:
        logging.exception("Unable to import pygraphviz to draw graph '%s'", name)
        return
    G.layout(prog='dot')
    G.graph_attr['label'] = name
    G.draw(file_path)
    
    
def graph_nodes(node_mgr):
    """
    :param node_mgr:
    :type node_mgr: NodeManager
    """
    # gr_all will contain all nodes
    gr_all = nx.DiGraph()
    # create nodes without attributes now as you can only add attributes once
    # (limitation of add_node_attribute())
    gr_all.add_nodes_from(node_mgr.lfl, color='forestgreen')
    derived_minus_lfl = dict_filter(node_mgr.derived_nodes, remove=node_mgr.lfl)
    gr_all.add_nodes_from(derived_minus_lfl.keys())
    
    # build list of dependencies
    derived_deps = set()  # list of derived dependencies
    for node_name, node_obj in derived_minus_lfl.iteritems():
        derived_deps.update(node_obj.get_dependency_names())
        # Create edges between node and its dependencies
        edges = [(node_name, dep) for dep in node_obj.get_dependency_names()]
        gr_all.add_edges_from(edges)
            
    # add root - the top level application dependency structure based on required nodes
    # filter only nodes which are at the top of the tree (no predecessors)
    gr_all.add_node('root', color='red')
    root_edges = [('root', node_name) for node_name in node_mgr.requested \
                  if not gr_all.predecessors(node_name)] 
    gr_all.add_edges_from(root_edges, color='red')
    
    #TODO: Split this up into the following lists of nodes
    # * LFL used
    # * LFL unused
    # * Derived used
    # * Derived not operational
    # * Derived not used -- coz not referenced by a dependency kpv etc therefore not part of the spanning tree
    
    # Note: It's hard to tell whether a missing dependency is a mistyped
    # reference to another derived parameter or a parameter not available on
    # this LFL
    # Set of all derived and LFL Nodes.
    ##available_nodes = set(node_mgr.derived_nodes.keys()).union(set(node_mgr.lfl))
    available_nodes = set(node_mgr.keys())
    # Missing dependencies.
    missing_derived_dep = list(derived_deps - available_nodes)
    # Missing dependencies which are required.
    missing_required = list(set(node_mgr.requested) - available_nodes)
    
    if missing_derived_dep:
        logging.warning("Dependencies referenced are not in LFL nor Node modules: %s",
                        missing_derived_dep)
    if missing_required:
        raise ValueError("Missing required parameters: %s" % missing_required)

    # Add missing nodes to graph so it shows everything. These should all be
    # RAW parameters missing from the LFL unless something has gone wrong with
    # the derived_nodes dict!    
    gr_all.add_nodes_from(missing_derived_dep)  
    return gr_all

    
def process_order(gr_all, node_mgr): ##lfl_params, derived_nodes):
    """
    :param gr_all:
    :type gr_all: nx.DiGraph
    :param derived_nodes: 
    :type derived_nodes: dict
    :param lfl_params:
    :type lfl_nodes: list of strings
    :returns:
    :rtype: 
    """
    # Then, draw the breadth first search spanning tree rooted at top of application
    ##order = breadth_first_search_all_nodes(gr_all, root="root")
    process_order = dependencies3(gr_all, 'root', node_mgr)
    logging.info("Processing order of %d nodes is: %s", len(process_order), process_order)
    

    
    ### Determine whether nodes are operational, this will repeatedly ask some 
    ### nodes as they may only become operational later on.
    ##process_order = []
    ##for node in reversed(order):
        ##if node_mgr.operational(node, process_order):
            ##if node not in node_mgr.lfl + ['root']:
                ##gr_all.node[node]['color'] = 'blue'
            ### un-grey edges that were previously inactive
            ##active_edges = gr_all.in_edges(node)
            ##gr_all.add_edges_from(active_edges, color='black')
            ##process_order.append(node)
        ##else:
            ##gr_all.node[node]['color'] = 'grey'
            ##inactive_edges = gr_all.in_edges(node)
            ##gr_all.add_edges_from(inactive_edges, color='grey')

    # remove nodes from gr_st that aren't in the process order
    ##gr_st.remove_nodes_from(set(gr_st.nodes()) - set(process_order))
    
    ### Breadth First Search Spanning Tree
    ###st, order = breadth_first_search(gr_st, root="root")
    ##order = list(nx.breadth_first_search.bfs_edges(gr_st, 'root')) #Q: Is there a method like in pygraph for retrieving the order of nodes traversed?
    ##if not order:
        ##raise ValueError("No relationship between any nodes - no process order can be defined!")
    
    ### reduce edges to node list and assign process order labels to the edges
    ### Note: this will skip last node (as it doesn't have an edge), which should 
    ### always be 'root' - this is desirable!
    ##node_order = []
    ##for n, edge in enumerate(reversed(order)):
        ##node_order.append(edge[1]) #Q: is there a neater way to get the nodes?
        ##gr_all.edge[edge[0]][edge[1]]['label'] = n
        ##gr_st.edge[edge[0]][edge[1]]['label'] = n
    for n, node in enumerate(process_order):
        gr_all.node[node]['label'] = n
        
    gr_st = gr_all.copy() 
    gr_st.remove_nodes_from(set(gr_st.nodes()) - set(process_order))
    
    ##logging.debug("Node processing order: %s", node_order)
        
    ##return gr_all, gr_st, node_order 
    return gr_all, gr_st, process_order[:-1] # exclude 'root'


def remove_floating_nodes(graph):
    """
    Remove all nodes which aren't referenced within the dependency tree
    """
    nodes = list(graph)
    for node in nodes:
        if not graph.predecessors(node) and not graph.successors(node):
            graph.remove_node(node)
    return graph
     
     
def dependency_order(node_mgr, draw=not_windows):
    """
    Main method for retrieving processing order of nodes.
    
    :param node_mgr: 
    :type node_mgr: NodeManager
    :param draw: Will draw the graph. Green nodes are available LFL params, Blue are operational derived, Black are not required derived, Red are active top level requested params, Grey are inactive params. Edges are labelled with processing order.
    :type draw: boolean
    :returns: List of Nodes determining the order for processing.
    :rtype: list of strings
    """
    _graph = graph_nodes(node_mgr)
    # TODO: Remove the two following lines. 
    ##_graph = remove_floating_nodes(_graph)
    ##draw_graph(_graph, 'Dependency Tree')
    gr_all, gr_st, order = process_order(_graph, node_mgr)
    
    inoperable_required = list(set(node_mgr.requested) - set(order))
    if inoperable_required:
        logging.warning("Required parameters are inoperable: %s", inoperable_required)
    if draw:
        draw_graph(gr_st, 'Active Nodes in Spanning Tree')
        draw_graph(gr_all, 'Dependency Tree')
    return order


