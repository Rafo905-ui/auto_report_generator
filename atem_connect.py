#!/usr/bin/env python3
"""Connect to a Blackmagic ATEM switcher and control its inputs."""

import argparse
import logging
import sys
import time

import PyATEMMax

DEFAULT_IP = "192.168.1.240"
DEFAULT_TIMEOUT = 10.0
DEFAULT_ME = 0
ACTION_SETTLE_SECONDS = 0.25
CAMERA_MIN = 1
CAMERA_MAX = 20
IRIS_MIN = 0
IRIS_MAX = 2048
FOCUS_MIN = 0
FOCUS_MAX = 65535
CAMERA_GAIN_VALUES = (512, 1024, 2048, 4096)
WHITE_BALANCE_VALUES = (3200, 4500, 5000, 5600, 6500, 7500)
ZOOM_MIN = 0.0
ZOOM_MAX = 1.0
SHUTTER_VALUES = (
    1 / 50,
    1 / 60,
    1 / 75,
    1 / 90,
    1 / 100,
    1 / 120,
    1 / 150,
    1 / 180,
    1 / 250,
    1 / 360,
    1 / 500,
    1 / 750,
    1 / 1000,
    1 / 1450,
    1 / 2000,
)

logger = logging.getLogger("atem_connect")


def parse_shutter(value: str) -> float:
    try:
        if "/" in value:
            numerator, denominator = value.split("/", 1)
            return float(numerator) / float(denominator)
        return float(value)
    except (ValueError, ZeroDivisionError) as error:
        raise ValueError(f"invalid shutter value: {value}") from error


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
    parser.add_argument(
        "--camera",
        type=int,
        metavar="CAMERA",
        help="Camera number for camera-control actions",
    )
    parser.add_argument(
        "--iris",
        type=int,
        metavar="IRIS",
        help="Set camera iris (0-2048)",
    )
    parser.add_argument(
        "--focus",
        type=int,
        metavar="FOCUS",
        help="Set camera focus (0-65535)",
    )
    parser.add_argument(
        "--auto-focus",
        action="store_true",
        help="Trigger camera auto-focus",
    )
    parser.add_argument(
        "--auto-iris",
        action="store_true",
        help="Trigger camera auto-iris",
    )
    parser.add_argument(
        "--gain",
        type=int,
        metavar="GAIN",
        help="Set camera gain (512, 1024, 2048, or 4096)",
    )
    parser.add_argument(
        "--white-balance",
        type=int,
        metavar="KELVIN",
        help="Set camera white balance (3200, 4500, 5000, 5600, 6500, or 7500)",
    )
    parser.add_argument(
        "--zoom",
        type=float,
        metavar="NORMALIZED",
        help="Set normalized camera zoom (0.0-1.0)",
    )
    parser.add_argument(
        "--shutter",
        type=parse_shutter,
        metavar="SECONDS",
        help="Set camera shutter (for example, 0.016667 for 1/60)",
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


def validate_camera_number(camera: int) -> None:
    if not CAMERA_MIN <= camera <= CAMERA_MAX:
        raise ValueError(
            f"camera must be between {CAMERA_MIN} and {CAMERA_MAX} (got {camera})"
        )


def validate_range(name: str, value: float, minimum: float, maximum: float) -> None:
    if not minimum <= value <= maximum:
        raise ValueError(
            f"{name} must be between {minimum} and {maximum} (got {value})"
        )


def validate_choice(name: str, value: int, choices: tuple[int, ...]) -> None:
    if value not in choices:
        choices_text = ", ".join(str(choice) for choice in choices)
        raise ValueError(f"{name} must be one of {choices_text} (got {value})")


def validate_shutter(shutter: float) -> None:
    if all(abs(shutter - value) > 1e-6 for value in SHUTTER_VALUES):
        values_text = ", ".join(f"1/{round(1 / value)}" for value in SHUTTER_VALUES)
        raise ValueError(
            f"shutter must be one of {values_text} (got {shutter})"
        )


def log_camera_state(switcher: PyATEMMax.ATEMMax, camera: int) -> None:
    camera_state = switcher.cameraControl[camera]
    logger.info(
        "Camera %d state: iris=%d focus=%d gain=%d whiteBalance=%d "
        "shutter=%.6f zoom=%.3f contrast=%s saturation=%s hue=%s sharpening=%d",
        camera,
        camera_state.iris,
        camera_state.focus,
        camera_state.gain.value,
        camera_state.whiteBalance,
        camera_state.shutter,
        camera_state.zoom.normalized,
        camera_state.contrast,
        camera_state.saturation,
        camera_state.hue,
        camera_state.sharpeningLevel,
    )


def settle_after_action() -> None:
    time.sleep(ACTION_SETTLE_SECONDS)


def apply_program_input(
    switcher: PyATEMMax.ATEMMax, me: int, video_source: int
) -> None:
    switcher.setProgramInputVideoSource(me, video_source)
    logger.info("Set M/E %d program input to %d", me, video_source)
    settle_after_action()
    log_input_state(switcher, me)


def apply_preview_input(
    switcher: PyATEMMax.ATEMMax, me: int, video_source: int
) -> None:
    switcher.setPreviewInputVideoSource(me, video_source)
    logger.info("Set M/E %d preview input to %d", me, video_source)
    settle_after_action()
    log_input_state(switcher, me)


def apply_cut(switcher: PyATEMMax.ATEMMax, me: int) -> None:
    switcher.execCutME(me)
    logger.info("Performed cut on M/E %d", me)
    settle_after_action()
    log_input_state(switcher, me)


def apply_auto(switcher: PyATEMMax.ATEMMax, me: int) -> None:
    switcher.execAutoME(me)
    logger.info("Performed auto transition on M/E %d", me)
    settle_after_action()
    log_input_state(switcher, me)


def apply_iris(switcher: PyATEMMax.ATEMMax, camera: int, iris: int) -> None:
    validate_camera_number(camera)
    validate_range("iris", iris, IRIS_MIN, IRIS_MAX)
    switcher.setCameraControlIris(camera, iris)
    logger.info("Set camera %d iris to %d", camera, iris)
    settle_after_action()
    log_camera_state(switcher, camera)


def apply_focus(switcher: PyATEMMax.ATEMMax, camera: int, focus: int) -> None:
    validate_camera_number(camera)
    validate_range("focus", focus, FOCUS_MIN, FOCUS_MAX)
    switcher.setCameraControlFocus(camera, focus)
    logger.info("Set camera %d focus to %d", camera, focus)
    settle_after_action()
    log_camera_state(switcher, camera)


def apply_auto_focus(switcher: PyATEMMax.ATEMMax, camera: int) -> None:
    validate_camera_number(camera)
    switcher.setCameraControlAutoFocus(camera)
    logger.info("Triggered camera %d auto-focus", camera)
    settle_after_action()
    log_camera_state(switcher, camera)


def apply_auto_iris(switcher: PyATEMMax.ATEMMax, camera: int) -> None:
    validate_camera_number(camera)
    switcher.setCameraControlAutoIris(camera)
    logger.info("Triggered camera %d auto-iris", camera)
    settle_after_action()
    log_camera_state(switcher, camera)


def apply_gain(switcher: PyATEMMax.ATEMMax, camera: int, gain: int) -> None:
    validate_camera_number(camera)
    validate_choice("gain", gain, CAMERA_GAIN_VALUES)
    switcher.setCameraControlGain(camera, gain)
    logger.info("Set camera %d gain to %d", camera, gain)
    settle_after_action()
    log_camera_state(switcher, camera)


def apply_white_balance(
    switcher: PyATEMMax.ATEMMax, camera: int, white_balance: int
) -> None:
    validate_camera_number(camera)
    validate_choice("white balance", white_balance, WHITE_BALANCE_VALUES)
    switcher.setCameraControlWhiteBalance(camera, white_balance)
    logger.info("Set camera %d white balance to %dK", camera, white_balance)
    settle_after_action()
    log_camera_state(switcher, camera)


def apply_zoom(switcher: PyATEMMax.ATEMMax, camera: int, zoom: float) -> None:
    validate_camera_number(camera)
    validate_range("zoom", zoom, ZOOM_MIN, ZOOM_MAX)
    switcher.setCameraControlZoomNormalized(camera, zoom)
    logger.info("Set camera %d normalized zoom to %.3f", camera, zoom)
    settle_after_action()
    log_camera_state(switcher, camera)


def apply_shutter(switcher: PyATEMMax.ATEMMax, camera: int, shutter: float) -> None:
    validate_camera_number(camera)
    validate_shutter(shutter)
    switcher.setCameraControlShutter(camera, shutter)
    logger.info("Set camera %d shutter to %.6f", camera, shutter)
    settle_after_action()
    log_camera_state(switcher, camera)


def print_interactive_help() -> None:
    logger.info("Interactive commands:")
    logger.info("  program INPUT  set program input")
    logger.info("  preview INPUT  set preview input")
    logger.info("  cut            perform a cut")
    logger.info("  auto           perform an automatic transition")
    logger.info("  state          show current program/preview inputs")
    logger.info("  camera CAMERA  show compact camera state")
    logger.info("  iris CAMERA VALUE  set iris (0-2048)")
    logger.info("  focus CAMERA VALUE  set focus (0-65535)")
    logger.info("  auto-focus CAMERA  trigger auto-focus")
    logger.info("  auto-iris CAMERA  trigger auto-iris")
    logger.info("  gain CAMERA VALUE  set gain (512, 1024, 2048, or 4096)")
    logger.info(
        "  white-balance CAMERA KELVIN  set white balance "
        "(3200, 4500, 5000, 5600, 6500, or 7500)"
    )
    logger.info("  zoom CAMERA VALUE  set normalized zoom (0.0-1.0)")
    logger.info(
        "  shutter CAMERA VALUE  set shutter "
        "(1/50, 1/60, 1/75, 1/90, 1/100, 1/120, 1/150, 1/180, "
        "1/250, 1/360, 1/500, 1/750, 1/1000, 1/1450, or 1/2000)"
    )
    logger.info("  help           show this help")
    logger.info("  quit           disconnect and exit")


def require_arguments(arguments: list[str], count: int, usage: str) -> None:
    if len(arguments) != count:
        raise ValueError(f"usage: {usage}")


def handle_program_command(
    switcher: PyATEMMax.ATEMMax, me: int, arguments: list[str]
) -> None:
    require_arguments(arguments, 1, "program INPUT")
    apply_program_input(switcher, me, int(arguments[0]))


def handle_preview_command(
    switcher: PyATEMMax.ATEMMax, me: int, arguments: list[str]
) -> None:
    require_arguments(arguments, 1, "preview INPUT")
    apply_preview_input(switcher, me, int(arguments[0]))


def handle_cut_command(
    switcher: PyATEMMax.ATEMMax, me: int, arguments: list[str]
) -> None:
    require_arguments(arguments, 0, "cut")
    apply_cut(switcher, me)


def handle_auto_command(
    switcher: PyATEMMax.ATEMMax, me: int, arguments: list[str]
) -> None:
    require_arguments(arguments, 0, "auto")
    apply_auto(switcher, me)


def handle_state_command(
    switcher: PyATEMMax.ATEMMax, me: int, arguments: list[str]
) -> None:
    require_arguments(arguments, 0, "state")
    log_input_state(switcher, me)


def handle_camera_state_command(
    switcher: PyATEMMax.ATEMMax, me: int, arguments: list[str]
) -> None:
    require_arguments(arguments, 1, "camera CAMERA")
    camera = int(arguments[0])
    validate_camera_number(camera)
    log_camera_state(switcher, camera)


def handle_iris_command(
    switcher: PyATEMMax.ATEMMax, me: int, arguments: list[str]
) -> None:
    require_arguments(arguments, 2, "iris CAMERA VALUE")
    apply_iris(switcher, int(arguments[0]), int(arguments[1]))


def handle_focus_command(
    switcher: PyATEMMax.ATEMMax, me: int, arguments: list[str]
) -> None:
    require_arguments(arguments, 2, "focus CAMERA VALUE")
    apply_focus(switcher, int(arguments[0]), int(arguments[1]))


def handle_auto_focus_command(
    switcher: PyATEMMax.ATEMMax, me: int, arguments: list[str]
) -> None:
    require_arguments(arguments, 1, "auto-focus CAMERA")
    apply_auto_focus(switcher, int(arguments[0]))


def handle_auto_iris_command(
    switcher: PyATEMMax.ATEMMax, me: int, arguments: list[str]
) -> None:
    require_arguments(arguments, 1, "auto-iris CAMERA")
    apply_auto_iris(switcher, int(arguments[0]))


def handle_gain_command(
    switcher: PyATEMMax.ATEMMax, me: int, arguments: list[str]
) -> None:
    require_arguments(arguments, 2, "gain CAMERA VALUE")
    apply_gain(switcher, int(arguments[0]), int(arguments[1]))


def handle_white_balance_command(
    switcher: PyATEMMax.ATEMMax, me: int, arguments: list[str]
) -> None:
    require_arguments(arguments, 2, "white-balance CAMERA KELVIN")
    apply_white_balance(switcher, int(arguments[0]), int(arguments[1]))


def handle_zoom_command(
    switcher: PyATEMMax.ATEMMax, me: int, arguments: list[str]
) -> None:
    require_arguments(arguments, 2, "zoom CAMERA VALUE")
    apply_zoom(switcher, int(arguments[0]), float(arguments[1]))


def handle_shutter_command(
    switcher: PyATEMMax.ATEMMax, me: int, arguments: list[str]
) -> None:
    require_arguments(arguments, 2, "shutter CAMERA VALUE")
    apply_shutter(switcher, int(arguments[0]), parse_shutter(arguments[1]))


def handle_help_command(
    switcher: PyATEMMax.ATEMMax, me: int, arguments: list[str]
) -> None:
    require_arguments(arguments, 0, "help")
    print_interactive_help()


def handle_quit_command(
    switcher: PyATEMMax.ATEMMax, me: int, arguments: list[str]
) -> bool:
    require_arguments(arguments, 0, "quit")
    return True


INTERACTIVE_COMMANDS = {
    "program": handle_program_command,
    "preview": handle_preview_command,
    "cut": handle_cut_command,
    "auto": handle_auto_command,
    "state": handle_state_command,
    "camera": handle_camera_state_command,
    "iris": handle_iris_command,
    "focus": handle_focus_command,
    "auto-focus": handle_auto_focus_command,
    "auto-iris": handle_auto_iris_command,
    "gain": handle_gain_command,
    "white-balance": handle_white_balance_command,
    "zoom": handle_zoom_command,
    "shutter": handle_shutter_command,
    "help": handle_help_command,
    "quit": handle_quit_command,
    "exit": handle_quit_command,
}


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
        command_handler = INTERACTIVE_COMMANDS.get(command)
        if command_handler is None:
            logger.warning("Unknown command: %s (use 'help' for commands)", command)
            continue

        try:
            if command_handler(switcher, me, command_line[1:]):
                return 0
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
        or args.iris is not None
        or args.focus is not None
        or args.auto_focus
        or args.auto_iris
        or args.gain is not None
        or args.white_balance is not None
        or args.zoom is not None
        or args.shutter is not None
    )


def has_camera_action(args: argparse.Namespace) -> bool:
    return (
        args.iris is not None
        or args.focus is not None
        or args.auto_focus
        or args.auto_iris
        or args.gain is not None
        or args.white_balance is not None
        or args.zoom is not None
        or args.shutter is not None
    )


def apply_one_shot_actions(
    switcher: PyATEMMax.ATEMMax, args: argparse.Namespace
) -> bool:
    try:
        if has_camera_action(args):
            if args.camera is None:
                raise ValueError(
                    "Camera control actions require --camera CAMERA"
                )
            validate_camera_number(args.camera)
            if args.iris is not None:
                validate_range("iris", args.iris, IRIS_MIN, IRIS_MAX)
            if args.focus is not None:
                validate_range("focus", args.focus, FOCUS_MIN, FOCUS_MAX)
            if args.gain is not None:
                validate_choice("gain", args.gain, CAMERA_GAIN_VALUES)
            if args.white_balance is not None:
                validate_choice(
                    "white balance", args.white_balance, WHITE_BALANCE_VALUES
                )
            if args.zoom is not None:
                validate_range("zoom", args.zoom, ZOOM_MIN, ZOOM_MAX)
            if args.shutter is not None:
                validate_shutter(args.shutter)

        if args.program_input is not None:
            apply_program_input(switcher, args.me, args.program_input)
        if args.preview_input is not None:
            apply_preview_input(switcher, args.me, args.preview_input)
        if args.cut:
            apply_cut(switcher, args.me)
        if args.auto:
            apply_auto(switcher, args.me)
        if args.iris is not None:
            apply_iris(switcher, args.camera, args.iris)
        if args.focus is not None:
            apply_focus(switcher, args.camera, args.focus)
        if args.auto_focus:
            apply_auto_focus(switcher, args.camera)
        if args.auto_iris:
            apply_auto_iris(switcher, args.camera)
        if args.gain is not None:
            apply_gain(switcher, args.camera, args.gain)
        if args.white_balance is not None:
            apply_white_balance(switcher, args.camera, args.white_balance)
        if args.zoom is not None:
            apply_zoom(switcher, args.camera, args.zoom)
        if args.shutter is not None:
            apply_shutter(switcher, args.camera, args.shutter)
    except ValueError as error:
        logger.warning("%s", error)
        return False

    settle_after_action()
    return True


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
            return 0 if apply_one_shot_actions(switcher, args) else 1
        return interactive_mode(switcher, args.me)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 0
    finally:
        logger.info("Disconnecting from %s", args.ip)
        switcher.disconnect()


if __name__ == "__main__":
    sys.exit(main())
