from __future__ import annotations

from anki_reminder_bot.entrypoints.common import app_now, build_components


def main() -> None:
    _, repository, anki, _ = build_components()
    config = repository.load_config()
    _, decks = anki.sync_and_get_stats(["*"], app_now(config.timezone))
    save_decks = getattr(repository, "save_decks", None)
    if save_decks is None:
        raise RuntimeError("The configured runtime backend cannot save a deck catalog")
    save_decks(decks)
    print(f"deck_sync_job completed; decks={len(decks)}")


if __name__ == "__main__":
    main()
