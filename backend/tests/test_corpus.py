from app.services import corpus as corpus_module
from app.services.corpus import find_token


def test_find_token_materializes_multi_level_stub_chain():
    corpus_module._CORPUS_CACHE.clear()
    token = find_token("classic", "qwen", "C_L9Q_S0_0_S1_0_S2_0_S3_0")
    assert token is not None
    assert token.token_id == "C_L9Q_S0_0_S1_0_S2_0_S3_0"
    assert token.text


def test_find_token_resolves_deep_eos_stub_token():
    corpus_module._CORPUS_CACHE.clear()
    eos_token_id = (
        "C_L9Q_S0_0_S1_0_S2_0_S3_0_S4_0_S5_0_S6_0_S7_0_S8_0_S9_0"
        "_S10_0_S11_0_S12_0_S13_0_S14_0_S15_0_S16_0_S17_0_S18_0_S19_0"
        "_S20_0_S21_0_S22_0_S23_0_EOS1"
    )
    token = find_token("classic", "qwen", eos_token_id)
    assert token is not None
    assert token.token_id == eos_token_id
    assert token.is_eos is True
