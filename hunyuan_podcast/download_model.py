from modelscope.hub.snapshot_download import snapshot_download

snapshot_download(
    model_id="IndexTeam/IndexTTS-2",
    cache_dir="checkpoints",
    revision="master"
)
