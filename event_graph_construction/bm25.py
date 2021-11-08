from dateutil import parser
import dateutil
import os
import ujson as json
import sys

from gensim.summarization.bm25 import BM25

from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.tokenize import sent_tokenize

from datetime import *

from collections import OrderedDict, defaultdict

def get_dates_timeline(timeline_file, timeline_output):
    # find date range of input timeline
    min_date = date.today()
    max_date = date(1800, 1, 1)
    date_num = 0
    date_last = date.today()
    timeline_writer = open(timeline_output.replace(' ','_'), 'w')
    for line in open(timeline_file):
        line = line.rstrip()
        if line.startswith('Our Standards:') or 'Min Read' in line or '</body>' == line or '<body>' == line or line.startswith('<title>') or line.startswith('By Reuters Staff') or line.startswith('Reporting by '):
            continue
        if ':' in line[:30]:
            date_str = line.split(':')[0]
        elif '- ' in line[:30]:
            date_str = line.split('-')[0]
        elif '– ' in line[:30]:
            date_str = line.split('–')[0]
        elif ' (' in line[:30]:
            date_str = line.split('(')[0]
        elif len(line) < 20:
            date_str = line
        # elif line.startswith('On '):
        else:
            date_str = ''
            # # print(line)
            # continue
        if 'Min Read' in date_str or '</body>' in date_str or '<body>' in date_str:
            continue
        
        if len(date_str) > 0:
            date_str_raw = date_str
            try:
                date_str = date_str.strip().split('(')[0].replace('On ', '').split(' to')[0]
                d = parser.parse(date_str, default=date_last, fuzzy=True, fuzzy_with_tokens=False)
                date_last = d
                if len(date_str) == 4:
                    # save year info, but delete this row
                    continue
                # print(d, date_last)
                # d = d.datetime.date()
                # print('aaaa', d, d.year, date_last)
                # d= datetime.date(d.strftime("%Y-%m-%d"))
                if min_date > d:
                    min_date = d
                if max_date < d:
                    max_date = d  
                date_num += 1
                timeline_writer.write('--------------------------------\n')
                timeline_writer.write(d.strftime("%Y-%m-%d"))
                timeline_writer.write('\n')
                content_str = line.replace(date_str_raw, '').strip('-').strip(':').strip()
                if len(content_str) > 0:
                    timeline_writer.write('\n'.join(sent_tokenize(content_str)))
                    timeline_writer.write('\n')
            except:
                try:
                    date_str = date_str.split(',')[-1]
                    d = parser.parse(date_str, default=date_last, fuzzy=True, fuzzy_with_tokens=False)
                    date_last = d
                    if len(date_str) == 4:
                        # save year info, but delete this row
                        continue
                    # print(d, date_last)
                    # d = d.datetime.date()
                    # print('aaaa', d, d.year, date_last)
                    # d= datetime.date(d.strftime("%Y-%m-%d"))
                    if min_date > d:
                        min_date = d
                    if max_date < d:
                        max_date = d  
                    date_num += 1
                    timeline_writer.write('--------------------------------\n')
                    timeline_writer.write(d.strftime("%Y-%m-%d"))
                    timeline_writer.write('\n')
                    content_str = line.replace(date_str_raw, '').strip('-').strip(':').strip()
                    if len(content_str) > 0:
                        timeline_writer.write('\n'.join(sent_tokenize(content_str)))
                        timeline_writer.write('\n')
                except: #dateutil.parser._parser.ParserError:
                    # print('CANNOT PARSE DATE', date_str)
                    # pass
                    # print(sys.exc_info())
                    content_str = line.strip('-').strip(':').strip()
                    if len(content_str) > 0:
                        timeline_writer.write('\n'.join(sent_tokenize(content_str)))
                        timeline_writer.write('\n')
        else:
            content_str = line.strip('-').strip(':').strip()
            if len(content_str) > 0:
                timeline_writer.write('\n'.join(sent_tokenize(content_str)))
                timeline_writer.write('\n')
    # Timeline of Paris attacks and investigation_idUSKBN0TB0XZ20151122.txt
    return min_date, max_date, date_num

def rewrite_tl(timeline_input, timeline_output):
    for timeline_file in os.listdir(timeline_input):
        timeline_content = open(os.path.join(timeline_input, timeline_file)).read()
        timeline_content = timeline_content[timeline_content.find('---\n') + 4:]
        with open(os.path.join(timeline_output, timeline_file), 'w') as writer:
            writer.write(timeline_content)


def get_datestr(date):
    # print(d.strftime("%Y-%m-%d")) #"%Y-%m-%d %H:%M:%S"))
    return date.strftime("%Y-%m-%d")

# get the input candidates of that time period
def get_candidate(min_date, max_date, all_doc, all_doc_date_sorted):
    corpus = []
    corpus_id = []

    min_date_ext = min_date - timedelta(days = 15)
    max_date_ext = max_date + timedelta(days = 15)

    min_date_ext = min_date_ext.strftime("%Y-%m-%d")
    max_date_ext = max_date_ext.strftime("%Y-%m-%d")

    for date_doc in all_doc_date_sorted:
        if date_doc >= min_date_ext and date_doc <= max_date_ext:
            for doc_path in all_doc[date_doc]:
                if 'voa_v2_processed' in doc_path:
                    corpus.append(open(doc_path).read().strip('\n'))
                elif 'voa_v1_processed' in doc_path:
                    corpus.append(open(doc_path).readlines()[0].rstrip('\n'))
                # corpus.append(open(doc_path).read())#os.path.join(all_doc_dir, doc_id)))
            corpus_id.extend(all_doc[date_doc])
        if date_doc > max_date_ext:
            break

    return corpus, corpus_id

def get_all_doc_voa_v1(all_doc_dir, all_doc_list, doc_date_dict):
    for doc_id in os.listdir(all_doc_dir):
        if doc_id.startswith('.'):
            continue
        # VOA_EN_NW_2009_11_01_406231_0.rsd
        date_year = doc_id[10:14]
        date_month = doc_id[15:17]
        date_day = doc_id[18:20]
        # print(doc_id, date_year, date_month, date_day)
        date_doc = date(int(date_year), int(date_month), int(date_day))
        date_doc = date_doc.strftime("%Y-%m-%d")
        if date_doc not in all_doc_list:
            all_doc_list[date_doc] = list()
        all_doc_list[date_doc].append(os.path.join(all_doc_dir, doc_id))
        doc_date_dict[os.path.join(all_doc_dir, doc_id)] = date_doc
    # all_doc_date_sorted = sorted(all_doc_list)
    # json.dump(all_doc_date_sorted, open('/shared/nas/data/m1/manling2/ibm/graph_sum_text/src/timeline/dataset/all_doc_date_sorted_v1.json', 'w'), indent=4)
    return all_doc_list, doc_date_dict

def get_all_doc_voa_v2(all_doc_head_dir, all_doc_list, doc_date_dict):
    for area in os.listdir(all_doc_head_dir):
        if area.startswith('.'):
            continue
        for doc_id in os.listdir(os.path.join(all_doc_head_dir, area, 'head_rsd')):
            if doc_id.startswith('.'):
                continue
            if doc_id.startswith('VOA_ENG_NW_None'):
                continue
            if doc_id.startswith('VOA_ENG_NW_'):
                doc_id_clean = doc_id.replace('VOA_ENG_NW_', 'VOA_ENG_NW.')
                tabs = doc_id_clean.split('.')
            else:
                # VOA_ENG_NW.12.10.2019.309_head.rsd.txt
                tabs = doc_id.split('.')
                # print(tabs)
            date_year = tabs[3]
            date_month = tabs[1]
            date_day = tabs[2]
            # print(doc_id, date_year, date_month, date_day)
            date_doc = date(int(date_year), int(date_month), int(date_day))
            date_doc = date_doc.strftime("%Y-%m-%d")
            if date_doc not in all_doc_list:
                all_doc_list[date_doc] = list()
            all_doc_list[date_doc].append(os.path.join(all_doc_head_dir, area, 'head_rsd', doc_id))
            doc_date_dict[os.path.join(all_doc_head_dir, area, 'head_rsd', doc_id)] = date_doc
    # all_doc_date_sorted = sorted(all_doc_list)
    # json.dump(all_doc_date_sorted, open('/shared/nas/data/m1/manling2/ibm/graph_sum_text/src/timeline/dataset/all_doc_date_sorted.json', 'w'), indent=4)
    return all_doc_list, doc_date_dict

# use BM25 to rank the candidates
stop_words = set(stopwords.words('english'))
def simple_tok(sent):
    # return sent.split()
 
    word_tokens = word_tokenize(sent)
 
    filtered_sent = [w for w in word_tokens if not w.lower() in stop_words]
    
    return filtered_sent

def bm25(corpus, corpus_ids, query, output_dir, doc_date_dict, timeline_name, topk=300):
    if len(corpus) == 0:
        return list(), list()
    # for s in corpus:
    #     print(s)
    # print('corpus', len(corpus))
    tok_corpus = [simple_tok(s) for s in corpus] # [s.split(" ") for s in corpus] #
    # print('tok_corpus', len(tok_corpus), corpus_ids[0], tok_corpus[0])
    bm25 = BM25(tok_corpus)
    tok_query = simple_tok(query) #query.split()
    scores = bm25.get_scores(tok_query)

    best_docs = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)#[:topk]
    best_docs_ids = list()
    best_docs_content = defaultdict()
    # print('corpus_ids', len(corpus_ids))
    for i, b in enumerate(best_docs):
        # print(b, len(corpus_ids))
        # print(f"rank {i+1}: {corpus_ids[b]}")
        score = scores[b]
        best_docs_ids.append(corpus_ids[b])
        best_docs_content[corpus_ids[b]] = (scores[b], corpus[b])
        dock_id = corpus_ids[b].split('/')[-1].replace('head_rsd', 'article_rsd').replace(' ','_')
        if score >= 100:
            os.makedirs(os.path.join(output_dir, timeline_name.replace(' ','_'), doc_date_dict[corpus_ids[b]]), exist_ok=True)
            with open(os.path.join(output_dir, timeline_name.replace(' ','_'), doc_date_dict[corpus_ids[b]],  dock_id), 'w') as writer:
                content_path = corpus_ids[b].replace('_head.rsd.txt', '.rsd.txt').replace('head_rsd', 'article_rsd')
                try:
                    content_str = open(content_path).read()
                    writer.write('\n'.join(sent_tokenize(content_str)))
                except:
                    print('cannot find file', content_path)
    return best_docs_ids, best_docs_content


if __name__ == '__main__':
    input_timeline = '/shared/nas/data/m1/manling2/ibm/graph_sum_text/data/timeline/cleaned'
    input_doc_dir_v1 = '/shared/nas/data/m1/manling2/mmqa/data/voa_v1_processed/article/rsd'
    input_doc_head_dir_v2 = '/shared/nas/data/m1/manling2/mmqa/data/voa_v2_processed'
    output_dir = '/shared/nas/data/m1/manling2/ibm/graph_sum_text/data/timeline/bm25_merge'
    output_timline_std = '/shared/nas/data/m1/manling2/ibm/graph_sum_text/data/timeline/clean_format'
    output_input_std = '/shared/nas/data/m1/manling2/ibm/graph_sum_text/data/timeline/input_format'
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(output_timline_std, exist_ok=True)
    os.makedirs(output_timline_std+'_tmp', exist_ok=True)
    os.makedirs(output_input_std, exist_ok=True)

    # timeline_file = 'A Timeline of Major Attacks in Kabul Over the Last Year .rsd.txt'

    # get_dates_timeline(os.path.join(input_timeline, timeline_file))
    all_doc_list = dict()
    doc_date_dict = dict()
    all_doc_list, doc_date_dict = get_all_doc_voa_v1(input_doc_dir_v1, all_doc_list, doc_date_dict)
    print('all_doc_list', len(all_doc_list))
    all_doc_list, doc_date_dict = get_all_doc_voa_v2(input_doc_head_dir_v2, all_doc_list, doc_date_dict)
    print('all_doc_list', len(all_doc_list))
    all_doc_date_sorted = sorted(all_doc_list)
    json.dump(all_doc_date_sorted, open('/shared/nas/data/m1/manling2/ibm/graph_sum_text/src/timeline/dataset/all_doc_date_sorted_merge.json', 'w'), indent=4)
    

    valid_timeline = list()
    for timeline_file in os.listdir(input_timeline):
        if timeline_file.startswith('.'):
            continue
        min_date, max_date, date_num = get_dates_timeline(os.path.join(input_timeline, timeline_file), os.path.join(output_timline_std+'_tmp', timeline_file))
        rewrite_tl(output_timline_std+'_tmp', output_timline_std)
        date_difference = (max_date - min_date).days
        print(timeline_file, date_difference, date_num)

        # if date_num < 7:
        #     continue
        if date_difference > 1000:
            continue
        # valid_timeline.append(timeline_file)  # 64

        corpus, corpus_id = get_candidate(min_date, max_date, all_doc_list, all_doc_date_sorted)
        print('candidate_size', min_date, max_date, len(corpus_id))
        if len(corpus_id) < 5:
            continue
        query = open(os.path.join(input_timeline, timeline_file)).read()
        best_docs_ids, best_docs_content = bm25(corpus, corpus_id, query, output_input_std, doc_date_dict, timeline_file, topk=date_num*30)
        # print(timeline_file, len(best_docs_ids), best_docs_ids)
        json.dump(best_docs_content, open(os.path.join(output_dir, timeline_file+'bm25.json'), 'w'), indent=4)

        valid_timeline.append(timeline_file)

        # break

        
    print('valid_timeline', len(valid_timeline))