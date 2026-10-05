"""Edit an image by instruction with FLUX.1 Kontext [dev] (GGUF Q5_K_S, fits a 12 GB GPU with CPU offload).

    <sana venv>\\Scripts\\python kontext_edit.py <image> <out.png> "<instruction>" [--steps 28] [--guidance 2.5]
        [--seed 0] [--width W --height H] [--long 1024]

Use it for what a text-to-image model cannot do: keep THIS character while changing the pose or the framing
("the same character standing in a neutral A-pose, arms 45 degrees down, full body, front view, plain white
background", "back view of the same character", "only the helmet of this character on a white background").
Output size defaults to the input's aspect ratio with the long side at --long.

Setup (no Hugging Face login needed): the transformer is QuantStack's GGUF; the text encoders, tokenizers and
VAE are the standard FLUX ones taken from shuttleai/shuttle-3-diffusion (Apache-2.0, not gated); the
transformer config and the scheduler settings of FLUX.1-dev are written out below because BFL's own repo is
gated. FLUX.1 Kontext [dev] itself is under BFL's non-commercial licence.
"""
import argparse, json, os, time
import torch
from PIL import Image
from diffusers import (FluxKontextPipeline, FluxTransformer2DModel, GGUFQuantizationConfig, AutoencoderKL,
                       FlowMatchEulerDiscreteScheduler)
from transformers import CLIPTextModel, CLIPTokenizer, T5EncoderModel, T5TokenizerFast

HERE = os.path.dirname(os.path.abspath(__file__))
COMP = os.path.join(HERE, "components")
GGUF = os.path.join(HERE, "flux1-kontext-dev-Q5_K_S.gguf")
CFG_DIR = os.path.join(HERE, "transformer_config")
FLUX_DEV_TRANSFORMER = {
    "_class_name": "FluxTransformer2DModel", "attention_head_dim": 128, "axes_dims_rope": [16, 56, 56],
    "guidance_embeds": True, "in_channels": 64, "joint_attention_dim": 4096, "num_attention_heads": 24,
    "num_layers": 19, "num_single_layers": 38, "out_channels": None, "patch_size": 1, "pooled_projection_dim": 768,
}

ap = argparse.ArgumentParser()
ap.add_argument("image")
ap.add_argument("out")
ap.add_argument("instruction")
ap.add_argument("--steps", type=int, default=28)
ap.add_argument("--guidance", type=float, default=2.5)
ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--width", type=int, default=0)
ap.add_argument("--height", type=int, default=0)
ap.add_argument("--long", type=int, default=1024, help="long side of the output when width/height are not given")
a = ap.parse_args()

t0 = time.time()
# Memory guard. On 2026-10-04 a run froze the whole PC (32 GB RAM, 37 GB commit limit): the 9 GB T5 encoder, the
# 8 GB transformer and everything else open did not fit. So: (1) refuse to start when RAM is short, (2) never
# hold the text encoder and the transformer at the same time: encode the prompt first, free the encoders, then
# load the transformer.
import ctypes, gc


def free_ram_gb():
    class MS(ctypes.Structure):
        _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong)] + [
            (n, ctypes.c_ulonglong) for n in ("ullTotalPhys", "ullAvailPhys", "ullTotalPageFile", "ullAvailPageFile",
                                              "ullTotalVirtual", "ullAvailVirtual", "ullAvailExtendedVirtual")]
    m = MS()
    m.dwLength = ctypes.sizeof(MS)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
    return m.ullAvailPhys / 2 ** 30, m.ullAvailPageFile / 2 ** 30


ram, commit = free_ram_gb()
print(f"MEMORY free RAM {ram:.1f} GB, free commit {commit:.1f} GB")
if ram < 13 or commit < 16:
    raise SystemExit("KONTEXT refused to start: needs about 13 GB of free RAM and 16 GB of free commit. Close some apps.")
os.makedirs(CFG_DIR, exist_ok=True)
with open(os.path.join(CFG_DIR, "config.json"), "w") as f:
    json.dump(FLUX_DEV_TRANSFORMER, f)
dt = torch.bfloat16
sched = FlowMatchEulerDiscreteScheduler(num_train_timesteps=1000, shift=3.0, use_dynamic_shifting=True, base_shift=0.5,
                                        max_shift=1.15, base_image_seq_len=256, max_image_seq_len=4096)
vae = AutoencoderKL.from_pretrained(COMP, subfolder="vae", torch_dtype=dt)
# stage 1: the prompt, with only the text encoders loaded
enc = FluxKontextPipeline(
    scheduler=sched, vae=vae, transformer=None,
    text_encoder=CLIPTextModel.from_pretrained(COMP, subfolder="text_encoder", torch_dtype=dt),
    tokenizer=CLIPTokenizer.from_pretrained(COMP, subfolder="tokenizer"),
    text_encoder_2=T5EncoderModel.from_pretrained(COMP, subfolder="text_encoder_2", torch_dtype=dt, low_cpu_mem_usage=True),
    tokenizer_2=T5TokenizerFast.from_pretrained(COMP, subfolder="tokenizer_2"))
enc.text_encoder.to("cuda")
enc.text_encoder_2.to("cuda")
with torch.no_grad():
    pe, ppe, _ = enc.encode_prompt(prompt=a.instruction, prompt_2=None, device="cuda")
pe, ppe = pe.to("cpu"), ppe.to("cpu")
del enc
gc.collect()
torch.cuda.empty_cache()
print(f"MEMORY after the prompt: free RAM {free_ram_gb()[0]:.1f} GB")
# stage 2: the image, with only the transformer and the VAE loaded
transformer = FluxTransformer2DModel.from_single_file(
    GGUF, quantization_config=GGUFQuantizationConfig(compute_dtype=dt), torch_dtype=dt, config=CFG_DIR)
pipe = FluxKontextPipeline(scheduler=sched, vae=vae, transformer=transformer, text_encoder=None, tokenizer=None,
                           text_encoder_2=None, tokenizer_2=None)
pipe.enable_model_cpu_offload()
img = Image.open(a.image).convert("RGB")
w, h = a.width, a.height
if not (w and h):
    s = a.long / max(img.size)
    w, h = int(round(img.width * s / 16)) * 16, int(round(img.height * s / 16)) * 16
out = pipe(image=img, prompt_embeds=pe.to("cuda", dt), pooled_prompt_embeds=ppe.to("cuda", dt), width=w, height=h,
           guidance_scale=a.guidance, num_inference_steps=a.steps,
           generator=torch.Generator("cpu").manual_seed(a.seed)).images[0]
out.save(a.out)
print(f"KONTEXT {a.out}: {w}x{h}, {a.steps} steps, {time.time() - t0:.0f}s, "
      f"peak VRAM {torch.cuda.max_memory_allocated() / 1e9:.1f} GB, free RAM at the end {free_ram_gb()[0]:.1f} GB")
