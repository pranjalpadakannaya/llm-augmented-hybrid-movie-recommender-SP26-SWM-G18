def test_imports():
    import backend.models.gru4rec as gru4rec
    import backend.models.kg as kg
    import backend.models.occf as occf

    assert kg is not None
    assert gru4rec is not None
    assert occf is not None
