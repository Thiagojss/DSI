"""Cálculo decimal, validação, persistência, migração e ausência de custo fictício."""
import os,sys,tempfile
from pathlib import Path
from decimal import Decimal
from fastapi.testclient import TestClient
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'backend'))
from services.costs import CostInputs, analyze_costs

missing=analyze_costs(CostInputs(), None)
assert missing['profit_brl'] is None and missing['break_even_brl'] is None
assert missing['status']=='incompleto' and len(missing['warnings'])>=3
exact=analyze_costs(CostInputs(purchase_override_brl=100,shipping_brl=20,
    import_tax_pct=10, import_fixed_brl=5,marketplace_pct=10,payment_pct=3,
    sales_tax_pct=5,return_reserve_pct=2,marketplace_fixed_brl=2,
    payment_fixed_brl=1,packaging_brl=4,advertising_brl=10,other_brl=1,
    sale_price_brl=250,target_margin_pct=20))
# base=120 import=12 fixed=155 variable=20%=50 => profit=45, margin=18%, break even=193.75, target=258.33
assert exact['fixed_cost_brl']==155,exact
assert exact['variable_fees_brl']==50 and exact['total_cost_brl']==205,exact
assert exact['profit_brl']==45 and exact['margin_pct']==18 and exact['roi_pct']==21.95,exact
assert exact['break_even_brl']==193.75 and exact['target_sale_price_brl']==258.33,exact
assert exact['sensitivity']['sale_minus_10_pct']['profit_brl']==25,exact
assert exact['sensitivity']['purchase_plus_10_pct']['profit_brl']==34,exact
assert exact['sensitivity']['combined_stress']['profit_brl']==14,exact
assert analyze_costs(CostInputs(purchase_override_brl=10,shipping_brl=0,marketplace_pct=100,sale_price_brl=20))['break_even_brl'] is None
assert analyze_costs(CostInputs(purchase_override_brl=10,shipping_brl=0,sale_price_brl=5))['profit_brl']==-5
assert analyze_costs(CostInputs(purchase_override_brl=10,shipping_brl=0,marketplace_pct=90,target_margin_pct=20))['target_sale_price_brl'] is None
assert analyze_costs(CostInputs(shipping_brl=1,sale_price_brl=10), 15, True)['status']=='incompleto'

with tempfile.TemporaryDirectory() as tmp:
    os.environ['DSI_DATABASE_PATH']=str(Path(tmp)/'test.db')
    import main
    c=TestClient(main.app)
    assert c.get('/health').json()['version']=='0.18.0'
    a=c.post('/products',json={'title':'Cabo USB teste','url':'https://www.aliexpress.com/item/100500555666777.html','price':100,'currency':'BRL','category':'Acessórios'})
    assert a.status_code==200,a.text
    pid=a.json()['id']
    no=c.get(f'/products/{pid}/cost-analysis').json()
    assert not no['saved'] and no['analysis']['profit_brl'] is None
    bad=c.put(f'/products/{pid}/cost-analysis',json={'shipping_brl':-1})
    assert bad.status_code==422
    assert c.put(f'/products/{pid}/cost-analysis',json={'shipping_brl':1,'extra':123}).status_code==422
    assert c.put('/products/9999/cost-analysis',json={}).status_code==404
    i={'shipping_brl':0,'sale_price_brl':150,'marketplace_pct':10,'advertising_brl':10,'target_margin_pct':15}
    saved=c.put(f'/products/{pid}/cost-analysis',json=i)
    assert saved.status_code==200,saved.text
    assert saved.json()['analysis']['profit_brl']==25
    assert saved.json()['analysis']['break_even_brl']==122.22
    assert c.get(f'/products/{pid}/cost-analysis').json()['inputs']['sale_price_brl']==150
    listing=c.get('/intelligence/costs').json()
    assert listing['total']==1 and listing['scenarios'][0]['category']=='Acessórios'
    assert c.put(f'/products/{pid}/cost-analysis',json={**i,'sale_price_brl':200}).status_code==200
    assert c.get('/intelligence/costs').json()['total']==1
    # Registros de cenário sobrevivem à recaptura parcial do anúncio.
    assert c.post('/products',json={'title':'Cabo USB teste','url':'https://www.aliexpress.com/item/100500555666777.html','rating':4.8}).status_code==200
    assert c.get(f'/products/{pid}/cost-analysis').json()['inputs']['sale_price_brl']==200
    from database import engine, migrate_schema
    from sqlalchemy import inspect
    migrate_schema();migrate_schema()
    assert inspect(engine).has_table('cost_scenarios')
print('OK: cálculos, entradas inválidas, persistência, recaptura e migração.')
