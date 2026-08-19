#!/usr/bin/env python3
"""Connect to a Blackmagic ATEM switcher and print device information."""

import argparse
import logging
import sys
import time

import PyATEMMax

DEFAULT_IP = "192.168.1.240"
DEFAULT_TIMEOUT = 10.0

logger = logging.getLogger("atem_connect")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Connect to a Blackmagic ATEM switcher and show device info."
    )
    parser.add_argument(
        "--ip",
        default=DEFAULT_IP,
        help=f"IP address of the ATEM device (default: {DEFAULT_IP})",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help=f"Connection timeout in seconds (default: {DEFAULT_TIMEOUT})",
    )
    return parser.parse_args()


def print_device_info(switcher: PyATEMMax.ATEMMax) -> None:
    logger.info("Connected: %s", switcher.connected)
    logger.info("Model: %s", switcher.atemModel)
    logger.info(
        "Protocol version: %d.%d",
        switcher.protocolVersion.major,
        switcher.protocolVersion.minor,
    )
    logger.info("Video mode: %s", switcher.videoMode.format)


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    switcher = PyATEMMax.ATEMMax()
    try:
        logger.info("Connecting to ATEM at %s ...", args.ip)
        switcher.connect(args.ip)
        if not switcher.waitForConnection(infinite=False, timeout=args.timeout):
            logger.error("Failed to connect to %s within %.1fs", args.ip, args.timeout)
            return 1

        logger.info("Connection established with %s", args.ip)
        print_device_info(switcher)

        logger.info("Press Ctrl+C to exit.")
        while switcher.connected:
            time.sleep(1)
        logger.warning("Connection to %s was lost", args.ip)
        return 1
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 0
    finally:
        logger.info("Disconnecting from %s", args.ip)
        switcher.disconnect()


if __name__ == "__main__":
    sys.exit(main())
