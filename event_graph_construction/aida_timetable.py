import argparse
import os
import re

def get_date(text):
    pattern_date = re.compile('[0-9]{4}-[0-9]{2}-[0-9]{2}')

    date_match = pattern_date.search(text)
    if date_match: # if line.startswith('--------------'):
        # date line
        return date_match.group()
    else:
        return None

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('rsd_dir', type=str, default='/shared/nas/data/m1/manling2/ibm/graph_sum_text/data/timeline17/oneie_input', help='input_dir')
    args = parser.parse_args()
    rsd_dir = args.rsd_dir

    with open(rsd_dir+'.timetable.tab', 'w') as writer:
        writer.write('%s\t%s\n' % ('docid', 'date')) 
        for rsd_file in os.listdir(rsd_dir):
            # print(rsd_file)
            date = get_date(rsd_file)
            # print(date)
            writer.write('%s\t%s\n' % (rsd_file, date)) 