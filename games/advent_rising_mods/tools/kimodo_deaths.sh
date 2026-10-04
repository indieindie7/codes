#!/bin/bash
# Generates the death motions in death_prompts.txt with Kimodo (3 takes each) into
# Documents/Tools/kimodo/out/deaths. Needs the GPU for about 45 s per prompt.
K=/c/Users/john/Documents/Tools/kimodo
HERE="$(cd "$(dirname "$0")" && pwd)"
export KIMODO_TEXT_ENCODER_LOCAL="C:/Users/john/Documents/Tools/kimodo/models/KIMODO-Meta3_llm2vec_NF4" TEXT_ENCODER_MODE=local PYTHONIOENCODING=utf-8
mkdir -p "$K/out/deaths"; cd "$K"
grep -v '^#' "$HERE/death_prompts.txt" | while IFS='|' read -r name prompt secs; do
  [ -z "$name" ] && continue
  [ -n "$1" ] && [ "$1" != "$name" ] && continue
  echo "== $name"
  venv/Scripts/python.exe -m kimodo.scripts.generate "$prompt." --model Kimodo-SOMA-RP-v1.1 --duration "$secs" --num_samples 3 --seed 7 --no-postprocess --output "out/deaths/$name" 2>&1 | grep -E "Error|error|Saving|Traceback" | cut -c1-200
done
ls "$K/out/deaths"
echo BATCH DONE
