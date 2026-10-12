# 10-12: Kontext paints each building's front + side together (one canvas) so the side matches the front, then splats.
cd ${WORK:-.}
K="$KONTEXT_PY $KONTEXT_DIR/kontext_edit.py"
P=$HUNYUAN_PY
mkdir -p sdf/paint
py -3.13 sdf/pair.py join geo/kA_input_front.png geo/kA_input_right.png sdf/paint/kA_pair_in.png
$K sdf/paint/kA_pair_in.png sdf/paint/kA_pair.png "Paint the right building in exactly the same painted style, colours, stone trim, window frames and roof colour as the left building. Keep the left building unchanged. Keep both outlines and shapes exactly. White background." --steps 24 --guidance 4 --long 1024
py -3.13 sdf/pair.py split sdf/paint/kA_pair.png sdf/paint/kA_front.png sdf/paint/kA_right.png
for m in candy tower spire booth; do
  py -3.13 sdf/pair.py join mix/lines/${m}_front.png mix/lines/${m}_right.png sdf/paint/${m}_pair_in.png
  $K sdf/paint/${m}_pair_in.png sdf/paint/${m}_pair.png "These are the front and side views of the same storybook building. Paint both as one consistent hand-painted illustration with warm colours, same materials and colours on both views. Keep every pencil line, window, door and the exact outline of each view. White background." --steps 24 --guidance 4 --long 1024
  py -3.13 sdf/pair.py split sdf/paint/${m}_pair.png sdf/paint/${m}_front.png sdf/paint/${m}_right.png
done
$P sdf/splat.py geo/kA.glb sdf/paint/kA_front.png sdf/paint/kA_right.png sdf/splat2_kA.png
for m in candy tower spire booth; do $P sdf/splat.py mix/${m}_lines.glb sdf/paint/${m}_front.png sdf/paint/${m}_right.png sdf/splat2_${m}.png; done
echo ALLDONE
