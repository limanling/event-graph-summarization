import os
import glob
import json
import requests
from os.path import join
import argparse
import shutil

BASE_PATH = '.'

def read_data(json_file):
    f = open(json_file, 'r')
    data = f.read()
    f.close()
    return data

def save_json_format(entity_cs_file, event_cs_file, relation_cs_file,
    json_file_dir, edl_cs_file, edl_tab_file, ltf_dir):
    data = {
        "oneie": {
            "en": {
                "cs": {
                    "entity": "",
                    "event": "",
                    "relation": ""
                },
                "json": {}
            },
            "es": {
                "cs": {
                    "entity": "",
                    "event": "",
                    "relation": ""
                },
                "json": {}
            }
        },
        "edl": {
            "en": {
                "cs": "",
                "tab": ""
            },
            "es": {
                "cs": "",
                "tab": ""
            }
        },
        "coref": {},
        "temporal_relation": {},
        "translation": {},
        "graph_g": "",
        "ext": {
            "en": "{}",
            "es": "{}"
        },
        "matching": {},
        "data": {
            "en": [],
            "es": []
        },
        "relation_enrichment": ""
    }
    # data = dict()

    # # oneie
    # data['oneie']['en']['bio']['nam'] = open(bio_nam_file).read()
    # data['oneie']['en']['bio']['nam+nom+pro'] = open(bio_all_file).read()
    # data['oneie']['en']['bio']['nom'] = open(bio_nom_file).read()
    # data['oneie']['en']['bio']['pro'] = open(bio_pro_file).read()
    # data['oneie']['en']['cfet'] = open(cfet_file).read()
    data['oneie']['en']['cs']['entity'] = open(entity_cs_file).read()
    data['oneie']['en']['cs']['event'] = open(event_cs_file).read()
    data['oneie']['en']['cs']['relation'] = open(relation_cs_file).read()
    # data['oneie']['en']['json'] = dict()
    for json_file in os.listdir(json_file_dir):
        data['oneie']['en']['json'][json_file] = open(os.path.join(json_file_dir, json_file)).read()
    # data['oneie']['en']['tab']['nam'] = open(tab_nam_file).read()
    # data['oneie']['en']['tab']['nam+nom+pro'] = open(tab_all_file).read()
    # data['oneie']['en']['tab']['nom'] = open(tab_nom_file).read()
    # data['oneie']['en']['tab']['pro'] = open(tab_pro_file).read()

    # edl
    data['edl']['en']['cs'] = open(edl_cs_file).read()
    data['edl']['en']['tab'] = open(edl_tab_file).read()

    # ltf data
    for ltf_file in os.listdir(ltf_dir):
        ltf_content = open(os.path.join(ltf_dir, ltf_file)).read()
        data['data']['en'].append(ltf_content)
    
    return data


def clean_event_cs(event_cs_str):
    lines = list()
    # revise the event id
    event_cs_str = event_cs_str.replace('::Event', ':Event')
    # remove `modality`
    for line in event_cs_str.split('\n'):
        if 'modality' not in line:
            lines.append(line)
    return '\n'.join(lines)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('input_dir', type=str, help='The dataset directory.')
    parser.add_argument('port', type=str, help='The port.')
    args = parser.parse_args()
    input_dir = args.input_dir
    port = args.port
    # input_dir = '/shared/nas/data/m1/manling2/ibm/graph_sum_text/data/timeline17/oneie_timeline'

    entity_cs_file = os.path.join(input_dir, 'merge/cs/entity.cs')
    event_cs_file = os.path.join(input_dir, 'merge/cs/event.cs')
    relation_cs_file = os.path.join(input_dir, 'merge/cs/relation.cs')
    json_file_dir = os.path.join(input_dir, 'merge/json')
    edl_cs_file = os.path.join(input_dir, 'edl/en.linking.cs')
    edl_tab_file = os.path.join(input_dir, 'edl/en.linking.tab')
    ltf_dir = os.path.join(input_dir, 'ltf')
    output_file = os.path.join(input_dir, 'coref.txt')
    output_file_entity = os.path.join(input_dir, 'entity_coref.cs')
    output_file_relation = os.path.join(input_dir, 'relation_coref.cs')
    output_file_event = os.path.join(input_dir, 'event_coref.cs')

    # input_data = read_data('./sample_input.json')
    # input_data = json.loads(input_data)
    input_data = save_json_format(entity_cs_file, event_cs_file, relation_cs_file,
        json_file_dir, edl_cs_file, edl_tab_file, ltf_dir)
    response = requests.post('http://localhost:%s/process' % port, json={'data': input_data})
    with open(output_file, 'w') as f:
        f.write(response.text)
    ans = json.loads(response.text)
    with open(output_file_entity, 'w') as f:
        f.write(ans['entity.cs'])
    with open(output_file_relation, 'w') as f:
        f.write(ans['relation.cs'])
    with open(output_file_event, 'w') as f:
        f.write(clean_event_cs(ans['event.cs']))

    # # rewrite event_corefer.cs
    # for event_corefer_file in glob.glob('/shared/nas/data/m1/manling2/ibm/graph_sum_text/data/timeline17/oneie_input/*/event_coref.cs'):
    #     # remove the modality line
    #     event_corefer_string = open(event_corefer_file).read()
    #     with open(event_corefer_file.replace('.cs', '_fix.cs'), 'w') as f:
    #         f.write(clean_event_cs(event_corefer_string))


# KAIROS_LIB=/shared/nas/data/m1/manling2/aida_docker_test/ta2-pipeline-local/output