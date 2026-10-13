"""Independent cap-probe ledger boundary controls; synthetic transports only."""
import contextlib,hashlib,importlib.util,io,json,tempfile
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def run():
    path=R/'runtime/operations.py';before=hashlib.sha256(path.read_bytes()).hexdigest()
    spec=importlib.util.spec_from_file_location('cap_probe_review_ledger',path);o=importlib.util.module_from_spec(spec);spec.loader.exec_module(o)
    results=[];log=io.StringIO()
    with contextlib.redirect_stdout(log):
        with tempfile.TemporaryDirectory() as temp:
            calls=[];ledger=o.Ledger(temp,{'test':'prior'},keys={'openrouter':'synthetic-OR','jev':'synthetic-Jev'},transport=lambda *args:(calls.append(args) or (200,b'{}')))
            assert ledger.totals()['budget_charge_usd']==.100166 and ledger.totals()['operations']==0
            try:ledger.operation('first','inventory',{},lambda raw:{'observed_cost_usd':0},identity={},reserve=1.90)
            except o.Pause:pass
            else:raise AssertionError('shared budget debit not applied before intent')
            assert not calls and ledger.totals()['operations']==0
            results.append('prior_debit_and_precall_shared_budget')
        with tempfile.TemporaryDirectory() as temp:
            calls=[];ledger=o.Ledger(temp,{'test':'stagecaps'},keys={'openrouter':'synthetic-OR','jev':'synthetic-Jev'},transport=lambda *args:(calls.append(args) or (200,b'{}')))
            for kind in ('inventory','jev','stronger'):
                ledger.operation(kind,kind,{},lambda raw:{'observed_cost_usd':0},identity={},reserve=.01)
                try:ledger.operation(kind+'-extra',kind,{},lambda raw:{'observed_cost_usd':0},identity={},reserve=.01)
                except o.Pause:pass
                else:raise AssertionError('second stage call permitted')
            assert len(calls)==ledger.totals()['operations']==3
            assert all(ledger.totals()[name]==1 for name in ('inventory_cases','jev_cases','stronger_cases'))
            results.append('one_per_stage_three_total')
        with tempfile.TemporaryDirectory() as temp:
            calls=[];ledger=o.Ledger(temp,{'test':'postresponse'},keys={'openrouter':'synthetic-OR','jev':'synthetic-Jev'},transport=lambda *args:(calls.append(args) or (200,b'{}')))
            result=ledger.operation('inventory','inventory',{},lambda raw:{'observed_cost_usd':1.95},identity={},reserve=.1)
            assert result['observed_cost_usd']==1.95 and abs(ledger.totals()['budget_charge_usd']-2.050166)<1e-12
            assert len(list(Path(temp).glob('operations/*/result.json')))==1
            try:ledger.operation('jev','jev',{},lambda raw:{'observed_cost_usd':0},identity={},reserve=.01)
            except o.Stop:pass
            else:raise AssertionError('postresponse shared overrun did not latch')
            assert len(calls)==1;results.append('completed_result_preserved_shared_overrun_latched')
        with tempfile.TemporaryDirectory() as temp:
            calls=[]
            def uncertain(*args):calls.append(args);raise TimeoutError('synthetic')
            ledger=o.Ledger(temp,{'test':'uncertain'},keys={'openrouter':'synthetic-OR'},transport=uncertain)
            try:ledger.operation('inventory','inventory',{},lambda raw:{},identity={},reserve=.1)
            except o.Stop:pass
            else:raise AssertionError('uncertain attempt accepted')
            try:o.Ledger(temp,{'test':'uncertain'},keys={'openrouter':'synthetic-OR'},transport=uncertain)
            except o.Stop:pass
            else:raise AssertionError('uncertain call resumed')
            assert len(calls)==1;results.append('uncertain_call_never_retried')
    assert hashlib.sha256(path.read_bytes()).hexdigest()==before,'ledger changed during review'
    return {'scope':'draft ledger only; not full implementation approval','checks':results,'passed':True,'operations_sha256':before,'provider_calls':0}
if __name__=='__main__':print(json.dumps(run(),indent=2))
