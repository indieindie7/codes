"""The Seven: the story data, from the revised episode script.

Each episode has an INTRO, played when the player first gains control on the
episode's first map: the previous episode's tag (radio chatter on the way
out), then the captain's log, then the cold open. MIDS are cues played a set
number of seconds after that.

A line is (speaker, text). Speakers: DALTON AIDA NEBAN ISAAK HAWKINS MEYER.
Special entries: ("BEAT", seconds) = silence, ("STATIC", seconds) = radio static.
"""

EPISODES = [
    dict(ep=1, title="Sanctuary", maps=["M08A1"], intro=[
        ("DALTON", "Marshal's log. Sanctuary went quiet three days ago. Quiet is an answer."),
        ("BEAT", 0.8),
        ("NEBAN", "Landing zone is clear, Marshal. Nothing moves."),
        ("AIDA", "Three hundred people. Nothing moves."),
        ("BEAT", 1.2),
        ("DALTON", "Keep the engines warm."),
    ], mids=[
        # once the first Izarians show up: who they really answer to
        (50, [("AIDA", "Izarians. Skaarj slave troops."),
              ("DALTON", "Then there's a Skaarj holding the leash."),
              ("BEAT", 1.0)]),
    ]),

    dict(ep=2, title="Marsh", maps=["MM_MARSH"], intro=[
        # bridge: the rest of Sanctuary is cut (the original's artifact scenes),
        # so the log tells how it ended
        ("DALTON", "Marshal's log. We found it under the colony. A marine was holding it. He'd held it a long time."),
        ("DALTON", "It looks alien. And old. Older than anything I've seen."),
        ("BEAT", 0.8),
        ("AIDA", "I decrypted a Skaarj intercept. They want that thing, Dalton. Badly."),
        ("DALTON", "Then they'll have to come and get it."),
        ("BEAT", 1.2),
        # Ep 1 tag
        ("HAWKINS", "Marshal Dalton. Hawkins, liaison to Command. Command is grateful."),
        ("HAWKINS", "There are six more. I will send the coordinates. Rest first. Please."),
        ("AIDA", "He said please."),
        ("DALTON", "He did."),
        ("AIDA", "Nobody says please to us."),
        ("BEAT", 1.5),
        # Ep 2 cold open: the crash
        ("NEBAN", "Mayday. Mayday. We are hit. We are going down."),
        ("ISAAK", "She'll hold. She'll hold."),
        ("STATIC", 2.0),
        ("AIDA", "Dalton."),
        ("BEAT", 1.0),
        ("AIDA", "Dalton."),
        ("DALTON", "Here."),
        ("ISAAK", "She held. Mostly. Give me an hour. Keep them off her."),
    ], mids=[
        (75, [("AIDA", "Nobody knew our route. Nobody but Command."), ("BEAT", 2.0)]),
    ]),

    dict(ep=3, title="Hell", maps=["M01A"], intro=[
        # Ep 2 tag
        ("ISAAK", "Engines."),
        ("NEBAN", "Lifting."),
        ("DALTON", "Marshal's log. We fell. We got up. One in the hold. Six to go."),
        ("BEAT", 1.5),
        # Ep 3
        ("DALTON", "Marshal's log. Hell is cold. The Izarians took the second one. Hawkins says Drexler asked for me."),
        ("BEAT", 1.0),
        ("HAWKINS", "Drexler asked about you. He remembers Kalydon, Marshal. He says the Colonel's chair is still empty."),
        ("STATIC", 1.5),
        ("HAWKINS", "Take your time. The Izarians aren't going anywhere."),
        ("AIDA", "He knew about Kalydon."),
        ("DALTON", "Everyone knows about Kalydon."),
        ("AIDA", "Nobody says it that kindly."),
    ], mids=[]),

    dict(ep=4, title="Acheron", maps=["M06_ACHERON"], intro=[
        # Ep 3 tag: the Act I argument
        ("AIDA", "Tell me what the job is."),
        ("DALTON", "Collect. Deliver. Get paid."),
        ("AIDA", "Tell me who pays."),
        ("DALTON", "Command."),
        ("AIDA", "You've never met Command. You've met a voice with no static on it."),
        ("DALTON", "I wore their stripes for twenty years. I know how they talk."),
        ("AIDA", "Then you know they never say please."),
        ("BEAT", 1.5),
        ("DALTON", "Two in the hold. Five to go."),
        ("BEAT", 1.5),
        # Ep 4
        ("DALTON", "Marshal's log. Acheron is alive. The ground breathes. Ne'Ban won't look at it."),
        ("BEAT", 0.8),
        ("NEBAN", "On my world we have a word for places like this. The listening ground."),
        ("AIDA", "What's it listening for?"),
        ("NEBAN", "What you want. Be careful what you want here, Marshal."),
        ("DALTON", "I want the artifact."),
        ("NEBAN", "That is what you say."),
    ], mids=[]),

    dict(ep=5, title="Janus", maps=["M09A"], intro=[
        # Ep 4 tag
        ("AIDA", "I pulled the traffic logs. Every order came down one channel."),
        ("DALTON", "Command's channel."),
        ("AIDA", "Hawkins's channel. There's no one behind it. It's a room with one man in it."),
        ("STATIC", 1.2),
        ("DALTON", "Three in the hold."),
        ("AIDA", "You can't count your way out of this."),
        ("BEAT", 1.5),
        # Ep 5
        ("DALTON", "Marshal's log. A research station. A doctor with two of them, and a lot to say."),
        ("BEAT", 0.8),
        ("HAWKINS", "Doctor Meyer is brilliant, and very tired. Collect the artifacts. Don't trouble her with questions."),
        ("NEBAN", "Why would questions trouble her?"),
        ("HAWKINS", "Everything troubles her. It's why she's brilliant."),
    ], mids=[
        (120, [
            ("MEYER", "Day forty. They are not tools. Not weapons. A key."),
            ("STATIC", 1.0),
            ("MEYER", "Something asleep in the blood of..."),
            ("STATIC", 1.0),
            ("MEYER", "Whoever is collecting them knows. Don't give them all to..."),
            ("STATIC", 0.6),
        ]),
    ]),

    dict(ep=6, title="Na Koja Abad", maps=["M03A1"], intro=[
        # Ep 5 tag: the Act II argument
        ("NEBAN", "Five in the hold. You feel them, Isaak. At night."),
        ("ISAAK", "I feel the reactor. That's what I feel."),
        ("NEBAN", "They are waiting. The thing that sleeps does not dream of us."),
        ("ISAAK", "I don't need to know what they are. I need to know where they go."),
        ("NEBAN", "And if where they go is the end of us?"),
        ("ISAAK", "Then someone above me decided. That's what above means."),
        ("AIDA", "Why don't we just destroy the ones we've already got?"),
        ("BEAT", 2.5),
        # Ep 6
        ("DALTON", "Marshal's log. Six in the hold. Hawkins wants Ne'Ban off my ship. He asked nicely."),
        ("BEAT", 0.8),
        ("HAWKINS", "A small thing, Marshal. Your pilot. Command would feel better with a human at the controls."),
        ("DALTON", "Command can come and fly her."),
        ("HAWKINS", "Of course. Forget I asked. Command is grateful."),
        ("BEAT", 1.0),
        ("NEBAN", "Thank you, Marshal."),
        ("DALTON", "Fly."),
    ], mids=[]),

    dict(ep=7, title="Drakk hive", maps=["M03B1"], intro=[
        # Ep 6 tag: overheard
        ("ISAAK", "Understood. I'll keep an eye on them."),
        ("STATIC", 0.5),
        ("BEAT", 1.5),
        # Ep 7
        ("DALTON", "Marshal's log. The last one. After this, the chair. I keep saying it. It gets quieter every time."),
        ("BEAT", 0.8),
        ("AIDA", "Isaak's been in the hold two days."),
        ("DALTON", "Isaak. Report."),
        ("STATIC", 1.5),
        ("NEBAN", "He is there. He is listening. He does not answer."),
    ], mids=[]),

    dict(ep=8, title="Avalon", maps=["M10_AVALON"], intro=[
        # Ep 7 tag: the Act III argument
        ("HAWKINS", "Seven. Remarkable. Command is grateful."),
        ("HAWKINS", "One formality left. Command likes to be asked. Say you want it back, Marshal. The rank. Just say it."),
        ("BEAT", 3.0),
        ("DALTON", "Bring them to Avalon."),
        ("HAWKINS", "That isn't what I asked."),
        ("DALTON", "It's what you're getting."),
        ("BEAT", 1.0),
        ("HAWKINS", "Avalon, then."),
        ("AIDA", "You could have said it."),
        ("DALTON", "No. I couldn't."),
        ("BEAT", 2.0),
        # Ep 8: Isaak's log, found on the ship, then silence on the radio
        ("ISAAK_LOG", "Engineer's log. She'll hold. I told them she'd hold."),
        ("STATIC", 1.0),
        ("ISAAK_LOG", "She wouldn't give me the artifacts. It was my duty."),
        ("STATIC", 1.0),
        ("ISAAK_LOG", "She'll ho..."),
        ("STATIC", 0.4),
        ("BEAT", 1.5),
        ("DALTON", "Atlantis. Aida. Ne'Ban."),
        ("STATIC", 1.5),
        ("DALTON", "Isaak."),
        ("STATIC", 2.0),
    ], mids=[]),

    dict(ep=9, title="Dorian Gray", maps=["M12"], intro=[
        # Ep 8 tag
        ("BEAT", 1.5),
        ("HAWKINS", "Thank you, Marshal. Truly. Command is grateful."),
        ("BEAT", 2.0),
        # Ep 9
        ("DALTON", "Marshal's log. Seven in the hold. None to go. Nobody left to read this."),
        ("BEAT", 1.0),
        ("HAWKINS", "It's all right, Marshal. You did everything we asked."),
        ("HAWKINS", "Tell me. What did you want? At the start. What did you really want?"),
        ("BEAT", 4.0),
        ("HAWKINS", "Most men know."),
    ], mids=[]),

    dict(ep=10, title="Epilogue", maps=["CS_OUTRO"], intro=[
        ("BEAT", 2.0),
        ("DALTON", "Marshal's log."),
        ("BEAT", 1.5),
        ("DALTON", "Nothing to report."),
    ], mids=[]),
]

# original dialogue to silence (voice and subtitle), by .dlg file under
# <game>\Dialog. The conversations still run, very quickly, so the events they
# fire (objectives, hatches opening) still happen.
MUTE = [
    # Danny Miller, the technician on the security cameras all through Sanctuary
    ("M08A", ["Sanctuary_15G", "Sanctuary_16G", "Sanctuary_16bG", "Sanctuary_17G", "Sanctuary_17bG",
              "Sanctuary_18G", "Sanctuary_19G", "Sanctuary_20G", "Sanctuary_21G", "Sanctuary_22G",
              "Sanctuary_23G", "Sanctuary_24G", "Sanctuary_25G"]),
]

# the Seven cut: after Acheron the story goes straight to Janus
CUT_MISSION_MAPS = ["MM_WATERFRONT", "M06_OBOLUS", "MM_SULFERON_ASSAULT", "MM_SULFERON_DEFEND", "PD_SULFERON"]
