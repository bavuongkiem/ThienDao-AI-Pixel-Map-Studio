import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading, queue
from engine import Studio

root=tk.Tk(); root.title('Thiên Đạo AI Pixel Map Studio | MVP 1.0'); root.geometry('900x690'); root.configure(bg='#172033')
frame=ttk.Frame(root,padding=18); frame.pack(fill='both',expand=True)
ttk.Label(frame,text='THIÊN ĐẠO AI PIXEL MAP STUDIO',font=('Segoe UI',20,'bold')).pack(anchor='w'); ttk.Label(frame,text='Ollama + ComfyUI local • Godot 4').pack(anchor='w')
vars={}
for label,key,default in [('Thư mục dự án (mỗi map một thư mục)','folder',''),('Model Ollama','model','qwen2.5:3b'),('Checkpoint ComfyUI (tên file chính xác)','checkpoint',''),('Workflow API JSON (tùy chọn)','workflow','')]:
    ttk.Label(frame,text=label).pack(anchor='w',pady=(8,0)); row=ttk.Frame(frame); row.pack(fill='x'); v=tk.StringVar(value=default); vars[key]=v; ttk.Entry(row,textvariable=v).pack(side='left',fill='x',expand=True)
    if key in ('folder','workflow'): ttk.Button(row,text='Chọn',command=lambda k=key,v=v:v.set(filedialog.askdirectory() if k=='folder' else filedialog.askopenfilename(filetypes=[('JSON','*.json')]))).pack(side='right')
style=tk.StringVar(value='Hiệp sĩ Pixel HD top-down')
ttk.Combobox(
    frame,
    textvariable=style,
    values=[
        'Hiệp sĩ Pixel HD top-down',
        'Hiệp sĩ Pixel HD side-scrolling',
        'Tu tiên Pixel HD top-down',
        'Ninja Pixel HD side-scrolling',
        'Kiếm hiệp Pixel HD top-down',
        'Trung cổ Fantasy Pixel HD',
        'Pháp sư Pixel HD top-down',
        'Thành trì Pixel HD top-down',
        'Thế giới mở Pixel HD top-down'
    ],
    state='readonly'
).pack(fill='x',pady=8)
text=tk.Text(frame,height=4); text.pack(fill='x'); text.insert('1.0','Tạo map Thiên Kiếm Tông có đại điện, cổng, cây đào và nền gạch đá.')
q=queue.Queue(); stop=threading.Event(); buttons=ttk.Frame(frame); buttons.pack(fill='x',pady=8)
log=tk.Text(frame,height=12,bg='#101827',fg='#e5e7eb'); log.pack(fill='both',expand=True)
def run():
    config={k:v.get() for k,v in vars.items()}; p=text.get('1.0','end').strip(); s=style.get()
    if not config['folder'] or not p: messagebox.showerror('Thiếu thông tin','Chọn thư mục và nhập yêu cầu.'); return
    start.config(state='disabled'); stop.clear()
    def worker():
        try:
            studio=Studio(config['folder'],config['model'],config['checkpoint'],q.put,config['workflow'] or None,stop.is_set); studio.run(p,s,'side-scrolling' in s)
        except Exception as e: q.put('LỖI: '+str(e))
        finally: q.put(None)
    threading.Thread(target=worker,daemon=True).start()
start=ttk.Button(buttons,text='Tạo / tiếp tục bản đồ',command=run); start.pack(side='left'); ttk.Button(buttons,text='Yêu cầu dừng',command=stop.set).pack(side='left',padx=8)
def poll():
    while not q.empty():
        m=q.get()
        if m is None: start.config(state='normal')
        else: log.insert('end',m+'\n'); log.see('end')
    root.after(200,poll)
poll(); root.mainloop()
