from __future__ import print_function
import argparse
import attr
import pkg_resources
from ruamel import yaml
import sys
import graphviz as gv
from ..fileio import openBw64Adm
from ..fileio.adm.time_format import unparse_time
from ..fileio.adm.xml import parse_file


def load_style():
    fname = "data/default_graph_config.yaml"
    with pkg_resources.resource_stream(__name__, fname) as style_file:
        return yaml.safe_load(style_file)


style = load_style()


def create_attribute_string(attribute, element_dict):
    value = None
    if attribute == 'typeDefinition':
        value = element_dict['type'].name
    elif attribute == 'typeLabel':
        value = '{:04d}'.format(element_dict['type'].value)
    elif attribute == 'formatDefinition':
        value = element_dict['format'].name
    elif attribute == 'formatLabel':
        value = '{:04d}'.format(element_dict['format'].value)
    elif attribute in ['start', 'end', 'duration']:
        if(element_dict[attribute] is not None):
            value = unparse_time(element_dict[attribute])
    elif attribute == 'frequency':
        value = '{0}'.format(element_dict[attribute])
        value = value[1:-1]
    elif attribute == 'audioComplementaryObjectIDRef':
        if(element_dict['audioComplementaryObjects']):
            value = ""
            for object in element_dict['audioComplementaryObjects']:
                value += '{0}, '.format(object['id'])
            value = value[0:-2]
    else:
        value = element_dict[attribute]
    return value


def create_attributes_string(element):
    element_dict = attr.asdict(element)
    content = '{{{0.id}'.format(element)
    first = True
    for attribute in style[element.element_type]['attributes']:
        if first:
            content += '|'
            first = False
        value_string = create_attribute_string(attribute, element_dict)
        if(value_string or style[element.element_type]
                                ['plot_attributes_with_none_value']):
            content += '{attribute}="{value}"\\l'.format(
                attribute=attribute, value=value_string)
    content += '}'
    return content


def add_node(graph, element):
    if style[element.element_type]['plot'] and not element.is_common_definition:
        graph.node(
            element.id,
            create_attributes_string(element),
            **style[element.element_type]['format']
        )


def add_edges(graph, element):
    if style[element.element_type]['plot']:
        for referenced_element_type, references in style[element.element_type]['references'].items():
            if style[referenced_element_type]['plot']:
                for referenced_element in getattr(element, references):
                    if not referenced_element.is_common_definition:
                        graph.edge(element.id, referenced_element.id)
        for referenced_element_type, reference in style[element.element_type]['reference'].items():
            if style[referenced_element_type]['plot']:
                referenced_element = getattr(element, reference)
                if referenced_element:
                    if not referenced_element.is_common_definition:
                        graph.edge(element.id, referenced_element.id)


def create_graph(input_file, output_file):
    print("Loading File...")

    try:
        with openBw64Adm(input_file) as f:
            adm = f._parse_adm()
    except RuntimeError:
        adm = parse_file(input_file)

    print("Creating Graph...")
    graph = gv.Digraph(
        format='pdf',
        graph_attr=style['Graph']['format'],
        node_attr=style['ADMElement']['format'])

    # create nodes
    print("Adding audioProgrammes...")
    for programme in adm.audioProgrammes:
        add_node(graph, programme)
        add_edges(graph, programme)
    print("Adding audioContents...")
    for content in adm.audioContents:
        add_node(graph, content)
        add_edges(graph, content)
    print("Adding audioObjects...")
    for object in adm.audioObjects:
        add_node(graph, object)
        add_edges(graph, object)
    print("Adding audioTrackUIDs...")
    for trackUID in adm.audioTrackUIDs:
        add_node(graph, trackUID)
        add_edges(graph, trackUID)
    print("Adding audioPackFormats...")
    for packFormat in adm.audioPackFormats:
        add_node(graph, packFormat)
        add_edges(graph, packFormat)
    print("Adding audioStreamFormats...")
    for streamFormat in adm.audioStreamFormats:
        add_node(graph, streamFormat)
        add_edges(graph, streamFormat)
    print("Adding audioTrackFormats...")
    for trackFormat in adm.audioTrackFormats:
        add_node(graph, trackFormat)
        add_edges(graph, trackFormat)
    print("Adding audioChannelFormats...")
    for channelFormat in adm.audioChannelFormats:
        add_node(graph, channelFormat)
        add_edges(graph, channelFormat)

    print("Saving Graph...")
    graph.render(filename=output_file)


def parse_command_line():
    parser = argparse.ArgumentParser(description='EBU ADM Graph Tool')

    parser.add_argument('input_file')
    parser.add_argument('output_file')

    parser.add_argument('-d', '--debug',
                        help="print debug information when an error occurres",
                        action="store_true")

    args = parser.parse_args()
    return args


def main():
    args = parse_command_line()

    try:
        create_graph(args.input_file, args.output_file)
    except Exception as error:
        if args.debug:
            raise
        else:
            sys.exit(str(error))


if __name__ == '__main__':
    main()
