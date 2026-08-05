from chaos.toxiproxy import remove_toxic


def reset() -> None:
    for name in ("provider_latency", "provider_reset"):
        remove_toxic(name)


if __name__ == "__main__":
    reset()
    print("removed mock-provider toxics")
