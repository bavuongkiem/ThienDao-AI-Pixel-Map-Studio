import json, time, uuid, random, re, sqlite3, shutil
from pathlib import Path
import requests
from PIL import Image

class Studio:
    def __init__(self, root, model='qwen2.5:3b', checkpoint='', log=print, workflow=None, cancelled=lambda:False):
        self.root=Path(root); self.root.mkdir(parents=True,exist_ok=True)
        self.model=model; self.checkpoint=checkpoint; self.log=log; self.workflow=workflow; self.cancelled=cancelled
        self.db=sqlite3.connect(self.root/'jobs.sqlite'); self.db.execute('CREATE TABLE IF NOT EXISTS jobs(name TEXT PRIMARY KEY, status TEXT, detail TEXT)'); self.db.commit()
    def check(self):
        if self.cancelled(): raise RuntimeError('Đã yêu cầu dừng; tác vụ ComfyUI đang chạy có thể vẫn tiếp tục.')
    def status(self,name,status,detail=''):
        self.db.execute('INSERT OR REPLACE INTO jobs VALUES(?,?,?)',(name,status,detail)); self.db.commit(); self.log(f'{name}: {status} {detail}')
    def plan(self,prompt,style):
        p=self.root/'plan.json'
        if p.exists(): return json.loads(p.read_text(encoding='utf-8'))
        self.status('Kế hoạch','đang chạy')
        schema={'type':'object','properties':{'assets':{'type':'array','minItems':3,'maxItems':6,'items':{'type':'object','properties':{'name':{'type':'string'},'prompt':{'type':'string'},'kind':{'type':'string','enum':['building','nature','ground']}},'required':['name','prompt','kind']}}},'required':['assets']}
        data=None
        for attempt in range(2):
            try:
                r=requests.post('http://127.0.0.1:11434/api/chat',json={'model':self.model,'stream':False,'keep_alive':'5m','options':{'num_predict':2048,'temperature':0},'format':schema,'messages':[{'role':'system','content':'Design a game asset list. English image prompts, consistent pixel art angle and palette, isolated single object on plain white background for buildings/nature; seamless square ground texture for ground. Include exactly one ground asset and at least two objects. Return one valid JSON object matching the schema, with no markdown or extra text.'},{'role':'user','content':style+'; '+prompt}]},timeout=(10,900)); r.raise_for_status()
                data=json.loads(r.json()['message']['content'])
                if not isinstance(data,dict) or not isinstance(data.get('assets'),list) or not 3<=len(data['assets'])<=6 or sum(a.get('kind')=='ground' for a in data['assets'] if isinstance(a,dict))!=1:
                    raise ValueError('Ollama returned a plan that does not match the required asset schema.')
                break
            except requests.exceptions.ReadTimeout as e:
                raise TimeoutError('Ollama chưa trả kế hoạch sau 15 phút. Kiểm tra Ollama còn hoạt động rồi thử lại; nếu vẫn lỗi, chọn một model Ollama nhẹ hơn.') from e
            except (json.JSONDecodeError,ValueError,KeyError,TypeError) as e:
                if attempt==0:
                    self.status('Kế hoạch','đang thử lại','Ollama trả về JSON không hợp lệ')
                    continue
                raise ValueError('Ollama trả kế hoạch JSON không hợp lệ sau 2 lần thử. Hãy bấm Tạo / tiếp tục bản đồ để thử lại.') from e
        if not 3<=len(data['assets'])<=6 or sum(a['kind']=='ground' for a in data['assets'])!=1: raise ValueError('Kế hoạch AI không hợp lệ: cần 3–6 asset, đúng một nền.')
        for i,a in enumerate(data['assets']): a['id']=f'asset_{i:02d}'
        p.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8'); self.status('Kế hoạch','hoàn tất'); return data
    def graph(self,prompt):
        if self.workflow:
            g=json.loads(Path(self.workflow).read_text(encoding='utf-8'))
            if not any(n.get('class_type')=='CLIPTextEncode' and n.get('inputs',{}).get('text')=='__PROMPT__' for n in g.values()): raise ValueError('Workflow API cần CLIPTextEncode có text __PROMPT__.')
            for n in g.values():
                if n.get('class_type')=='CLIPTextEncode' and n.get('inputs',{}).get('text')=='__PROMPT__': n['inputs']['text']=prompt
                if n.get('class_type')=='KSampler': n['inputs']['seed']=random.randrange(2**32)
            return g
        if not self.checkpoint: raise ValueError('Chọn tên checkpoint ComfyUI hoặc workflow API.')
        return {'1':{'class_type':'CheckpointLoaderSimple','inputs':{'ckpt_name':self.checkpoint}},'2':{'class_type':'CLIPTextEncode','inputs':{'clip':['1',1],'text':prompt}},'3':{'class_type':'CLIPTextEncode','inputs':{'clip':['1',1],'text':'blurry, photorealistic, text, watermark, multiple objects, perspective inconsistency'}},'4':{'class_type':'EmptyLatentImage','inputs':{'width':512,'height':512,'batch_size':1}},'5':{'class_type':'KSampler','inputs':{'model':['1',0],'positive':['2',0],'negative':['3',0],'latent_image':['4',0],'seed':random.randrange(2**32),'steps':24,'cfg':7,'sampler_name':'euler','scheduler':'normal','denoise':1}},'6':{'class_type':'VAEDecode','inputs':{'samples':['5',0],'vae':['1',2]}},'7':{'class_type':'SaveImage','inputs':{'images':['6',0],'filename_prefix':'ThienDao'}}}
    def generate(self,a,style):
        self.check(); folder=self.root/'assets'; folder.mkdir(exist_ok=True); dest=folder/(a['id']+'.png')
        if dest.exists(): self.log('Dùng lại '+dest.name); return dest
        self.status(a['id'],'đang tạo',a['name']); base='http://127.0.0.1:8188'
        r=requests.post(base+'/prompt',json={'prompt':self.graph(style+', '+a['prompt']),'client_id':str(uuid.uuid4())},timeout=30); r.raise_for_status(); pid=r.json()['prompt_id']
        for _ in range(600):
            self.check(); r=requests.get(base+'/history/'+pid,timeout=20); r.raise_for_status(); h=r.json().get(pid)
            if h:
                if h.get('status',{}).get('status_str')=='error': raise RuntimeError(str(h['status']))
                imgs=[im for o in h.get('outputs',{}).values() for im in o.get('images',[])]
                if imgs:
                    im=imgs[0]; r=requests.get(base+'/view',params={k:im[k] for k in ('filename','subfolder','type')},timeout=60); r.raise_for_status(); raw=folder/(a['id']+'_raw.png'); raw.write_bytes(r.content)
                    with Image.open(raw) as src: img=src.convert('RGBA')
                    if a['kind']!='ground':
                        from rembg import remove
                        img=remove(img); bbox=img.getbbox()
                        if not bbox: raise ValueError('Tách nền không còn đối tượng.')
                        img=img.crop(bbox)
                    img.thumbnail((256,256),Image.Resampling.NEAREST)
                    if a['kind']=='ground': img=img.resize((256,256),Image.Resampling.NEAREST)
                    img.save(dest); self.status(a['id'],'hoàn tất'); return dest
            time.sleep(2)
        raise TimeoutError('ComfyUI quá thời gian chờ.')
    def run(self,prompt,style,side=False):
        plan=self.plan(prompt,style)
        for a in plan['assets']: self.generate(a,style)
        self.check(); self.export(plan,side); self.status('Dự án','hoàn tất')
    def export(self,plan,side=False):
        out=self.root/'godot'; out.mkdir(exist_ok=True); (out/'assets').mkdir(exist_ok=True)
        for a in plan['assets']: shutil.copy2(self.root/'assets'/(a['id']+'.png'),out/'assets')
        ground=next(a for a in plan['assets'] if a['kind']=='ground'); objs=[a for a in plan['assets'] if a['kind']!='ground']; w,h=2048,1024
        (out/'project.godot').write_text('config_version=5\n[application]\nconfig/name="Thien Dao Map"\nrun/main_scene="res://map.tscn"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\ntextures/default_filters/use_nearest_mipmap_filter=false\n',encoding='utf-8')
        lines=[f'[gd_scene load_steps={len(plan["assets"])+3} format=3]']
        for i,a in enumerate(plan['assets'],1): lines.append(f'[ext_resource type="Texture2D" path="res://assets/{a["id"]}.png" id="{i}"]')
        lines+=['[sub_resource type="RectangleShape2D" id="floor"]',f'size = Vector2({w}, 32)','[sub_resource type="RectangleShape2D" id="object_shape"]','size = Vector2(80, 40)','[node name="Map" type="Node2D"]','texture_filter = 1','[node name="Ground" type="Node2D" parent="."]']
        gi=plan['assets'].index(ground)+1
        for y in range(0,h,128):
            for x in range(0,w,128):
                if side and y<896: continue
                lines += [f'[node name="Tile_{x}_{y}" type="Sprite2D" parent="Ground"]',f'position = Vector2({x+64}, {y+64})',f'texture = ExtResource("{gi}")','scale = Vector2(0.5, 0.5)']
        lines+=['[node name="Objects" type="Node2D" parent="."]','y_sort_enabled = true']; layout=[]
        for i,a in enumerate(objs):
            x=240+(i%5)*350; y=896 if side else 280+(i//5)*300; idx=plan['assets'].index(a)+1
            lines += [f'[node name="Object_{i}" type="Sprite2D" parent="Objects"]',f'position = Vector2({x}, {y})',f'texture = ExtResource("{idx}")','offset = Vector2(0, -80)']; layout.append({'asset':a['id'],'x':x,'y':y})
        if not side:
            for i,o in enumerate(layout):
                lines += [f'[node name="Block_{i}" type="StaticBody2D" parent="."]',f'position = Vector2({o["x"]}, {o["y"]})',f'[node name="CollisionShape2D" type="CollisionShape2D" parent="Block_{i}"]','shape = SubResource("object_shape")']
        for name,x,y in [('PlayerSpawn',100,800 if side else 500),('NPCSpawn',400,800 if side else 500),('MonsterSpawn',1700,800 if side else 800)]: lines += [f'[node name="{name}" type="Marker2D" parent="."]',f'position = Vector2({x}, {y})']
        if side: lines+=['[node name="Floor" type="StaticBody2D" parent="."]',f'position = Vector2({w//2}, 912)','[node name="CollisionShape2D" type="CollisionShape2D" parent="Floor"]','shape = SubResource("floor")']
        lines+=['[node name="Camera2D" type="Camera2D" parent="."]','position = Vector2(1024, 512)','zoom = Vector2(0.5, 0.5)']
        (out/'map.tscn').write_text('\n\n'.join(lines)+'\n',encoding='utf-8'); (out/'map.json').write_text(json.dumps({'width':w,'height':h,'objects':layout,'side_scrolling':side},indent=2),encoding='utf-8'); self.log('Xuất: '+str(out))
