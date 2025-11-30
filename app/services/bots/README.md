# Bots Directory

This directory contains all trading bots in an organized structure.

## Structure

Each bot should be in its own subdirectory:

```
bots/
├── bot-usdjpy/
│   ├── main.py
│   ├── config.json
│   ├── requirements.txt
│   └── Dockerfile (optional)
├── bot-eurusd/
│   └── ...
└── ...
```

## Migration from /home/admintrader/tradermain

When copying bots from the old project:

1. Copy the bot directory to `bots/bot-[name]/`
2. Review and update paths in config files
3. Test the bot in isolation
4. Update any systemd services to point to new locations

## Best Practices

- Keep each bot self-contained
- Use relative paths where possible
- Document bot-specific requirements
- Include a README in each bot directory

