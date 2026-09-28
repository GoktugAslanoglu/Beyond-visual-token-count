"""CPU native input materialization; never loads weights or generates answers."""
import argparse
from pathlib import Path
from PIL import Image,ImageChops
from experiment_common import ROOT,CONFIG,read,put,sha,digest,text_count,measure,plan,render,load_processor
from storage import pack,decode_compact
from experiment_common import empty_question_counter

def build(split,assets=None,case_index=None):
    assets=Path(assets or ROOT/'assets/GLM');processor=load_processor(assets);model_config=read(assets/'config.json')
    folder=ROOT/'inputs'/split
    if folder.exists() and case_index is None: raise FileExistsError('Immutable inputs already exist; use explicit CPU case worker')
    source_index=read(ROOT/'cases'/split/'INDEX.json');rows=[];empty_count=empty_question_counter(processor)
    for item in source_index['cases']:
        if case_index is not None and item not in source_index['cases'][case_index:case_index+3]: continue
        source_path=ROOT/'cases'/split/(item['id']+'.json');assert sha(source_path)==item['sha256']
        case=read(source_path);geometry=plan(case['memory'],CONFIG['layout']);representations={}
        # Commit BOTH text stores before accessing actual question or target diagnostics.
        for arm,compact in [('hash_text',False),('compact_text',True)]:
            memory,indices=pack(case['records'],case['base_id'],empty_count,
                CONFIG['B'],CONFIG['query_reserve'],CONFIG['seeds']['retention'],compact)
            if compact: assert decode_compact(memory)==[case['records'][i] for i in indices]
            representations[arm]=(memory,indices)
        for arm in CONFIG['arms']:
            dest=folder/case['id']/arm;dest.mkdir(parents=True)
            images=render(geometry,CONFIG['side']) if arm=='optical' else []
            memory,indices=(case['memory'],list(range(len(case['records'])))) if images else representations[arm]
            measured=measure(processor,model_config,memory,case['question'],images)
            assert measured['total_input_tokens']<=CONFIG['B']
            assert measured['total_input_tokens']+CONFIG['max_new_tokens']<=measured['native_context_limit']
            assert measured['vision_tokens']==(CONFIG['vision_tokens'] if images else 0)
            page_meta=[]
            for page,image in enumerate(images):
                bbox=ImageChops.difference(image,Image.new('RGB',image.size,'white')).getbbox()
                assert bbox and min(bbox[:2])>0 and bbox[2]<image.width and bbox[3]<image.height
                image.save(dest/f'page_{page:03}.png');page_meta.append({'ink_bbox':bbox,'image_sha256':sha(dest/f'page_{page:03}.png')})
            diagnostic={'target_included':case['target_record'] in [case['records'][i] for i in indices],
                'records_retained':len(indices),'source_records':len(case['records']),
                'stored_indices':indices,'stored_source_sha256':digest(memory)}
            request={'case_id':case['id'],'split':split,'arm':arm,'memory':memory,'question':case['question'],
                'images':[f'page_{i:03}.png' for i in range(len(images))],'max_new_tokens':CONFIG['max_new_tokens'],
                'source_sha256':sha(source_path),'diagnostics':diagnostic,
                'storage_empty_query_tokens':None if images else text_count(processor,memory,''),
                'query_reserve':CONFIG['query_reserve'],'B':CONFIG['B'],
                'geometry':{'layout':geometry,'final_side':CONFIG['side'],'pages':page_meta} if images else None,
                'accounting':{k:measured[k] for k in ['total_input_tokens','vision_tokens','nonvision_input_tokens','image_grid_thw','vision_tokens_per_page']}}
            put(dest/'REQUEST.json',request);put(dest/'MEASUREMENT.json',measured)
            rows.append({'case_id':case['id'],'arm':arm,'path':dest.relative_to(ROOT).as_posix(),
                'request_sha256':sha(dest/'REQUEST.json'),'measurement_sha256':sha(dest/'MEASUREMENT.json')})
            for image in images: image.close()
        print('CPU inputs',split,len(rows)//3,'/',len(source_index['cases']),flush=True)
    manifest={'experiment_id':CONFIG['experiment_id'],'split':split,'rows':rows,'B':CONFIG['B'],
        'held_out_inference_started':False,'model_calls':0}
    if case_index is None: put(ROOT/('manifest.json' if split=='eval' else f'manifest_{split}.json'),manifest)
    return manifest

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--split',choices=['dev','eval','smoke'],required=True);p.add_argument('--assets',type=Path);p.add_argument('--case-index',type=int)
    a=p.parse_args();build(a.split,a.assets,a.case_index)
