id: conc_shed
name: the concentrate shed
owner: liandri
layer: boom
kind: hall
at: 18600 5400 300
size: 24 14 9
users: dock_gang hauliers lindqvist
doors: front:roller back:roller left:personnel
bays: front
roof: pitched
wear: 0.2
lit: yes
provides: goods conc
needs: power workers
ref: processing_hall

Placed by the chain: at the dock, where the slurry pipeline ends at the pump station and the quay begins
(engineer s.1: [conc_shed + filter] at the dock -> [shiploader] on the quay -> ship; -> trucks -> [cargo_pad]).
24 x 14 x 9 m, a filter press on a mezzanine over the stockpile, the roller door on the quay side for the
loader's feed belt, the back door for the trucks to the cargo pad. The last stage of the conc chain in
systems.py; it hands the concentrate on to the shiploader as goods.

Everything the island is worth is a black heap on this floor for two days a month. The dock gang shovels
the corners the loader cannot reach and goes to the Tin Bar black to the elbows; the company weighs the
heap twice, once before the ship and once after, and the difference is the foreman's problem.
