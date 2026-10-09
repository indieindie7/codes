# Avalon redesign, 2026-10-09: the reference board

> **Reference only.** Nothing here was downloaded. None of it ships in a mod, and nothing is traced or copied into
> textures. The licences are copied as each role file states them, including its "not stated", "check", "not
> fetched" and *(summary)* markers. Spot-check each licence on its page before any use beyond private reference.

Merged from [writer.md](writer.md) s.7 (W1-W14), [director.md](director.md) s.5 (R1-R15),
[engineer.md](engineer.md) s.7 (E1-E14), [level_designer.md](level_designer.md) s.7 (L1-L13) and
[artist.md](artist.md) s.8 (A1-A25). Duplicates are merged into one entry with every role that cited it. Where two
roles cited different pages on the same subject, both pages are listed in the one entry, each with its own licence.
*(summary)* = the engineer took the fact from a search summary, not a full read of the page.

Entry format: **title**, then the pages (URL, source, licence), what fits, what it is for, and the roles.

---

## 1. Tower and landmark (the Liandri temple, the company gate)

**Heroico Colegio Militar, Mexico City (1976)**
- https://en.wikipedia.org/wiki/Agust%C3%ADn_Hern%C3%A1ndez_Navarro ; https://archive.pinupmagazine.org/articles/interview-agustin-hernandez-sci-architecture-mexico-suleman-anaya
- Source: Agustín Hernández Navarro with Manuel González Rul. Licence: Wikipedia text CC BY-SA; photos per file; PIN-UP not stated.
- Fits: a brutalist campus planned as a pre-Columbian ceremonial centre; battered masses with modern boxes on top.
- For: the Liandri crane-temple, the company core plan, the company gate. Roles: artist (A1).

**Tikal Structure 5C-49, talud-tablero**
- https://uncoveredhistory.com/guatemala/tikal/tikal-talud-tablero-temple-5c-49/
- Source: Uncovered History. Licence: not stated.
- Fits: the talud (slope) + tablero (framed overhang) profile.
- For: `B_talud` / `B_tablero`, terrace faces, temple tiers. Roles: artist (A2).

**Pyramid of the Sun, Teotihuacan**
- https://www.worldhistory.org/image/3631/pyramid-of-the-sun-teotihuacan/
- Source: World History Encyclopedia. Licence: check the page (WHE images are often CC BY-NC-SA).
- Fits: terrace proportions, levels joined by stairs, the scale of a mass you climb.
- For: the plinth and terrace stepping ratios. Roles: artist (A3).

**Ziggurat of Ur**
- https://en.wikipedia.org/wiki/Ziggurat_of_Ur
- Source: Wikipedia. Licence: CC BY-SA text; the photo per its Commons file.
- Fits: three monumental stairs converging on a gate; a battered brick mass; history on the surface.
- For: `B_stair3` at the company gate (beat 3, smallness). Roles: artist (A4).

**Sci-fi Planetary Mining Installation**
- https://r_bago.artstation.com/projects/Nq1Jog
- Source: r_bago (ArtStation). Licence: not stated.
- Fits: machinery grafted onto a brutalist megastructure.
- For: the crane-temple's top and its jibs. Roles: artist (A5).

**UEA "Ziggurats", Norfolk and Suffolk Terraces (1962-68)**
- https://bluecrowmedia.com/blogs/news/brutalist-building-denys-lasdun-university-of-east-anglia ; https://sosbrutalism.org/cms/15888753
- Source: Denys Lasdun (architect); photo Simon Phipps. Licence: © Blue Crow Media, all rights reserved.
- Fits: stepped concrete down a slope, each roof the next one's terrace, walkways to a spine block.
- For: `liandri_tower`'s stepped base; terraced company housing. Roles: writer (W9).

**Sparth: one hard hero form against soft ground; black as a framing element**
- https://www.destructoid.com/?p=151415 ; https://halopedia.org/Sparth (writer: © 343/Microsoft; pages ©)
- https://parkablogs.com/content/book-review-art-of-halo-5-guardians (director: Book art © Microsoft (reference only))
- Source: Nicolas "Sparth" Bouvier (343 Industries); *The Art of Halo 5* (review).
- Fits: one geometric hero against soft terrain (the temple must be the only stepped shape); black used to frame scenes.
- For: the temple's silhouette on the summit; cutting the duplicate crane towers; the dark frame of F4/F5. Roles:
  writer (W14), director (R13).

**Half-Life 2 Citadel design evolution**
- https://www.combineoverwiki.net/wiki/Citadel_design_evolution
- Source: Viktor Antonov, Dhabih Eng, Eric Kirchmer (Valve). Licence: Concept art © Valve (reference only).
- Fits: a wall at street level with the landmark rising over it; the landmark far off from a platform.
- For: F10 smallness; F8 the glimpse over the roofs. Roles: director (R11).

---

## 2. Company core (housing, the store, identity)

**Russell Lee, company store, Westland PA, 1946 (NAID 540334)**
- https://www.docsteach.org/documents/document/scene-in-front-of-company-store
- Source: Russell Lee, 1946 coal survey (US National Archives, RG 245). Licence: Public domain, free of known copyright restrictions.
- Fits: the company store as the town's living room and bank.
- For: `company_store`, the PA's scrip lines. Roles: writer (W1).

**Russell Lee, typical home for miners, Lynch KY, 1946 (NAID 541404)**
- https://www.docsteach.org/documents/document/typical-home-for-miners-us-coal-coke-company ; series: https://prologue.blogs.archives.gov/?p=36929
- Source: Russell Lee / National Archives. Licence: Public domain (NARA DocsTeach records).
- Fits: identical company housing, cost-cut material, family life in company stock.
- For: `dorm`, `staff_houses`, Tin Row families. Roles: writer (W2).

**Hashima (Gunkanjima): the company island, exteriors**
- https://www.pakutaso.com/en/20190326079post-20005.html (artist: PAKUTASO's free-use terms (read them before any use beyond reference))
- https://www.pakutaso.com/en/2019035507831.html (director: PAKUTASO free licence (commercial and non-commercial, no attribution needed, Terms of Use apply)), susi-paku: the lighthouse seen through Building No. 31
- https://cabinetmagazine.org/issues/7/burke-gaffney.php (engineer: not stated (©)), Burke-Gaffney in Cabinet *(summary)*
- Fits: concrete dorm blocks stacked against each other on a rock in the sea; a landmark framed through a block;
  9.9 m² single rooms with shared baths; housing on one side, the mine on the other.
- For: dorms, the core's density, the sea wall; F13 the dorm gallery's end; F1 mullions; the dorm room module and E21.
  Roles: artist (A12), director (R1), engineer (E7). (Interiors: see 6.4.)

**Unreal Tournament 2004 (the Liandri Archives)**
- https://unrealarchive.org/wikis/the-liandri-archives/Unreal_Tournament_2004.html
- Source: BeyondUnreal / Unreal Archive wiki. Licence: wiki text per the site; game art © Epic.
- Fits: the company's in-universe identity; the 2003-04 Unreal look (team colours, chrome, lit strips).
- For: the LIANDRI wordmark, signage, checking the palette against the era. Roles: artist (A25).

---

## 3. Works and plant

**Kennecott mill and company town, Alaska**
- https://home.nps.gov/wrst/learn/historyculture/kennecott-mines-national-historic-landmark.htm (engineer: US Government work (NPS text usually public domain; check each photo's credit)) *(summary)*
- https://www.loc.gov/item/ak0476 (engineer: HAER records are usually "no known restrictions" (check the record)), HAER AK-1-D measured drawings *(summary)*
- https://sah-archipedia.org/node/7575 ; https://www.valdezmuseum.org/kennecott/ (artist: not stated (NPS photos are often public domain; check per image))
- Fits: a 14-storey mill stepping down the mountain under the tramway terminal; measured floor levels and chutes;
  a town painted red with the hospital the only white building; the rail bed as the spine.
- For: hall_a/hall_b stepped on 2 pads; hall_b's section; the transfer tower; the one pale building. Roles: engineer
  (E1, E2), artist (A9).

**Zeche Zollverein, Essen**
- https://www.zollverein.de/app/uploads/2018/02/UNESCO-Welterbe-Zollverein-Imagebroschüre-englisch.pdf (engineer: not stated (©)) *(summary)*
- https://www.baukunst-nrw.de/en/projects/Objekt-Highlight--183.htm (artist: not stated), Shaft XII
- https://commons.wikimedia.org/wiki/File:Rolltreppe_Zeche_Zollverein.JPG (director: CC BY-SA 3.0), Martin Falbisoner, the OMA escalator
- Fits: right-angle axes and conveyor bridges; one dominant winding tower on one line; a long orange-lit diagonal
  climbing into a dark mass.
- For: `conveyor_gallery`, `transfer_tower`, the ore line as datum; hall_b, the generator house; F10 the stair
  cut-in. Roles: engineer (E4), artist (A7), director (R4).

**Bernd and Hilla Becher, industrial typologies**
- https://smarthistory.org/?p=66679 (gallery: https://fraenkelgallery.com/artists/bernd-and-hilla-becher)
- Source: Smarthistory. Licence: Smarthistory text CC BY-NC-SA; the photos are © the estate.
- Fits: one type, many variants, form dictated by process.
- For: the kit's variation rules; silos, water tower, cooling towers; a silhouette check sheet. Roles: artist (A6).

**Völklingen Ironworks**
- https://www.erih.net/i-want-to-go-there/site/world-heritage-site-voelklingen-iron-works
- Source: ERIH. Licence: not stated.
- Fits: rusted steel, catwalks 30 m up, plants reclaiming the plant.
- For: catwalks, hall_c (dead), abandoned wear. Roles: artist (A8).

**Early Hedley townsite and stamp mill**
- https://livingsignificantly.ca/?p=1056
- Source: local history site. Licence: not stated. *(summary)*
- Fits: a mill built so ore moves through by gravity; mine high, mill on the slope, town low.
- For: the chain's z-order (E12'). Roles: engineer (E3).

**Longyearbyen coal cableway centre**
- https://www.spitsbergen-svalbard.com/photos-panoramas-videos-and-webcams/spitsbergen-panoramas/longyearbyen/coal-cableway-centre-taubanesentrale.html
- Source: spitsbergen-svalbard.com (Rolf Stange). Licence: not stated. *(summary)*
- Fits: the hub where mine lines meet before the harbour; towers down the valley.
- For: `transfer_tower` / B_ctower angle station; the overland run. Roles: engineer (E5).

**Gateway Pacific Terminal operations**
- https://www.ezview.wa.gov/pr/Portals/_1357/images/default/20110428%20GPT%20Terminal%20Operations%20for%20MAPT%20Final(1).pdf
- Source: Washington State. Licence: state public record (not stated). *(summary)*
- Fits: transfer towers, enclosed galleries on a trestle, a shiploader.
- For: `shiploader` + `conc_shed` on the quay; E23. Roles: engineer (E8).

**911 Metallurgist: flotation plant design**
- https://www.911metallurgist.com/flotation-plant-design
- Source: 911 Metallurgist. Licence: not stated (©). *(summary)*
- Fits: the flowsheet: crushing, fine ore bin, grinding, cells, thickener, filters over the concentrate bins.
- For: hall_a/hall_b machinery order; the thickener; the filter over the bin. Roles: engineer (E12).

**Edward Burtynsky, *Oil***
- https://metiviergallery.com/exhibitions/110/
- Source: Metivier Gallery. Licence: © the artist.
- Fits: refinery architecture and tank farms at landscape scale.
- For: the tank farm, the fuel depot, the works from the window. Roles: artist (A10).

**Edward Burtynsky, *Shipbreaking #1, Chittagong***
- https://collections.remaimodern.org/objects/4554/shipbreaking-1-chittagong-bangladesh
- Source: Remai Modern. Licence: ©.
- Fits: hulls cut open, rust in low gold light, tiny figures against huge steel.
- For: the wreck, the dead rig, the dusk rust palette. Roles: artist (A11).

**Offshore oil platform at sunset, Huntington Beach**
- https://www.usgs.gov/media/images/oil-drilling-platform-offshore-huntington-beach-california
- Source: Pete Markham, USGS Pacific Coastal and Marine Science Center. Licence: Public domain.
- Fits: a rig as pure silhouette on a warm band.
- For: F14 the rigs; F5's horizon band. Roles: director (R2).

**Factory silhouette against a dusk sky**
- https://unsplash.com/de/fotos/industriegebaude-silhouette-gegen-den-dammerungshimmel-xFbDJRuLz4c
- Source: Muhammad Rasel. Licence: Unsplash License.
- Fits: the plant as one flat dark shape on a gradient.
- For: F1/F6, the plant's two-value silhouette test. Roles: director (R7).

---

## 4. Shanty (Tin Row, Ship Row)

**Kowloon Walled City, 1986-92**
- https://mplus.org.hk/en/magazine/exploring-kowloon-walled-city-photographic-journey (writer: © photographers/M+; artist: ©)
- https://hongkongfp.com/2019/10/13/hkfp-lens-city-darkness%e2%81%a0-greg-girard-ian-lambot-revisit-kowloons-long-gone-walled-city/ (writer; not fetched: 1854.photography gave 403)
- Source: Greg Girard and Ian Lambot, "City of Darkness" (1993) / "Revisited" (2014).
- Fits: an organic megastructure adapted by its residents: wiring, workshops in homes, light from small sources.
- For: Tin Row interiors (`shanty_a/b/c`), the transformation rule, the cables off the dock lights, the summit ring.
  Roles: writer (W11), artist (A14).

**Portraits from Above: Hong Kong's informal rooftop communities**
- https://halfletterpress.com/portraits-from-above-hong-kongs-informal-rooftop-communities/
- Source: Rufina Wu & Stefan Canham. Licence: ©.
- Fits: self-built huts on formal concrete, with measured drawings.
- For: shacks on the company terraces' roofs, `B_shack`, shanty block plans. Roles: artist (A15).

**Makoko, Lagos: living on stilts**
- https://ripplesnigeria.com/living-on-stilts-75-unforgettable-images-of-makoko-will-it-survive-sanwo-olus-smart-city-plan
- Source: Ripples Nigeria. Licence: not stated.
- Fits: corrugated iron, planks and bamboo on stilts over water.
- For: Ship Row, the old boat landing, `B_stilts`. Roles: artist (A16).

**Shanty Megastructures, Olalekan Jeyifous**
- https://www.dezeen.com/2016/08/09/shanty-megastructures-lekan-jeyif-conceptual-images-lagos-nigeria/
- Source: Dezeen. Licence: ©.
- Fits: a shanty climbing a vertical megastructure in patchwork metal and plastic.
- For: the shanty ring round the summit; shacks on the temple's lower terraces. Roles: artist (A17).

---

## 5. Authority

**GDR border command tower, Nieder Neuendorf (1987)**
- https://www.dark-tourism.com/index.php/1202-watchtower-nieder-neuendorf
- Source: Peter Hohenhaus, dark-tourism.com. Licence: © Peter Hohenhaus.
- Fits: a small state post: field telephone, searchlight control, binoculars, a holding cell.
- For: `checkpoint` (Nkemelu's hut); Hawkins's binoculars. Roles: writer (W13).

(The Authority's command room is in 6.1.)

---

## 6. Interiors

### 6.1 Command room and control rooms

**Chornobyl NPP Control Rooms 3 and 4**
- https://www.thisiscolossal.com/2020/10/darmon-richter-chernobyl/ ; https://www.gerdludwig.com/no-end-in-sight
- Source: Darmon Richter ("Chernobyl: A Stalkers' Guide", FUEL); Gerd Ludwig. Licence: © Richter/FUEL, shared with permission; © Gerd Ludwig, use without permission prohibited.
- Fits: a control room whose power has gone elsewhere; walls of dead instruments; one important button.
- For: `tower:command_room` (Oduya's board, the dead consoles). Roles: writer (W8).

**Gravelines nuclear plant control room**
- https://energytransition.org/gravelines
- Source: Serge Ottaviani (photo). Licence: director: CC BY-SA 3.0 (repost; the page says modified); artist: CC BY-SA 3.0.
- Fits: long, low console rows; the mimic diagram; operators' posture.
- For: the command room's consoles (kept under the glass); the plant control room. Roles: director (R6), artist (A19).

**Power station control room, Trafford Park**
- https://collection.sciencemuseumgroup.org.uk/documents/aa110015087 (see also aa110015091)
- Source: Science Museum Group. Licence: CC BY-NC-SA 4.0.
- Fits: meters, switches, a wall of panels.
- For: the command room's consoles (`console`). Roles: artist (A18).

**AusIMM: designing a control room**
- https://www.ausimm.com/bulletin/bulletin-articles/mine-monitoring-and-control-designing-a-control-room/
- Source: AusIMM Bulletin. Licence: not stated. *(summary)*
- Fits: 3-4 screens per console; about 7 x 5 m minimum for one controller; a raised floor.
- For: the plant control room (engineer s.2.3, D10). Roles: engineer (E9).

**ABB central control rooms for mining**
- https://new.abb.com/control-rooms/references/central-control-rooms-for-mining-and-mining-and-bulk-material-handling
- Source: ABB. Licence: not stated (©). *(summary)*
- Fits: consoles and a video wall; consoles face the process.
- For: the plant control room's console order (sorted by bearing). Roles: engineer (E10).

### 6.2 The mess

**Pyramiden: the cafeteria and the company town**
- https://www.urbex.nl/pyramiden-cafeteria/ ; https://www.smithsonianmag.com/travel/soviet-ghost-town-arctic-circle-pyramiden-stands-alone-180951429/ (writer: © site, no licence given), urbex.nl author (unnamed, visited 2018); Smithsonian
- https://cruisehandboka.npolar.no/en/isfjorden/pyramiden.html (engineer: not stated), Norwegian Polar Institute *(summary)*
- Fits: one giant mural over long tables; a mining town zoned vertically: mine above, plant and pier below, quarters and mess.
- For: `mess` (the company mural as the room's sentence); dorm, mess and quay relations. Roles: writer (W5), engineer (E6).

**Colliery canteens: Caerau (1954) and Lynemouth (1950s)**
- https://museum.wales/collections/online/object/958afac8-f73f-345b-a787-f78cfa0503a0 ; https://www.ncm.org.uk/?p=4405
- Source: Museum Wales (item 2009.3/5819); National Coal Mining Museum (Harold White, NCB). Licence: check each record.
- Fits: rows of tables, a serving hatch, tiled walls.
- For: the mess. Roles: artist (A20).

**PKL remote-site camp kitchens (TW 400 dining)**
- https://www.pkl.co.uk/products/transworld-kitchens/kitchens-and-camps/tw-400-dining/
- Source: PKL (vendor). Licence: not stated (©). *(summary)*
- Fits: zoning from production to warewash, stores, servery and dining.
- For: the mess layout (engineer s.2.5). Roles: engineer (E13).

**Edward Hopper, *Nighthawks* (1942)**
- https://www.artic.edu/artworks/111628/nighthawks
- Source: Art Institute of Chicago. Licence: © Heirs of Josephine N. Hopper (licensed by the Whitney): reference only.
- Fits: the only lit room on a dark street; figures seen through glass.
- For: F9 / I3, the mess window. Roles: director (R15).

### 6.3 Processing halls and signage

**The Nostromo, Ron Cobb (Domus, "the menacing architecture of Alien")**
- https://www.domusweb.it/en/news/2025/09/19/alien-design-nostromo.amp.html
- Source: Domus. Licence: artist: ©; writer: not fetched: 403.
- Fits: a ship as an orbital refinery: pipes, valves, grilles and cables exposed; a sign system.
- For: a Liandri icon set for doors, hazards and rooms; the halls and pump houses. Roles: artist (A22), writer (W7).

(The hall sections themselves: Kennecott HAER and 911 Metallurgist in section 3.)

### 6.4 Dorms

**Hashima interiors, Andrew Meredith**
- https://old.designcurial.com/news/hashima---the-abandoned-japanese-island-4199747/
- Source: Andrew Meredith (meredithphoto.com), Designcurial. Licence: writer: © all rights reserved; artist: ©.
- Fits: the Nikkyu miners' flats, the lightwell, kitchens left mid-use, the hospital's operating theatre.
- For: `dorm` / `dorm_b` interiors, dorm C (abandoned), the clinic. Roles: writer (W3), artist (A13).

**Single cabins on Gullfaks A**
- https://gullfaks.industriminne.no/en/single-cabins-on-gullfaks-a-a-crucial-choice-for-the-offshore-work-environment/
- Source: photo Shadé B. Martins / Norwegian Petroleum Museum. Licence: © Norsk Oljemuseum.
- Fits: offshore bunk history, from eight-man cabins to single ones; Avalon going back to four to a room.
- For: `dorm_b` (rig crews), `new_rig` quarters. Roles: writer (W4).

### 6.5 Pump house

**Belmont desalination project description**
- https://www.hunterwater.com.au/documents/assets/src/uploads/documents/Belmont-Desalination/Environmental-assessments/Report-5-BDRDP-D-Project-Description.PDF
- Source: Hunter Water. Licence: not stated. *(summary)*
- Fits: a wet well with screens and pump housing; an intake pipeline.
- For: `pump_house` + `intake`. Roles: engineer (E11).

### 6.6 The drain (culvert and sluice gallery)

**G-Cans, Metropolitan Area Outer Underground Discharge Channel**
- https://metropolisjapan.com/g-cans/ (writer: © Metropolis Japan, all rights reserved), photos and text Tamatha Roman
- https://interestingengineering.com/tokyos-futuristic-underground-flood-system (artist: ©), photos Joe Nishizawa
- Fits: giant pillars in a dim tank, puddles with reflections, light from above, a drop-off at one end.
- For: `drain`, the sluice gallery, `B_pillar` (scaled down). Roles: writer (W12), artist (A21).

**Lagoon Drain, Brisbane ("Dark Days")**
- https://commons.wikimedia.org/wiki/File:Lagoon_Drain_-_Brisbane_-_Dark_Days_(16419817739).jpg
- Source: "darkday" (Flickr). Licence: CC BY 2.0.
- Fits: a figure black against a storm-drain outflow, the tunnel as the dark frame.
- For: F11 / I6, the culvert reveal. Roles: director (R3).

### 6.7 Catwalks, stairs and rails

**Structural component of walkway at Gulf Foundation (c. 1970)**
- https://digitalcommons.usf.edu/gandy/5945
- Source: George "Skip" Gandy IV. Licence: CC BY 3.0 (the page's badge says BY-NC-SA: treat it as reference only).
- Fits: grated walkway, bolted brackets, railings up close.
- For: F5 / I2, the grating and rails. Roles: director (R5).

**OSHA 1910.25 (stairs) and 1910.29 (guardrails)**
- https://www.osha.gov/laws-regs/regulations/standardnumber/1910/1910.25 ; https://www.osha.gov/laws-regs/regulations/standardnumber/1910/1910.29
- Source: US OSHA. Licence: US Government work (public domain). *(summary)*
- Fits: riser and tread limits; guardrail 42 in top, mid-rail halfway.
- For: `stair_flight`, `catwalk` rails (scaled up for the game). Roles: engineer (E14).

### 6.8 Liandri House (the exchange hall)

**National Assembly of Bangladesh, Dhaka**
- https://archeyes.com/bangladeshs-national-parliament-house-by-louis-kahn-a-masterpiece-of-modern-architecture/ ; https://www.atlasobscura.com/places/national-assembly-of-bangladesh
- Source: Louis I. Kahn (architect). Licence: © page photographers.
- Fits: monumental concrete, huge cut-outs as light wells, top-lit voids; power as mass and light.
- For: the empty, top-lit exchange hall (D4); the battered gate wall. Roles: writer (W10).

---

## 7. Light, mood and film

**Outland (1981), the Con-Am 27 mining colony**
- https://en.wikipedia.org/wiki/Outland_(film) ; https://moriareviews.com/sciencefiction/outland-1981.htm
- Source: production design Philip Harrison, art direction Malcolm Middleton. Licence: film © (Ladd Co./Warner); pages ©.
- Fits: the company-town sci-fi: cage bunks, mess hall, bar, a marshal the company tolerates.
- For: `dorm_b`, `mess`, `tin_bar`; Hawkins and Vask as the tolerated law. Roles: writer (W6).

**Aliens (1986), Hadley's Hope**
- https://avp.fandom.com/wiki/Peter_Lamont (writer: film © 20th Century; fan wiki CC BY-SA text, images vary)
- https://www.avpcentral.com/hadleys-hope-colony (director: Fan wiki; film © 20th Century (reference only))
- Source: production design Peter Lamont.
- Fits: a prefab company colony with families, run from one ops room; wind and rain; a tunnel to the processor.
- For: the prefab kit read, `plant_office`; F6 storm; I6 the culvert as the storm-proof link. Roles: writer (W7),
  director (R14).

**Roger Deakins, *Blade Runner 2049***
- https://neiloseman.com/roger-deakins-oscar-winning-cinematography-blade-runner-2049/
- Source: Neil Oseman. Licence: Article; film frames are copyrighted (reference only).
- Fits: smog and rain reduce people to silhouettes; motivated light from moving water.
- For: F5, F6; I1 motivated light. Roles: director (R8).

**Roger Deakins / Denis Villeneuve, *Sicario***
- https://xsmultimedia.com/2022/07/15/film-and-shadow-the-power-of-silhouettes-with-cinematographer-roger-deakins/ ; https://www.motionpictures.org/2015/10/sicario-reunites-director-denis-villeneuve-cinematographer-roger-deakins/
- Licence: Articles; frames copyrighted (reference only).
- Fits: silhouettes against a red horizon at dusk; the storm sky as a character.
- For: F5 the lone figure; the sunset band in the colour script. Roles: director (R9).

**Tarkovsky, *Stalker* (1979)**
- https://velveteyes.net/?p=6698
- Source: Stan Lamontagne. Licence: Article; frames copyrighted (reference only).
- Fits: shot at dusk with the sky held down; flooded rooms, seeping walls, rain indoors.
- For: I6 the culvert, I7 the pump house; "cheat the sky down" for F5. Roles: director (R10).

**Firewatch, GDC 2015 (Jane Ng / Olly Moss)**
- https://www.thumbsticks.com/gdc-2015-the-art-of-firewatch
- Source: Campo Santo. Licence: Article; art © Campo Santo (reference only).
- Fits: fog in coloured layers; a colour script per story moment; flat shapes with strong silhouettes.
- For: the colour script (director s.3); F1's layers. Roles: director (R12).

**Simon Stålenhag, machines in the landscape**
- https://amp.cnn.com/cnn/style/article/simon-stalenhag-sci-fi-art
- Source: CNN Style. Licence: © the artist.
- Fits: huge machines as forgotten neighbours; small lone figures; observed light.
- For: the dead rig, the conveyor towers on the hills, the lone figure (beat 4). Roles: artist (A23).

**Serial Experiments Lain and power lines**
- https://www.atlasobscura.com/articles/why-power-lines-anime-electrical-infrastructure.amp
- Source: Atlas Obscura. Licence: ©.
- Fits: cables and poles as atmosphere; the hum.
- For: power lines across the shanty, pylons on the spine, the soundscape. Roles: artist (A24).

(Also see Sparth in section 1. Reference zero for every frame is the user's own peak frame,
design-refs/avalon_peak_frames/catwalk_dusk_silhouette.png.)

---

## 8. Level design

**Rrajigar Mine (Unreal)**
- https://unrealarchive.org/wikis/the-liandri-archives/Rrajigar_Mine.html
- Source: The Liandri Archives (Unreal Archive); map by Cliff Bleszinski. Licence: CC BY-SA 3.0 (stated).
- Fits: the first Skaarj: corpse corridor, barriers close, lights die from the far end, red light, a solo Skaarj, supply alcoves.
- For: the sluice gallery reveal (level designer s.4). Roles: level designer (L1).

**NyLeve's Falls (Unreal)**
- https://unrealarchive.org/wikis/the-liandri-archives/NyLeve's_Falls.html
- Source: The Liandri Archives; map by Juan Pancho Eekels. Licence: CC BY-SA 3.0 (stated).
- Fits: calm outdoor stretches alternating with interior fights; dark inside to bright outside.
- For: the whole route's interior/exterior rhythm. Roles: level designer (L2).

**The Level Design Book: layout typology**
- https://book.leveldesignbook.com/process/layout/typology
- Source: Robert Yang et al. Licence: CC BY-NC-SA 4.0 (stated).
- Fits: combat bowl, ring-around-the-rosie, hub-and-spoke, loopback, string of pearls.
- For: E3 (bowl), I2 (loops), the works loop. Roles: level designer (L3).

**The Level Design Book: encounter design**
- https://book.leveldesignbook.com/process/combat/encounter
- Source: Robert Yang et al. Licence: CC BY-NC-SA 4.0.
- Fits: footholds, one-way commits, the enemy palette table.
- For: E1's foothold, the sluice commit, the E3 brawl. Roles: level designer (L4).

**Half-Life 2 developer commentary**
- https://combineoverwiki.net/wiki/Developer_commentary/Half-Life_2
- Source: Combine OverWiki, transcribing Valve's commentary. Licence: not stated on the fetched page (check before quoting).
- Fits: rest stops between pressure; a reveal framed by the street; the canals' drainage.
- For: I3 the drain, the post-fight relax, E4's drop-pod sightline. Roles: level designer (L5).

**Jeff Orkin, "Three States and a Plan: The A.I. of F.E.A.R." (GDC 2006)**
- https://pages.cs.wisc.edu/~dyer/cs540/handouts/gdc2006_orkin_jeff_fear.pdf
- Source: Monolith, course copy. Licence: author's copyright.
- Fits: furniture for cover, multiple entries; apparent flanking from cover-seeking.
- For: I2 side doors and office stair, I4 tables, E2. Roles: level designer (L6).

**Damian Isla, "Building a Better Battle: The Halo 3 AI Objectives System"**
- https://web.cs.wpi.edu/~rich/courses/imgd4000-d09/lectures/halo3.pdf
- Source: Bungie, WPI course copy. Licence: Bungie's copyright.
- Fits: hold, fallback, last stand; snipers and dropships as spice.
- For: E2 (barricade -> door -> roof), E4 (terraces), the E3 rim sniper. Roles: level designer (L7).

**Killzone's AI: Dynamic Procedural Tactics (GDC Europe 2005)**
- https://www.guerrilla-games.com/media/News/Files/gdce05_killzone_ai.pdf
- Source: Arjen Beij and Remco Straatman (Guerrilla). Licence: Guerrilla's copyright.
- Fits: positions scored by lines of fire and cover over a waypoint graph fine enough for cover.
- For: PathNodes on both sides of each cover piece. Roles: level designer (L8).

**Doom (2016), Lazarus Labs deconstructed**
- https://blog.playstation.com/archive/2017/05/12/classic-levels-deconstructed-the-beautiful-brutality-of-dooms-lazarus-labs
- Source: PlayStation Blog with Hugo Martin, Marty Stratton, Jerry Keehan (id). Licence: publisher's copyright.
- Fits: sightline breaks; dead-end halls linked into loops.
- For: I2's aisle loops, E1's container yard. Roles: level designer (L9).

**Adam Saltsman, the design of Doom Eternal**
- https://blog.adamatomic.com/post/613311014289768448/design-of-doom-eternal
- Source: Adam Saltsman. Licence: author's copyright.
- Fits: jungle gyms (distinct floors) against canyons; pickups that pull players into position.
- For: I2's three floors, the I1 mezzanine, the E3 rim. Roles: level designer (L10).

**Max Pears, "Level design for combat" (2019)**
- https://www.gamedeveloper.com/design/level-design-for-combat
- Source: Game Developer. Licence: publisher's copyright.
- Fits: main doors about 2x side doors; cover at doorways; consistent cover spacing.
- For: door sizes, the I1 airlock cover, E1. Roles: level designer (L11).

**Titanfall 2 action blocks (Christopher Dionne, GDC 2018)**
- https://primagames.com/news/blocking-drunk-titanfall-2s-story-mode-came (session: https://gdcvault.com/play/1025105/)
- Source: Prima Games, on Respawn's talk. Licence: publisher's copyright.
- Fits: "not perfect, but playable" prototypes; Into the Abyss follows one assembly line through a factory.
- For: I2 the production line; the greybox order. Roles: level designer (L12).

**Robert Yang, how to graybox / blockout**
- https://www.blog.radiator.debacle.us/2017/09/how-to-graybox-blockout-3d-video-game.html
- Source: Radiator blog. Licence: not stated.
- Fits: a floor plane, human-scale references, fast blocks, early playtests, annotated sizes.
- For: the shell blockouts for I1-I4 before any art. Roles: level designer (L13).
