# Jarvis for Home Assistant

Tells [Jarvis](https://github.com/kucau0901/jarvis-voice-agent) what changes in your house, as it happens.

Jarvis is the brain: it decides what in the house is worth watching (doors, windows, locks, lights, people,
motion, climate, leaks, smoke, the alarm, batteries) and what to do about it. Home Assistant is the backend that
senses and switches. This integration is the link between them. It asks Jarvis which things to watch, listens
to their changes inside Home Assistant, and passes them on. It adds no entities and makes no decisions.

Without it, Jarvis reads the house itself every 15 minutes. With it, a door opening at night reaches Jarvis
within seconds.

## What it sends

- **Urgent changes within a few seconds.** Doors, windows, locks, garage doors and gates, leaks, smoke and gas,
  the alarm, and people coming and going. Jarvis says which things count as urgent.
- **Everything else in one batch every 5 minutes at most.** Lights, motion and temperatures. Each request counts
  towards the token's day in Jarvis (500 by default), so a busy house stays well inside it.
- **Only real changes.** An entity is sent once per batch, from its first state to its latest. A light that
  changed and changed back is not sent at all. Neither is Home Assistant starting up (`unavailable`, `unknown`).
- **Nothing is lost when Jarvis cannot be reached.** A batch that failed is kept and tried again, waiting longer
  each time, up to 15 minutes.

It asks Jarvis for the list again when Jarvis's reply says the list changed, and every 6 hours. The list changes
when you tell Jarvis "don't watch the garden lights" or "also watch the freezer temperature".

## Install

1. In HACS, open **Custom repositories**, add this repository's address, and choose the type **Integration**.
   Then install **Jarvis** and restart Home Assistant.
2. In Jarvis, open **Devices** while signed in as the first person (the one who set Jarvis up): only their
   devices may tell Jarvis about the house, or anyone's could make it up. Make a device token with the
   scope **the house and cameras** (`home`). Jarvis shows it once.
3. In Home Assistant, go to **Settings → Devices & services → Add integration → Jarvis**. Enter Jarvis's address
   (for example `https://jarvis.example.com`) and the token. The token is tried before it is saved.

Then, in Jarvis's **Settings → Home Assistant → Watch the house**, choose **unusual** or **every** to have Jarvis
act on what it hears. With **off**, Jarvis still keeps track of the house for its looks around, but judges
nothing.

## Manual install

Copy `custom_components/jarvis` into your Home Assistant `config/custom_components/` folder, restart, and carry
on from step 2.

## Development

The timing (what is sent when) lives in `custom_components/jarvis/batch.py`, apart from Home Assistant, and is
tested on its own:

```bash
python3 -m unittest discover tests
```

## Licence

MIT
