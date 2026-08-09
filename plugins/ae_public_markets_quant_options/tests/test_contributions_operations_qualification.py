from ae_public_markets_quant_options.contributions import dashboard_contributions, cli_contributions
from ae_public_markets_quant_options.operations import operation_descriptors
from ae_public_markets_quant_options.qualification import run_fixture_reference_loop


def test_dashboard_and_cli_contributions_are_namespaced():
    assert all(x.contribution_id.startswith("pmqo.") for x in dashboard_contributions())
    assert all(x.command.startswith("pmqo ") for x in cli_contributions())


def test_operations_are_declarations_not_scheduler():
    ops=operation_descriptors()
    assert len(ops)>=8
    assert all(x.operation_type.startswith("pmqo.") for x in ops)
    assert all(x.permission_scope.startswith("public_markets.") for x in ops)


def test_fixture_reference_loop_reaches_outcome():
    r=run_fixture_reference_loop()
    assert (r.bars,r.signals,r.opportunities,r.paper_candidates,r.fills,r.outcomes)==(35,1,1,1,1,1)
