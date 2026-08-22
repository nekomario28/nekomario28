from __future__ import annotations

import json, shutil, subprocess, time
from pathlib import Path
import requests
from gradio_client import Client, handle_file
from huggingface_hub import hf_hub_download

OUT=Path('wan_state_probe'); OUT.mkdir(exist_ok=True)

def save_ref(ref,dst):
    if isinstance(ref,dict): ref=ref.get('path') or ref.get('url') or ref.get('video') or ref.get('value')
    print('SAVE_REF',repr(ref),flush=True)
    if not ref: raise RuntimeError('empty video ref')
    s=str(ref)
    if s.startswith('http'):
        r=requests.get(s,timeout=180); r.raise_for_status(); dst.write_bytes(r.content)
    else:
        p=Path(s)
        if not p.exists(): raise RuntimeError(f'no local file {s!r}')
        shutil.copy2(p,dst)

def poll_noargs(client,kind,timeout=900):
    start=time.time(); last=None
    while time.time()-start<timeout:
        try:
            res=client.predict(api_name='/status_refresh')
            last=res
            print('STATE_POLL',kind,repr(res),flush=True)
            first=res[0] if isinstance(res,(tuple,list)) else res
            if isinstance(first,dict): first=first.get('path') or first.get('url') or first.get('video') or first.get('value')
            if first: return first,res
        except Exception as e:
            last=repr(e); print('STATE_POLL_ERROR',repr(e),flush=True)
        time.sleep(20)
    raise TimeoutError(repr(last))

def fresh():
    c=Client('Wan-AI/Wan2.1',verbose=True)
    prompt='A bicycle pedals itself down the street, stops at a red light, and then continues when it turns green.'
    res=c.predict(prompt,'1280*720',False,2003,api_name='/t2v_generation_async')
    print('FRESH_SUBMIT_PUBLIC',repr(res),flush=True)
    time.sleep(15)
    v,poll=poll_noargs(c,'t2v')
    dst=OUT/'sid_003-fresh-wan21.mp4'; save_ref(v,dst)
    return {'status':'success','output':str(dst),'submit_public':repr(res),'poll_public':repr(poll)}

def anchor():
    c=Client('Wan-AI/Wan2.1',verbose=True)
    src=Path(hf_hub_download(repo_id='UBC-ViL/Spotlight-VideoGen-Errors',repo_type='dataset',filename='test/spotlight/ltx2/sid_021.mp4',local_dir=OUT/'src'))
    anchor=OUT/'sid_021-anchor.png'
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-ss','0.900','-i',str(src),'-frames:v','1',str(anchor)],check=True)
    prompt='The same tabby cat remains inside the cardboard box and slowly pokes only its head out over the edge, looking around.'
    res=c.predict(prompt,handle_file(str(anchor)),False,3021,api_name='/i2v_generation_async')
    print('ANCHOR_SUBMIT_PUBLIC',repr(res),flush=True)
    time.sleep(15)
    v,poll=poll_noargs(c,'i2v')
    dst=OUT/'sid_021-anchor-wan21.mp4'; save_ref(v,dst)
    return {'status':'success','output':str(dst),'anchor':str(anchor),'submit_public':repr(res),'poll_public':repr(poll)}

def main():
    m={}
    try: m['fresh']=fresh()
    except Exception as e: m['fresh']={'status':'failed','error':repr(e)}; print('FRESH_FAIL',repr(e),flush=True)
    try: m['anchor']=anchor()
    except Exception as e: m['anchor']={'status':'failed','error':repr(e)}; print('ANCHOR_FAIL',repr(e),flush=True)
    (OUT/'manifest.json').write_text(json.dumps(m,indent=2),encoding='utf-8')
    print(json.dumps(m,indent=2),flush=True)

if __name__=='__main__': main()
