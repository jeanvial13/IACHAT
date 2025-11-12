import os, json, re
from datetime import datetime

BASE = "/data/chats"

def ensure_dirs():
    os.makedirs(BASE, exist_ok=True)
    # proyecto por defecto
    p = os.path.join(BASE, "default.json")
    if not os.path.exists(p):
        json.dump({"project":"default","messages":[]}, open(p,"w",encoding="utf-8"))

def sanitize(name:str)->str:
    name = name.strip().lower()
    name = re.sub(r'[^a-z0-9_\- ]+', '', name)
    name = name.replace(' ', '_')
    return name or "default"

def list_projects():
    ensure_dirs()
    items = []
    for fn in os.listdir(BASE):
        if fn.endswith(".json"):
            items.append(fn[:-5])
    return sorted(items)

def project_path(name:str)->str:
    ensure_dirs()
    name = sanitize(name)
    return os.path.join(BASE, f"{name}.json")

def load_project(name:str):
    path = project_path(name)
    if not os.path.exists(path):
        return {"project": sanitize(name), "messages":[]}
    try:
        return json.load(open(path,"r",encoding="utf-8"))
    except Exception:
        return {"project": sanitize(name), "messages":[]}

def save_message(name:str, role:str, content:str):
    data = load_project(name)
    data["project"] = sanitize(name)
    data["messages"].append({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "role": role,
        "content": content
    })
    json.dump(data, open(project_path(name), "w", encoding="utf-8"))

def overwrite_project(name:str, messages:list):
    data = {"project": sanitize(name), "messages": messages}
    json.dump(data, open(project_path(name), "w", encoding="utf-8"))

def export_project(name:str):
    data = load_project(name)
    txt_lines = []
    for m in data.get("messages", []):
        who = "USER" if m["role"]=="user" else "ASSISTANT"
        ts = m.get("timestamp","")
        txt_lines.append(f"[{ts}] {who}: {m['content']}")
    txt = "\n".join(txt_lines)
    return data, txt
