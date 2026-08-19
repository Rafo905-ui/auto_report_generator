#!/usr/bin/env python3
"""Connect to a Blackmagic ATEM switcher and control its inputs."""

import argparse
import logging
import sys

import PyATEMMax

DEFAULT_IP = "192.168.1.240"
DEFAULT_TIMEOUT = 10.0
DEFAULT_ME = 0

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
    parser.add_argument(
        "--program-input",
        "--program",
        dest="program_input",
        type=int,
        metavar="INPUT",
        help="Set the program input (one-shot action)",
    )
    parser.add_argument(
        "--preview-input",
        "--preview",
        dest="preview_input",
        type=int,
        metavar="INPUT",
        help="Set the preview input (one-shot action)",
    )
    parser.add_argument(
        "--cut",
        action="store_true",
        help="Perform a cut on the selected mix effect (one-shot action)",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Perform an automatic transition on the selected mix effect (one-shot action)",
    )
    parser.add_argument(
        "--me",
        "--mix-effect",
        dest="me",
        type=int,
        default=DEFAULT_ME,
        metavar="ME",
        help=f"Mix effect block for actions (default: {DEFAULT_ME})",
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


def log_input_state(switcher: PyATEMMax.ATEMMax, me: int) -> None:
    logger.info(
        "M/E %d state: program=%s, preview=%s",
        me,
        switcher.programInput[me].videoSource,
        switcher.previewInput[me].videoSource,
    )


def apply_program_input(
    switcher: PyATEMMax.ATEMMax, me: int, video_source: int
) -> None:
    switcher.setProgramInputVideoSource(me, video_source)
    logger.info("Set M/E %d program input to %d", me, video_source)
    log_input_state(switcher, me)


def apply_preview_input(
    switcher: PyATEMMax.ATEMMax, me: int, video_source: int
) -> None:
    switcher.setPreviewInputVideoSource(me, video_source)
    logger.info("Set M/E %d preview input to %d", me, video_source)
    log_input_state(switcher, me)


def apply_cut(switcher: PyATEMMax.ATEMMax, me: int) -> None:
    switcher.execCutME(me)
    logger.info("Performed cut on M/E %d", me)
    log_input_state(switcher, me)


def apply_auto(switcher: PyATEMMax.ATEMMax, me: int) -> None:
    switcher.execAutoME(me)
    logger.info("Performed auto transition on M/E %d", me)
    log_input_state(switcher, me)


def print_interactive_help() -> None:
    logger.info("Interactive commands:")
    logger.info("  program INPUT  set program input")
    logger.info("  preview INPUT  set preview input")
    logger.info("  cut            perform a cut")
    logger.info("  auto           perform an automatic transition")
    logger.info("  state          show current program/preview inputs")
    logger.info("  help           show this help")
    logger.info("  quit           disconnect and exit")


def interactive_mode(switcher: PyATEMMax.ATEMMax, me: int) -> int:
    print_interactive_help()
    while switcher.connected:
        try:
            command_line = input("> ").strip().split()
        except EOFError:
            logger.info("End of input")
            return 0
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
            return 0

        if not command_line:
            continue

        command = command_line[0].lower()
        try:
            if command in {"program", "preview"}:
                if len(command_line) != 2:
                    raise ValueError(f"usage: {command} INPUT")
                video_source = int(command_line[1])
                if command == "program":
                    apply_program_input(switcher, me, video_source)
                else:
                    apply_preview_input(switcher, me, video_source)
            elif command == "cut":
                if len(command_line) != 1:
                    raise ValueError("usage: cut")
                apply_cut(switcher, me)
            elif command == "auto":
                if len(command_line) != 1:
                    raise ValueError("usage: auto")
                apply_auto(switcher, me)
            elif command == "state":
                if len(command_line) != 1:
                    raise ValueError("usage: state")
                log_input_state(switcher, me)
            elif command == "help":
                if len(command_line) != 1:
                    raise ValueError("usage: help")
                print_interactive_help()
            elif command in {"quit", "exit"}:
                if len(command_line) != 1:
                    raise ValueError("usage: quit")
                return 0
            else:
                logger.warning("Unknown command: %s (use 'help' for commands)", command)
        except ValueError as error:
            logger.warning("%s", error)

    logger.warning("Connection to switcher was lost")
    return 1


def has_one_shot_action(args: argparse.Namespace) -> bool:
    return (
        args.program_input is not None
        or args.preview_input is not None
        or args.cut
        or args.auto
    )


def apply_one_shot_actions(
    switcher: PyATEMMax.ATEMMax, args: argparse.Namespace
) -> None:
    if args.program_input is not None:
        apply_program_input(switcher, args.me, args.program_input)
    if args.preview_input is not None:
        apply_preview_input(switcher, args.me, args.preview_input)
    if args.cut:
        apply_cut(switcher, args.me)
    if args.auto:
        apply_auto(switcher, args.me)


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

        if has_one_shot_action(args):
            apply_one_shot_actions(switcher, args)
            return 0
        return interactive_mode(switcher, args.me)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 0
    finally:
        logger.info("Disconnecting from %s", args.ip)
        switcher.disconnect()


if __name__ == "__main__":
    sys.exit(main())
