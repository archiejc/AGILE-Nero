"""Render a validated drawing-plane path as a standalone SVG."""

from html import escape

from agile_nero.contracts.drawing import Action, Toolpath
from agile_nero.planning.validation import validate_path


def render_svg(path: Toolpath) -> str:
    validation = validate_path(path)
    if not validation.passed:
        raise ValueError("Cannot render invalid path: " + "; ".join(validation.issues))
    width, height = path.config.width_mm, path.config.height_mm
    segments = []
    for previous, point in zip(path.waypoints, path.waypoints[1:]):
        if point.action not in (Action.DRAW, Action.TRAVEL):
            continue
        drawing = point.action == Action.DRAW
        color = "#12618c" if drawing else "#a86532"
        dash = "" if drawing else ' stroke-dasharray="1.5 1"'
        segments.append(
            f'<line x1="{previous.x:g}" y1="{height - previous.y:g}" '
            f'x2="{point.x:g}" y2="{height - point.y:g}" stroke="{color}"{dash}/>'
        )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-2 -2 {width + 4:g} {height + 4:g}" '
        f'width="{width:g}mm" height="{height:g}mm">\n'
        f"<title>{escape(path.task_id)}: offline drawing-plane preview</title>\n"
        "<desc>Blue: drawing; dashed orange: raised travel. "
        "Geometry only; robot simulation and physical execution pending.</desc>\n"
        f'<rect width="{width:g}" height="{height:g}" fill="white" '
        'stroke="#c9c9c9" stroke-width="0.2"/>\n'
        '<g stroke-width="0.45" stroke-linecap="round">\n'
        + "\n".join(segments)
        + "\n</g>\n</svg>\n"
    )
