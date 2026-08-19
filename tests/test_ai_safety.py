from ai.safety import validate_llm_output


def test_ai_rejects_wrong_tax_figure():
    assert not validate_llm_output('Tax payable is PKR 100. [SRC-1]', {'tax_payable':416000}, ['SRC-1'])['valid']

def test_ai_rejects_unknown_citation():
    r=validate_llm_output('Tax payable is PKR 416,000. [BAD]', {'tax_payable':416000}, ['SRC-1'])
    assert not r['valid']

def test_ai_accepts_verified_structured_answer():
    r=validate_llm_output('Tax payable is PKR 416,000 under the verified rule. [SRC-1]', {'tax_payable':416000}, ['SRC-1'])
    assert r['valid']
