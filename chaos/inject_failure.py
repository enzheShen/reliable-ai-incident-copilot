from toxiproxy import add_toxic


def main() -> None:
    add_toxic("provider_reset", "reset_peer", {"timeout": 0})
    print("injected mock-provider connection resets")


if __name__ == "__main__":
    main()
