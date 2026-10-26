{
  qwen = {
    family = "qwen";
    quant = "IQ3_XXS";
    serverName = "qwen3.8-flash-next-iq3_xxs";
    displayName = "Qwen3.8 Flash Next IQ3_XXS";
    context = 65536;
    output = 16384;
  };

  whisper = {
    url = "https://huggingface.co/ggerganov/whisper.cpp/resolve/5359861c739e955e79d9a303bcbc70fb988958b1/ggml-small.bin";
    sha256 = "1be3a9b2063867b937e64e2ec7483364a79917e157fa98c5d94b5c1fffea987b";
  };
}
