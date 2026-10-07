"""Controller-held calibration controls, never copied into model workspaces."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pilot_fixtures import CLI


CONFIG_FAULTS = {
    "shallow": "recursive-delete", "concat-arrays": "arrays",
    "ignore-delete": "recursive-delete", "mutate-input": "recursive-delete",
    "first-owner": "owner", "empty-replace": "empty-object",
    "bad-pointer": "escaped-pointer", "bool-version": "bool-version",
    "duplicate-name": "duplicate-name", "cli-missing-provenance": "owner",
    "blank-name": "blank-name",
}
INVENTORY_FAULTS = {
    "sorted": "encounter-order", "per-row-filter": "aggregate-filter",
    "allow-bool": "boolean-delta", "bool-threshold": "boolean-threshold",
    "validate-survivors": "blocked-invalid", "float-total": "exact-total",
    "drop-zero": "zero-total",
}
BATCH_FAULTS = {
    "early-receipt": "partial-recovery", "duplicate-receipt": "completed-replay",
    "payload-conflict": "payload-conflict", "external-overwrite": "external-edit",
    "skip-last": "partial-recovery", "no-io": "partial-recovery",
    "receipt-only": "normal", "swallow-failure": "io-failure",
}
SUPPLEMENTARY_BATCH_FAULTS = {"completion-boundary", "utf8-preimage"}

VALIDATE_CONFIG = '''def valid(r):
    if not isinstance(r,dict) or (r.get("schema_version") != 1 or
        (FAULT != "bool-version" and type(r.get("schema_version")) is not int)):
        return False
    if not isinstance(r.get("layers"),list): return False
    names=[]
    for layer in r["layers"]:
        if not isinstance(layer,dict) or not isinstance(layer.get("name"),str) or (not layer["name"].strip() and FAULT!="blank-name") or not isinstance(layer.get("values"),dict): return False
        names.append(layer["name"])
    return FAULT == "duplicate-name" or len(set(names)) == len(names)
'''
RECURSIVE_CONFIG = '''import copy
def merge(layers):
    config={}; owners={}
    def erase(path):
        for key in list(owners):
            if key[:len(path)] == path: del owners[key]
    def apply(target,patch,path,owner):
        for key,value in patch.items():
            location=path+(key,)
            if value is None:
                if FAULT != "ignore-delete":
                    target.pop(key,None); erase(location)
            elif isinstance(value,dict):
                if not isinstance(target.get(key),dict) or (not value and FAULT == "empty-replace"):
                    target[key]={}; erase(location)
                if FAULT == "shallow":
                    target[key]=copy.deepcopy(value)
                else: apply(target[key],value,location,owner)
            else:
                if FAULT == "concat-arrays" and isinstance(value,list) and isinstance(target.get(key),list):
                    target[key]=target[key]+copy.deepcopy(value)
                else: target[key]=copy.deepcopy(value)
                if FAULT != "first-owner" or location not in owners: owners[location]=owner
                for child in list(owners):
                    if len(child)>len(location) and child[:len(location)]==location: del owners[child]
    for layer in layers: apply(config,layer["values"],(),layer["name"])
    def pointer(path):
        return "/"+"/".join(k if FAULT=="bad-pointer" else k.replace("~","~0").replace("/","~1") for k in path)
    return {"config":config,"provenance":{pointer(k):v for k,v in owners.items()}}
'''
FLAT_CONFIG = '''import copy
def merge(layers):
    nodes={():("object",None,None)}
    def clear(prefix):
        for path in list(nodes):
            if path[:len(prefix)]==prefix: del nodes[path]
    def overlay(value,path,owner):
        if value is None: clear(path)
        elif isinstance(value,dict):
            if nodes.get(path,(None,))[0] != "object": clear(path)
            nodes[path]=("object",None,None)
            for key,item in value.items(): overlay(item,path+(key,),owner)
        else:
            clear(path); nodes[path]=("leaf",copy.deepcopy(value),owner)
    for layer in layers:
        for key,value in layer["values"].items(): overlay(value,(key,),layer["name"])
    config={}; owners={}
    for path,(kind,value,owner) in sorted(nodes.items(),key=lambda item:len(item[0])):
        if not path: continue
        target=config
        for key in path[:-1]: target=target[key]
        target[path[-1]]={} if kind=="object" else value
        if kind=="leaf": owners["/"+"/".join(k.replace("~","~0").replace("/","~1") for k in path)]=owner
    return {"config":config,"provenance":owners}
'''


def install_config(root, algorithm="recursive", fault=None):
    if algorithm not in ("recursive", "flat") or (fault and fault not in CONFIG_FAULTS):
        raise ValueError("unknown config control")
    package = Path(root) / "config_tool"
    prefix = f"FAULT={fault!r}\n"
    (package / "validate.py").write_text(prefix + VALIDATE_CONFIG)
    (package / "merge.py").write_text(prefix + (RECURSIVE_CONFIG if algorithm == "recursive" else FLAT_CONFIG))
    resolve = 'from .validate import valid\nfrom .merge import merge\ndef resolve(request):\n    if not valid(request): return {"error":"invalid"}\n    result=merge(request["layers"])\n'
    if fault == "mutate-input":
        resolve += '    request["layers"].clear()\n'
    resolve += '    return result\n'
    (package / "__init__.py").write_text(resolve)
    cli = CLI
    if fault == "cli-missing-provenance":
        cli = cli.replace('print(json.dumps({"result": resolve(json.load(sys.stdin))}))', 'r=resolve(json.load(sys.stdin))\nr.pop("provenance",None)\nprint(json.dumps({"result":r}))')
    (package / "cli.py").write_text(cli)


INVENTORY_HEADER = '''import json
import sys
from helpers import normalize
def resolve(r):
    if not isinstance(r,dict) or not isinstance(r.get("rows"),list) or not isinstance(r.get("blocked",[]),list): return {"error":"invalid"}
    blocked=r.get("blocked",[])
    if any(not isinstance(s,str) or not s.strip() for s in blocked): return {"error":"invalid"}
    blocked={normalize(s) for s in blocked}
    minimum=r.get("minimum_total") if VERSION==2 else None
    if VERSION==2 and "minimum_total" in r and (not isinstance(minimum,int) if FAULT=="bool-threshold" else type(minimum) is not int): return {"error":"invalid"}
    rows=[]
    for row in r["rows"]:
        if not isinstance(row,dict) or not isinstance(row.get("sku"),str) or not row["sku"].strip(): return {"error":"invalid"}
        sku=normalize(row["sku"])
        if FAULT=="validate-survivors" and sku in blocked: continue
        if (not isinstance(row.get("delta"),int) if FAULT=="allow-bool" else type(row.get("delta")) is not int): return {"error":"invalid"}
        if FAULT=="per-row-filter" and minimum is not None and row["delta"]<minimum: continue
        rows.append((sku,row["delta"]))
'''
INVENTORY_DICT = '''    totals={}
    for sku,delta in rows: totals[sku]=totals.get(sku,0)+delta
    result=[{"sku":sku,"total":total} for sku,total in totals.items() if sku not in blocked and (minimum is None or total>=minimum)]
'''
INVENTORY_BUCKETS = '''    names=list(dict.fromkeys(sku for sku,_ in rows))
    result=[]
    for sku in names:
        total=sum(delta for name,delta in rows if name==sku)
        if sku not in blocked and (minimum is None or total>=minimum): result.append({"sku":sku,"total":total})
'''
INVENTORY_TAIL = '''    if VERSION==1 or FAULT=="sorted": result.sort(key=lambda row:row["sku"])
    if FAULT=="float-total":
        for row in result: row["total"]=float(row["total"])
    if FAULT=="drop-zero": result=[row for row in result if row["total"]]
    return result
if __name__=="__main__":
    print(json.dumps({"result":resolve(json.load(sys.stdin))}))
'''


def install_inventory(root, algorithm="dict", version=2, fault=None, write_helper=False):
    if algorithm not in ("dict", "buckets") or version not in (1, 2) or (fault and fault not in INVENTORY_FAULTS):
        raise ValueError("unknown inventory control")
    root = Path(root)
    if write_helper:
        helper = 'def normalize(value):\n    return value.strip().upper()\n' if algorithm == "dict" else 'def normalize(value):\n    stripped = str.strip(value)\n    return str.upper(stripped)\n'
        (root / "helpers.py").write_text(helper)
    (root / "candidate.py").write_text(f"FAULT={fault!r}\nVERSION={version}\n" + INVENTORY_HEADER + (INVENTORY_DICT if algorithm == "dict" else INVENTORY_BUCKETS) + INVENTORY_TAIL)
    (root / "handoff.json").write_text('{"requirement_version":' + str(version) + ',"previous_verification":"unknown","remaining":[]}')


BATCH_HEADER = '''import hashlib
import json
import sys
from pathlib import Path
from public_io import IO
def encoded(value): return json.dumps(value,sort_keys=True,separators=(",",":"))
def execute(r):
    if not isinstance(r,dict) or not isinstance(r.get("root"),str) or not Path(r["root"]).is_absolute() or not isinstance(r.get("operation_id"),str) or not r["operation_id"].strip() or not isinstance(r.get("outputs"),dict) or not r["outputs"]: return "invalid"
    outputs=r["outputs"]; names=list(outputs)
    for name,body in outputs.items():
        if not name or name.startswith("/") or any(p in ("",".","..") for p in name.split("/")) or name.split("/")[0] in (".batch","receipts.json") or not isinstance(body,str): return "invalid"
    if any(a!=b and b.startswith(a+"/") for a in names for b in names): return "invalid"
    root=Path(r["root"]); io=IO(root); op=r["operation_id"]
    def read(path):
        target=root/path
        return target.read_bytes().decode("utf-8") if target.exists() else None
    def raw(path):
        target=root/path
        if not target.exists(): return None
        body=target.read_bytes()
        if FAULT=="utf8-preimage": body=body.decode("utf-8").encode()
        return body.hex()
    def write(path,body):
        if FAULT=="no-io":
            target=root/path; target.parent.mkdir(parents=True,exist_ok=True); target.write_text(body)
        else: io.replace(path,body)
    def complete():
        receipt=json.loads(read("receipts.json") or '{"completed":[]}')
        if op not in receipt["completed"] or FAULT=="duplicate-receipt": receipt["completed"].append(op)
        write("receipts.json",encoded(receipt))
    def completed():
        value=json.loads(read("receipts.json") or '{"completed":[]}')
        ids=value.get("completed",[])
        if (isinstance(ids,list) and all(isinstance(x,str) and x.strip() for x in ids)
                and len(set(ids))==len(ids) and ids.count(op)==1):
            return "replayed" if all(raw(path)==body.encode().hex() for path,body in outputs.items()) else "conflict"
        return None
    state=".batch/"+hashlib.sha256(op.encode()).hexdigest()+".json"
'''
BATCH_JOURNAL = '''    previous=read(state)
    if previous:
        journal=json.loads(previous)
        if journal["outputs"]!=outputs and FAULT!="payload-conflict": return "conflict"
    else:
        journal={"outputs":outputs,"before":{path:raw(path) for path in names},"done":False}
        write(state,encoded(journal))
    for path,body in outputs.items():
        if raw(path) not in (journal["before"].get(path),body.encode().hex()) and FAULT not in ("external-overwrite","payload-conflict"): return "conflict"
    completion=completed()
    if completion=="conflict" and FAULT not in ("external-overwrite","payload-conflict","early-receipt"): return "conflict"
    if FAULT!="completion-boundary" and completion=="replayed":
        if FAULT=="duplicate-receipt": complete()
        return "replayed"
    if journal["done"]: return "replayed" if FAULT else "conflict"
    if FAULT=="early-receipt":
        complete(); journal["done"]=True; write(state,encoded(journal))
    for index,(path,body) in enumerate(outputs.items()):
        if FAULT=="receipt-only" or (FAULT=="skip-last" and index==len(outputs)-1): continue
        if raw(path)!=body.encode().hex(): write(path,body)
    complete(); journal["done"]=True; write(state,encoded(journal))
    return "applied"
'''
BATCH_STAGED = '''    previous=read(state)
    fingerprint=hashlib.sha256(encoded(outputs).encode()).hexdigest()
    if previous:
        manifest=json.loads(previous)
        if manifest["fingerprint"]!=fingerprint: return "conflict"
    else:
        entries=[]
        for index,(path,body) in enumerate(outputs.items()):
            stage=state+"."+str(index)+".stage"
            write(stage,body)
            entries.append({"path":path,"old":raw(path),"stage":stage})
        manifest={"fingerprint":fingerprint,"entries":entries,"done":False}
        write(state,encoded(manifest))
    for entry in manifest["entries"]:
        if raw(entry["path"]) not in (entry["old"],raw(entry["stage"])): return "conflict"
    completion=completed()
    if completion=="conflict": return "conflict"
    if FAULT!="completion-boundary" and completion=="replayed": return "replayed"
    if manifest["done"]: return "replayed" if FAULT else "conflict"
    for entry in manifest["entries"]:
        body=read(entry["stage"])
        if raw(entry["path"])!=body.encode().hex(): write(entry["path"],body)
    complete(); manifest["done"]=True; write(state,encoded(manifest))
    return "applied"
'''
BATCH_TAIL = '''if __name__=="__main__":
    try: status=execute(json.load(sys.stdin))
    except OSError:
        if FAULT!="swallow-failure": raise
        status="applied"
    print(json.dumps({"result":{"status":status}}))
'''


def install_batch(root, algorithm="journal", fault=None):
    if algorithm not in ("journal", "staged") or (fault and fault not in BATCH_FAULTS and fault not in SUPPLEMENTARY_BATCH_FAULTS):
        raise ValueError("unknown batch control")
    (Path(root) / "batch_tool.py").write_text(f"FAULT={fault!r}\n" + BATCH_HEADER + (BATCH_JOURNAL if algorithm == "journal" else BATCH_STAGED) + BATCH_TAIL)
