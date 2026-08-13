from api.scenes.schema import Layer, Narration, Scene


def test_layer_defaults_and_scene_carries_layers():
    layer = Layer(kind="headline", content="Photosynthesis")
    assert layer.region == "center" and layer.size == "md" and layer.depth == 1
    assert layer.frame is None
    scene = Scene(id="s0", narration=Narration(text="..."), layers=[layer])
    assert scene.layers[0].content == "Photosynthesis"
