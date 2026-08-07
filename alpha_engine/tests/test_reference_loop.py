from alpha_engine.reference_loop.runner import run

def test_reference_loop(tmp_path):
    m=run(tmp_path/'alpha.db',tmp_path/'artifacts'); assert m['artifact_integrity'] is True; assert m['learning_auto_applied'] is False; assert m['score_total']=='0.9375'
