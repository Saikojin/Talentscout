# LLM Models Directory

Place your `.gguf` language model files in this directory (`llmworkbench/models/`).

## Recommended Models

You can download GGUF models directly from [Hugging Face](https://huggingface.co/models?search=gguf):

1. **Gemma 3 1B IT (Fast & Lightweight - Recommended Default)**
   - Filename: `gemma-3-1B-it-QAT-Q4_0.gguf`
   - Size: ~720 MB
   - Great for fast resume and cover letter synthesis.

2. **LFM 2.5 1.2B Thinking (Reasoning & Analysis)**
   - Filename: `LFM2.5-1.2B-Thinking-Q4_0.gguf`
   - Size: ~695 MB

3. **Gemma 4 Coding Q8 (Deep Technical Alignment)**
   - Filename: `gemma4-coding-Q8_0.gguf`
   - Size: ~12.6 GB (Requires GPU/ample RAM)

4. **Gemma 4 12B IT (Balanced Large Model)**
   - Filename: `gemma-4-12b-it-qat-q4_0.gguf`
   - Size: ~6.9 GB

---

## How It Works
* TalentScout will automatically detect any `.gguf` file placed in this folder and populate the **Model Selector** in the Dashboard top navigation.
* You can click **▶️ Start Local LLM** in the Dashboard to launch the model server on `http://localhost:8000`.
* The `.gitignore` in this repository automatically excludes all `.gguf` and binary files so they won't be pushed to git.
