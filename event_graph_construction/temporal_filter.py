import os
import csv
import json
import copy
import logging
# import configargparse
import argparse

from math import ceil
from tqdm import tqdm
from queue import Queue
from datetime import datetime
from typing import List, Optional
from collections import defaultdict
from itertools import product


# def _get_validated_args(input_args: Optional[List[str]] = None):
#     parser = configargparse.ArgumentParser(
#         config_file_parser_class=configargparse.YAMLConfigFileParser
#     )

#     parser.add_argument("--input_cs", type=str, default="/shared/nas/data/m1/wen17/tmp/20201011_kairos_backpack_roadside_temporal_relation/temporal_relation.cs",
#                         help="The input file for temporal relations.")
#     parser.add_argument("--input_es_cs", type=str, default="None",
#                         help="The input file for Spanish temporal relations.")
#     parser.add_argument("--filtered_output_cs", type=str, default="./outputs/filtered_temporal_relation.cs",
#                         help="The output file for filtered temporal relations.")
#     parser.add_argument("--do_augmentation", action="store_true",
#                         help="Do relation augmentation (find the closure).")
#     parser.add_argument("--augmented_output_cs", type=str, default="/shared/nas/data/m1/wen17/tmp/20201011_kairos_backpack_roadside_temporal_relation/augmented_temporal_relation.cs",
#                         help="The output file for augmented temporal relations.")
#     parser.add_argument("--event_cs", type=str, default="/shared/nas/data/m1/tuanml2/kairos/output/backpack_roadside_ied/event.cs",
#                         help="The input file for cold start format events.")

#     args = parser.parse_args(input_args)
    
#     logging.basicConfig(format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
#                         datefmt="%m/%d/%Y %H:%M:%S",
#                         level=logging.INFO)
    
#     return args



def load_temporal_cs(input_cs):
    temporal_rels = []
    for line in open(input_cs):
        line = line.rstrip('\n')
        tabs = line.split('\t')
        if tabs[1] == "TEMPORAL_BEFORE":
            events = [tabs[0], tabs[2]]
        elif tabs[1] == "TEMPORAL_AFTER":
            events = [tabs[2], tabs[0]]
        else:
            continue
        confidence = float(tabs[3])
        temporal_rels.append([events, confidence])
    return temporal_rels


def remove_conflict_temporal_relations(temporal_rels):
    edges = defaultdict(list)
    def can_reach(x, y):
        vis.add(x)
        for edge in edges[x]:
            if edge == y:
                return True
            else:
                if not edge in vis:
                    is_reached = can_reach(edge, y)
                    if is_reached:
                        return True
        return False

    temporal_rels = sorted(temporal_rels, key=lambda x: x[1], reverse=True)
    final_temporal_rels = []
    for rel in tqdm(temporal_rels, total=len(temporal_rels)):
        vis = set()
        # Remove self loop
        if rel[0][1] == rel[0][0]:
            continue
        if (not can_reach(rel[0][1], rel[0][0])) and not (rel[0][1] in edges[rel[0][0]]):
            edges[rel[0][0]].append(rel[0][1])
            final_temporal_rels.append(rel)

    return final_temporal_rels

def augment_temporal_relations(temporal_rels):
    edges = defaultdict(set)
    inverse_edges = defaultdict(set)
    nodes = set()
    for rel in temporal_rels:
        edges[rel[0][0]].add(rel[0][1])
        inverse_edges[rel[0][1]].add(rel[0][0])
        nodes.add(rel[0][0])
        nodes.add(rel[0][1])
    for k in tqdm(nodes, total=len(nodes)):
        for i in inverse_edges[k]:
            if k in edges[i]:
                for j in edges[k]:
                    if not (j in edges[i]):
                        temporal_rels.append([[i, j], 0])
                        edges[i].add(j)
                        inverse_edges[j].add(i)
    return temporal_rels



def topological_sort(temporal_rels, nodes):
    edges = defaultdict(list)
    nodes = list(nodes)
    in_degree = defaultdict(int)
    for rel in temporal_rels:
        edges[rel[0][0]].append(rel[0][1])
        in_degree[rel[0][1]] += 1
    
    q = Queue()
    for node in nodes:
        if in_degree[node] == 0:
            q.put(node)
    
    sorted_event_ids = []
    while not q.empty():
        x = q.get()
        sorted_event_ids.append(x)
        for edge in edges[x]:
            in_degree[edge] -= 1
            if in_degree[edge] == 0:
                q.put(edge)
    return sorted_event_ids


def get_connected_components(sorted_event_ids, temporal_rels):
    edges = defaultdict(list)
    total_components = 0
    node_to_component_id = dict()
    components = []
    def find_component(x):
        vis.add(x)
        if x in node_to_component_id:
            return node_to_component_id[x]
        for edge in edges[x]:
            if not (edge in vis):
                component_id = find_component(edge)
                if component_id != -1:
                    return component_id
        return -1

    def set_component(x, component_id):
        vis.add(x)
        components[component_id].add(x)
        node_to_component_id[x] = component_id
        for edge in edges[x]:
            if not (edge in vis) and not (edge in node_to_component_id):
                set_component(edge, component_id)

    for rel in temporal_rels:
        edges[rel[0][0]].append(rel[0][1])
    for x in sorted_event_ids:
        vis = set()
        component_id = find_component(x)
        if component_id == -1:
            component_id = total_components
            components.append(set())
            total_components += 1
        vis = set()
        set_component(x, component_id)
    event_id_rank = dict()
    for i, event in enumerate(sorted_event_ids):
        event_id_rank[event] = i
    final_components = []
    for component in components:
        component = list(component)
        final_components.append(sorted(component, key=lambda x:event_id_rank[x]))
    return final_components


def load_event_cs(filename):
    events = defaultdict(dict)
    data = open(filename).readlines()
    for line in data:
        splits = line.strip("\n").split("\t")
        if splits[1] == "type":
            event_type = splits[2]
            event_id = splits[0]
            events[event_id]["type"] = event_type
            if not "arguments" in events[event_id]:
                events[event_id]["arguments"] = []
        else:
            if splits[1] == "canonical_mention.actual":
                event_id = splits[0]
                mention_text = splits[2].strip("\"")
                events[event_id]["mention_text"] = mention_text
            elif splits[2].startswith(":Entity_EDL"):
                event_id = splits[0]
                arg_role = splits[1]
                entity_id = splits[2]
                events[event_id]["arguments"].append({"role": arg_role, "id": entity_id})
    return events

def id_normalize(id_raw, language):
    return id_raw


def parse_offset_str(offset_str):
    doc_id = offset_str[:offset_str.rfind(':')]
    start = int(offset_str[offset_str.rfind(':') + 1:offset_str.rfind('-')])
    end = int(offset_str[offset_str.rfind('-') + 1:])
    return doc_id, start, end


def load_mention(tabs, info_dict, validate_offset, ltf_dir):
    offset = tabs[3]
    mention_type = tabs[1].replace(".actual", "")
    mention_confidence = float(tabs[4])
    mention_str = tabs[2][1:-1]
    doc_id, start, end = parse_offset_str(offset)
    # if validate_offset:
    #     doc_id, start, end = parse_offset_str(offset)
    #     mention_str_ltf = get_str_from_ltf(doc_id, start, end, ltf_dir)
    #     assert mention_str == mention_str_ltf
    if 'mention' not in info_dict:
        info_dict['mention'] = list()
    info_dict['mention'].append([mention_type, mention_str, doc_id, start, end])


def load_canonical_mention(tabs, info_dict, validate_offset, ltf_dir):
    offset = tabs[3]
    mention_type = tabs[1].replace(".actual", "")
    mention_confidence = float(tabs[4])
    mention_str = tabs[2][1:-1]
    doc_id, start, end = parse_offset_str(offset)
    # if validate_offset:
    #     doc_id, start, end = parse_offset_str(offset)
    #     mention_str_ltf = get_str_from_ltf(doc_id, start, end, ltf_dir)
    #     assert mention_str == mention_str_ltf
    # if 'mention' not in info_dict:
    #     info_dict['mention'] = list()
    info_dict["canonical_mention"] = [mention_type, mention_str, doc_id, start, end]


def get_events(filename, language='en'):
    logging.info("***** Loading events *****")

    evt_info = defaultdict(lambda : defaultdict())
    evt_args = defaultdict(lambda : defaultdict(lambda: defaultdict(list)))
    for line in open(filename):
        line = line.rstrip('\n')
        tabs = line.split('\t')
        if line.startswith('::Event'):
            evt_id = id_normalize(tabs[0], language)
            if tabs[1] == 'type':
                evt_info[evt_id]['type'] = tabs[2].split('#')[-1]
            elif 'canonical_mention' in tabs[1]:
                load_canonical_mention(tabs, evt_info[evt_id], False, None)
            elif 'mention' in tabs[1]:
                load_mention(tabs, evt_info[evt_id], False, None)    
            elif len(tabs) > 3 and ('Entity' in tabs[2] or 'Filler' in tabs[2]):
                role = tabs[1].split('#')[-1].replace(".actual", "") # no other label than ".actual" for now
                arg_id = id_normalize(tabs[2], language)
                arg_offset = tabs[3]
                doc_id, start, end = parse_offset_str(arg_offset)
                arg_confidence = float(tabs[4])
                evt_args[evt_id][role][arg_id].append( (doc_id, start, end, arg_confidence) )
            elif len(tabs) > 2 and tabs[1].startswith('t') and len(tabs[1]) == 2:
                # t_num = tabs[1]
                # date = tabs[2]
                # # for event_id, t_num, date in four_tuples:
                # num = int(t_num[1:]) - 1
                # # if "inf" not in date:
                # #     date = convert_data_gdate(date)
                # # else:
                # #     if num < 3:
                # #         date = convert_data_gdate("_9999-01-01")
                # #     else:
                # #         date = convert_data_gdate("9999-12-31")
                # date = convert_data_date(date)
                # if 'time' not in evt_info[evt_id]: 
                #     evt_info[evt_id]['time'] = [None, None, None, None]
                # evt_info[evt_id]['time'][num] = date
                pass
    return evt_info, evt_args


def main(input_args: Optional[List[str]] = None):
    # args = _get_validated_args(input_args)
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_cs", type=str, default="/shared/nas/data/m1/wen17/tmp/20201011_kairos_backpack_roadside_temporal_relation/temporal_relation.cs",
                        help="The input file for temporal relations.")
    parser.add_argument("--input_es_cs", type=str, default="None",
                        help="The input file for Spanish temporal relations.")
    parser.add_argument("--filtered_output_cs", type=str, default="./outputs/filtered_temporal_relation.cs",
                        help="The output file for filtered temporal relations.")
    parser.add_argument("--do_augmentation", action="store_true",
                        help="Do relation augmentation (find the closure).")
    parser.add_argument("--augmented_output_cs", type=str, default="/shared/nas/data/m1/wen17/tmp/20201011_kairos_backpack_roadside_temporal_relation/augmented_temporal_relation.cs",
                        help="The output file for augmented temporal relations.")
    parser.add_argument("--event_cs", type=str, default="/shared/nas/data/m1/tuanml2/kairos/output/backpack_roadside_ied/event.cs",
                        help="The input file for cold start format events.")
    args = parser.parse_args()


    temporal_rels = load_temporal_cs(input_cs=args.input_cs)

    if args.input_es_cs != "None":
        logging.info("Loading Spanish")
        es_temporal_rels = load_temporal_cs(input_cs=args.input_es_cs)
        # TODO: Try more confidence adjustment for English and Spanish
        temporal_rels = temporal_rels + es_temporal_rels

    # temporal_rels_cleanup
    logging.info(f"Before filter: {len(temporal_rels)}")
    temporal_rels = remove_conflict_temporal_relations(temporal_rels=temporal_rels)
    logging.info(f"After filter: {len(temporal_rels)}")
    f = open(args.filtered_output_cs, "w")
    results = ""
    for [event_i, event_j], confidence in temporal_rels:
        f.write("".join([event_i, "\t", "TEMPORAL_BEFORE", "\t", event_j, "\t", str(min(confidence,1.0)), "\n"]))
        results += "".join([event_i, "\t", "TEMPORAL_BEFORE", "\t", event_j, "\t", str(min(confidence,1.0)), "\n"])


    if args.do_augmentation:
        results = ""
        temporal_rels = augment_temporal_relations(temporal_rels=temporal_rels)
        logging.info(f"After Augment: {len(temporal_rels)}")
        f = open(args.augmented_output_cs, "w")
        for [event_i, event_j], confidence in temporal_rels:
            f.write("".join([event_i, "\t", "TEMPORAL_BEFORE", "\t", event_j, "\t", str(confidence), "\n"]))
            results += "".join([event_i, "\t", "TEMPORAL_BEFORE", "\t", event_j, "\t", str(confidence), "\n"])
        # temporal_rels = remove_conflict_temporal_relations(temporal_rels=temporal_rels)
        # print(f"After filter: {len(temporal_rels)}")
        f.close()
    return results

def post_processing_main(input_args: Optional[List[str]] = None):
    return main(input_args)

if __name__ == "__main__":
    main()