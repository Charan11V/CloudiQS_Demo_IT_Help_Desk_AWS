"""Informational mapping of existing enterprise capability catalogue to cases.
This prevents claiming untested features are covered. Input is the existing pack.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from eval_utils import all_public,ROOT
SOURCE=Path(__file__).resolve().parents[2]/'_eval_analysis/cloudiqs_helio_cursor_workspace/cloudiqs_enterprise_demo_pack/data/feature_inventory.json'
# A self-contained snapshot of the user's original feature catalogue is kept in docs.
SOURCE=ROOT/'docs/feature_inventory_reference.json'
features=json.loads(SOURCE.read_text()); cases=all_public()
mapping={
1:['S-005','S-042'],2:['S-005','M-003'],3:['S-005','S-013'],4:['S-007','M-004'],5:['S-006','M-004'],6:['S-005'],7:['S-011','M-019'],8:['S-016'],9:['S-004','S-027'],
11:['S-018','M-022'],12:['S-002','S-036'],13:['S-002'],15:['S-027'],17:['S-004','M-002'],20:['S-021'],21:['S-001','M-001'],22:['S-001','S-004'],24:['S-026'],27:['S-019','M-006'],
31:['S-031','S-032','S-033'],32:['S-043'],34:['S-023'],35:['S-024'],37:['S-001','S-036'],39:['S-023'],
41:['S-021'],42:['S-021','S-022'],43:['S-021'],44:['S-011'],49:['LEG-CASE-013'],51:['S-016','M-015'],52:['LEG-CASE-040'],
56:['S-037','S-007'],57:['S-007'],58:['S-012','S-027'],59:['S-008','S-010','S-034'],60:['S-008'],61:['UI-013'],62:['S-020','S-039','ADV-001'],63:['UI-014'],64:['S-012','S-049'],65:['S-030','UI-019'],
66:['S-020','S-003'],67:['UI-005'],68:['S-003','M-013'],69:['S-020'],70:['S-018','S-036'],71:['S-041'],72:['UI-014'],74:['S-028','M-018'],
75:['S-027','S-029'],76:['UI-015'],77:['S-005','S-013','UI-015'],78:['S-030','UI-018'],79:['S-013','UI-017'],80:['S-031','M-010'],81:['S-031'],82:['S-033'],83:['M-017'],84:['S-031'],85:['S-040','M-017'],
87:['S-024','UI-020'],88:['S-044','M-032'],89:['UI-012'],90:['S-045'],91:['S-029'],92:['UI-035'],93:['S-032'],94:['S-031'],95:['UI-014'],96:['UI-029'],
97:['UI-004'],100:['UI-026'],101:['M-018'],103:['M-001','M-009'],104:['M-018'],
105:['UI-011'],106:['UI-012'],108:['UI-011'],109:['S-012','UI-011'],110:['UI-013'],111:['UI-011'],114:['S-050']
}
rows=[]
for x in features:
 n=int(x['feature_id'].split('-')[1]);ids=mapping.get(n,[])
 unknown=[c for c in ids if c not in cases]
 if unknown:raise RuntimeError((n,unknown))
 # Coverage labels require different levels of verification.
 status='explicit_test_case' if ids and not all(i.startswith('LEG-') for i in ids) else ('legacy_exploratory_only' if ids else 'not_explicitly_tested')
 # UI acceptance scenario is only a specification until Cursor implements Playwright test.
 if ids and all(i.startswith('UI-') for i in ids):status='ui_acceptance_defined_not_automated'
 rows.append({'feature_id':x['feature_id'],'module':x['module'],'capability':x['capability'],'operation_class':x['operation_class'],'data_support_status':x['status'],
              'mapped_case_ids':ids,'coverage_label':status,'note':'A test case exists; this is not proof that the app implements/passes the feature.'})
(ROOT/'docs/FEATURE_COVERAGE_MAP.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False)+'\n')
from collections import Counter
cnt=Counter(x['coverage_label'] for x in rows)
text=['# Capability-to-Evaluation Coverage Map','',
'Original enterprise fixture advertises 114 capabilities, not 114 features already built. A test case is **not** evidence of implementation or successful evaluation.','',
'| Coverage label | Count |','|---|---:|']
for s,n in sorted(cnt.items()):text.append(f'| {s} | {n} |')
text+=['','## Per-feature mapping','', '| Feature | Capability | Test cases | Status |','|---|---|---|---|']
for x in rows:text.append('| '+ ' | '.join([x['feature_id'],x['capability'].replace('|','/'),', '.join(x['mapped_case_ids']) or '—',x['coverage_label']])+' |')
text+=['','Unmapped features should be marked as gaps in the evaluation UI and implemented/tested if part of the application scope. Do not silently count them as complete.']
(ROOT/'docs/FEATURE_COVERAGE_MAP.md').write_text('\n'.join(text)+'\n')
print('Features',len(rows),'Coverage',dict(cnt))
