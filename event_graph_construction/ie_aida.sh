data_root=$1
export CUDA_VISIBLE_DEVICES=$2
# data_root="/shared/nas/data/m1/manling2/ibm/graph_sum_text/data/timeline17/oneie_timeline"
ltf_source=${data_root}/ltf
rsd_source=${data_root}/rsd
parent_child_tab_path=${data_root}/parent_children.tab
lang="en"

rsd_file_list=${data_root}/rsd_lst
core_nlp_output_path=${data_root}/corenlp
edl_tab_nam_filename=${lang}.nam.tab
edl_tab_nom_filename=${lang}.nom.tab
edl_tab_pro_filename=${lang}.pro.tab
edl_output_dir=${data_root}/edl
edl_tab_link=${edl_output_dir}/${lang}.linking.tab
edl_tab_link_fb=${edl_output_dir}/${lang}.linking.freebase.tab
edl_tab_final=${edl_output_dir}/merged_final.tab
edl_cs_coarse=${edl_output_dir}/merged.cs
edl_cs_oneie=${data_root}/merge/cs/entity.cs
filler_coarse=${edl_output_dir}/filler_${lang}.cs
filler_coarse_color=${edl_output_dir}/filler_${lang}_all.cs
relation_cs_oneie=${data_root}/merge/cs/relation.cs # final cs output for relation
relation_result_dir=${data_root}/relation   # final cs output file path
relation_cs_coarse=${relation_result_dir}/${lang}.rel.cs # final cs output for relation
new_relation_coarse=${relation_result_dir}/new_relation_${lang}.cs
event_result_dir=${data_root}/event
event_coarse_oneie=${data_root}/merge/cs/event.cs
event_coarse_without_time=${event_result_dir}/event_rewrite.cs
event_corefer=${data_root}/event_coref.cs
event_corefer_idfix=${data_root}/event_coref_idfix.cs
event_corefer_time=${data_root}/event_coref_timenorm.cs
event_corefer_timesimple=${data_root}/event_coref_timesimple.cs
event_corefer_timeorder=${data_root}/event_order.cs
event_corefer_timeorder_filter=${data_root}/event_order_filter.cs
entity_corefer=${data_root}/entity_coref.cs
merged_cs=${data_root}/${lang}${source}_full.cs
timetable_tab=${data_root}/rsd.timetable.tab

# oneie
docker run --rm -i -v ${data_root}:${data_root} -w /oneie --gpus device=$2 limteng/oneie_aida_m36 \
    /opt/conda/bin/python \
    /oneie/predict.py -i ${ltf_source} -o ${data_root} -l ${lang}



# # stanford nlp
docker run --rm -v ${data_root}:${data_root} -w `pwd` -i limanling/uiuc_ie_m36 \
    /opt/conda/envs/py36/bin/python \
    /aida_utilities/dir_readlink.py ${rsd_source} ${rsd_file_list} 
python aida_timetable.py ${rsd_source}
docker run --rm -v ${data_root}:${data_root} -w /stanford-corenlp-aida_0 -i limanling/aida-tools \
    java -mx50g -cp '/stanford-corenlp-aida_0/*' edu.stanford.nlp.pipeline.StanfordCoreNLP \
    $* -annotators 'tokenize,ssplit,pos,lemma,ner' \
    -outputFormat json \
    -filelist ${rsd_file_list} \
    -ner.docdate.useMappingFile ${timetable_tab} \
    -properties StanfordCoreNLP_${lang}.properties \
    -outputDirectory ${core_nlp_output_path}

# # echo "** Linking entities to KB **"
wget http://159.89.180.81/demo/resources/edl_data.tar.gz -P ./data
tar zxvf ./data/edl_data.tar.gz -C ./data
docker run -d --rm -v ${PWD}/edl_data/db:/data/db --name db mongo:4.2
docker run -v ${PWD}/edl_data:/data \
    -v ${data_root}:/testdata_${lang} \
    --link db:mongo panx27/edl \
    python ./projs/docker_aida19/aida19.py \
    ${lang} \
    /testdata_${lang}/merge/mention/${edl_tab_nam_filename} \
    /testdata_${lang}/merge/mention/${edl_tab_nom_filename} \
    /testdata_${lang}/merge/mention/${edl_tab_pro_filename} \
    /testdata_${lang}/edl \
    m36

# # coreference
python event_coref_cross.py ${data_root} 22222

## rewrite relation and event
docker run --rm -v ${data_root}:${data_root} -i limanling/uiuc_ie_m36 \
    /opt/conda/envs/py36/bin/python \
    /aida_utilities/rewrite_entity_id.py \
    ${edl_cs_oneie} ${relation_cs_oneie} ${event_coarse_oneie} \
    ${entity_corefer} ${relation_cs_coarse} ${event_coarse_without_time}

# temporal order
docker run --rm -v ${data_root}:${data_root} --gpus device=$2  -w /roberta_temporal_relation -i wenhycs/uiuc_kairos_temporal_relation \
    python kairos_temporal_relation_pipeline.py \
    --ltf_path ${ltf_source} \
    --event_cold_start_filename ${event_corefer} \
    --output_filename ${event_corefer_timeorder} \
    --add_sharing_arg

python temporal_filter.py \
    --input_cs ${event_corefer_timeorder} --filtered_output_cs ${event_corefer_timeorder_filter}

# # Filler Extraction & new relation
docker run --rm -v ${data_root}:${data_root} -i limanling/uiuc_ie_m36 \
    /opt/conda/envs/py36/bin/python \
    /entity/aida_filler/extract_filler_relation.py \
    --corenlp_dir ${core_nlp_output_path} \
    --ltf_dir ${ltf_source} \
    --edl_path ${entity_corefer} \
    --text_dir ${rsd_source} \
    --path_relation ${new_relation_coarse} \
    --path_filler ${filler_coarse} \
    --lang ${lang}

## Add time expression
python time_expression.py \
    ${ltf_source} ${filler_coarse} ${event_corefer} ${event_corefer_timesimple}

# 4-tuple
docker run -i --rm -v ${data_root}:${data_root} \
    -v ${parent_child_tab_path}:${parent_child_tab_path} \
    -w /EventTimeArg --gpus device=$2 wenhycs/uiuc_event_time \
    python aida_event_time_pipeline.py \
    --time_cold_start_filename ${filler_coarse} \
    --event_cold_start_filename ${event_corefer} \
    --read_cs_event \
    --parent_children_filename ${parent_child_tab_path} \
    --ltf_path ${ltf_source} \
    --output_filename ${event_corefer_time} \
    --use_dct_as_default \
    --lang ${lang}


