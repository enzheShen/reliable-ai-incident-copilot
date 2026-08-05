import argparse

from toxiproxy import add_toxic


def main() -> None:
    parser = argparse.ArgumentParser(description="Inject mock-provider response latency")
    parser.add_argument("--milliseconds", type=int, default=15_000)
    parser.add_argument("--jitter", type=int, default=0)
    args = parser.parse_args()
    add_toxic("provider_latency", "latency", {"latency": args.milliseconds, "jitter": args.jitter})
    print(f"injected {args.milliseconds}ms mock-provider latency")


if __name__ == "__main__":
    main()
