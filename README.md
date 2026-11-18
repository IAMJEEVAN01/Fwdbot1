# Telegram Forward Bot

Ek channel se doosre channel me messages (video/audio/PDF/text) copy karta hai,
caption me find/replace ke saath.

## Commands
- `/start` - welcome
- `/clone` - range, destination aur find/replace set karke transfer shuru

## Local run (Termux)
```bash
pip install -r requirements.txt
export API_ID=12345 API_HASH=your_hash BOT_TOKEN=your_token
python bot.py
```

## Render deploy
1. Repo GitHub par push karo.
2. Render > New > Web Service > repo select karo.
3. Build: `pip install -r requirements.txt`, Start: `python bot.py`
4. Environment me `API_ID`, `API_HASH`, `BOT_TOKEN` add karo.
5. Free plan par service sleep hoti hai, UptimeRobot se service URL ko har 5 min ping karo.

## Note
- Bot source aur destination me member/admin hona chahiye.
- Secrets kabhi code ya GitHub me mat daalo, sirf environment variables me.
