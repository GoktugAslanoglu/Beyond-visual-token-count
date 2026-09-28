"""Independent CPU reconstruction of sources, storage, rendering and tensors."""
import argparse
import math
import gc
from pathlib import Path
from collections import Counter
from PIL import Image,ImageChops
from experiment_common import ROOT,REPO,LEGACY,CONFIG,read,put,sha,digest,load_processor,text_count,chat,tensor_check,plan,render
from build_cases import make_cases
from storage import pack,decode_compact
from experiment_common import empty_question_counter

def validate(split,assets=None,report_path=None):
    processor=load_processor(assets);manifest_path=ROOT/('manifest.json' if split=='eval' else f'manifest_{split}.json')
    model_config=read(Path(assets or ROOT/'assets/GLM')/'config.json')
    empty_count=empty_question_counter(processor)
    manifest=read(manifest_path);cases={c['id']:c for c in make_cases(split)}
    expected={(case_id,arm) for case_id in cases for arm in CONFIG['arms']};keys=[(r['case_id'],r['arm']) for r in manifest['rows']]
    assert len(keys)==len(set(keys)) and set(keys)==expected
    assert len(set(CONFIG['seeds'].values()))==len(CONFIG['seeds'])
    image_count=0;seen_sources=set();excluded_sources=set();excluded_paths=[]
    # Corpus membership checks use source content only; never old model answers.
    for other_split in ['dev','eval','smoke']:
        if other_split!=split: excluded_paths.extend((ROOT/'cases'/other_split).glob('final-*.json'))
    historic=REPO/'final_iclr/final_followups/checkpoints/cpu_1790114103802037991/prepared/01_budget_crossover/cases'
    excluded_paths.extend(historic.glob('cross-*.json'))
    for path in excluded_paths: excluded_sources.add(digest(read(path)['memory']))
    historical_hashes=read(ROOT/'environment/HISTORICAL_SOURCE_HASHES.json')
    assert historical_hashes['count']==len(historical_hashes['rows'])==90
    excluded_sources.update(h['source_sha256'] for h in historical_hashes['rows'])
    from fontTools.ttLib import TTFont
    with TTFont(str(LEGACY/'assets/DejaVuSansMono.ttf'),lazy=True) as face: supported=set(face.getBestCmap())
    for case_id,case in cases.items():
        assert case==read(ROOT/'cases'/split/(case_id+'.json'))
        assert case['memory']=='\n'.join(case['records']) and case['memory'].count(case['target_record'])==1
        assert case['memory'].count(case['reference'])==1 and len(set(case['records']))==len(case['records'])
        assert digest(case['memory']) not in excluded_sources
        assert all(ord(c) in supported for c in case['memory'] if c!='\n')
        if split=='eval': assert case['seed'] not in [CONFIG['seeds']['development'],CONFIG['seeds']['smoke']]
        assert case['memory'] not in seen_sources;seen_sources.add(case['memory'])
    for row in manifest['rows']:
        folder=ROOT/row['path'];case=cases[row['case_id']];arm=row['arm']
        assert sha(folder/'REQUEST.json')==row['request_sha256'] and sha(folder/'MEASUREMENT.json')==row['measurement_sha256']
        request=read(folder/'REQUEST.json');measured=read(folder/'MEASUREMENT.json')
        assert not {'reference','target_record','target_key','answer'} & set(request)
        assert request['case_id']==case['id'] and request['arm']==arm and request['question']==case['question']
        assert request['source_sha256']==sha(ROOT/'cases'/split/(case['id']+'.json'))
        indices=request['diagnostics']['stored_indices']
        assert request['diagnostics']=={'target_included':case['target_record'] in [case['records'][i] for i in indices],
            'records_retained':len(indices),'source_records':len(case['records']),'stored_indices':indices,'stored_source_sha256':digest(request['memory'])}
        if arm=='optical':
            g=plan(case['memory'],CONFIG['layout']);images=render(g,CONFIG['side'])
            assert request['geometry']['layout']==g and indices==list(range(len(case['records'])))
            assert request['memory']==case['memory'] and len(images)==CONFIG['pages']
            for index,image in enumerate(images):
                with Image.open(folder/request['images'][index]) as saved:
                    assert saved.mode=='RGB' and saved.size==image.size and saved.tobytes()==image.tobytes()
                assert sha(folder/request['images'][index])==request['geometry']['pages'][index]['image_sha256']
                bbox=ImageChops.difference(image,Image.new('RGB',image.size,'white')).getbbox()
                assert bbox and min(bbox[:2])>0 and bbox[2]<image.width and bbox[3]<image.height
                image_count+=1
            assert measured['vision_tokens']==CONFIG['vision_tokens']
        else:
            images=[];memory,rebuilt_indices=pack(case['records'],case['base_id'],empty_count,
                CONFIG['B'],CONFIG['query_reserve'],CONFIG['seeds']['retention'],arm=='compact_text')
            assert request['memory']==memory and indices==rebuilt_indices
            assert request['storage_empty_query_tokens']==text_count(processor,memory,'')
            assert text_count(processor,memory,'')+CONFIG['query_reserve']<=CONFIG['B']
            assert text_count(processor,memory,case['question'])-text_count(processor,memory,'')<=CONFIG['query_reserve']
            assert measured['vision_tokens']==0 and not request['images']
            if arm=='compact_text': assert decode_compact(memory)==[case['records'][i] for i in indices]
        rendered=chat(processor,request['memory'],case['question'],images);assert rendered==measured['rendered_chat']
        batch=processor(text=[rendered],images=images or None,return_tensors='pt',padding=False);tensor_check(batch,measured)
        actual_ids=batch['input_ids'][0].tolist()
        image_placeholders=sum(v==int(model_config['image_token_id']) for v in actual_ids)
        actual_grid=batch['image_grid_thw'].tolist() if images else []
        merged_grid=sum(math.prod(g)//int(processor.image_processor.merge_size)**2 for g in actual_grid)
        assert image_placeholders==merged_grid==measured['vision_tokens']
        assert actual_grid==measured['image_grid_thw']
        assert len(batch['input_ids'][0])==measured['total_input_tokens']<=CONFIG['B']
        assert measured['total_input_tokens']+CONFIG['max_new_tokens']<=measured['native_context_limit']
        assert request['accounting']=={k:measured[k] for k in request['accounting']}
        for image in images: image.close()
        del batch,images
        gc.collect()
        print('CPU validated',split,row['case_id'],arm,flush=True)
    positions=Counter(c['position'] for c in cases.values())
    if split=='eval': assert dict(positions)=={'early':50,'middle':50,'late':50}
    result={'status':'passed','split':split,'source_cases':len(cases),'inputs':len(keys),
        'heldout_inputs':len(keys) if split=='eval' else 0,'rendered_pages':image_count,'position_counts':dict(positions),
        'source_reconstruction':True,'storage_reconstruction':True,'processor_tensor_reconstruction':True,
        'storage_receives_future_query':False,'reference_or_key_annotations_in_requests':False,
        'source_span_preservation':True,'no_clipping':True,'seed_separation':True,'model_calls':0,
        'cross_split_and_historical_source_disjointness':True,'excluded_source_files':len(excluded_paths),
        'native_grid_placeholder_count':True,'fixed_query_reserve_validated':True,'font_glyph_coverage':True,
        'empty_question_total_tokens':text_count(processor,'',''),
        'available_fixed_storage_native_tokens':CONFIG['B']-text_count(processor,'','')-CONFIG['query_reserve'],
        'weights_loaded':False,'manifest_sha256':sha(manifest_path)}
    put(report_path or ROOT/'audit'/f'{split}_INPUT_AUDIT.json',result);return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--split',choices=['dev','eval','smoke'],required=True);p.add_argument('--assets',type=Path);p.add_argument('--report',type=Path)
    a=p.parse_args();validate(a.split,a.assets,a.report)
