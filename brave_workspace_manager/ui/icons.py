"""Icons drawn in code: the repository does not depend on binary resources."""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPainterPath, QPen, QPixmap

GLYPH_NAMES = (
    "circle",
    "star",
    "heart",
    "bolt",
    "globe",
    "code",
    "briefcase",
    "home",
    "book",
    "gear",
    "leaf",
    "flame",
    "sun",
    "moon",
    "user",
    "folder",
)

ACTION_GLYPHS = ("activate", "minimize", "maximize", "close", "more")


def _polygon(center: QPointF, radius: float, sides: int, rotation: float = 0.0) -> QPainterPath:
    path = QPainterPath()
    for index in range(sides):
        angle = rotation + 2 * math.pi * index / sides
        point = QPointF(
            center.x() + radius * math.cos(angle),
            center.y() + radius * math.sin(angle),
        )
        if index == 0:
            path.moveTo(point)
        else:
            path.lineTo(point)
    path.closeSubpath()
    return path


def draw_glyph(painter: QPainter, name: str, rect: QRectF, color: QColor) -> None:
    """Draws a vector glyph inside rect."""
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(color))
    center = rect.center()
    radius = min(rect.width(), rect.height()) / 2

    if name == "circle":
        painter.drawEllipse(rect)
    elif name == "star":
        path = QPainterPath()
        points = 5
        for index in range(points * 2):
            angle = -math.pi / 2 + math.pi * index / points
            length = radius if index % 2 == 0 else radius * 0.45
            point = QPointF(
                center.x() + length * math.cos(angle), center.y() + length * math.sin(angle)
            )
            path.moveTo(point) if index == 0 else path.lineTo(point)
        path.closeSubpath()
        painter.drawPath(path)
    elif name == "heart":
        path = QPainterPath()
        path.moveTo(center.x(), center.y() + radius * 0.8)
        path.cubicTo(
            center.x() - radius * 1.4,
            center.y() - radius * 0.2,
            center.x() - radius * 0.5,
            center.y() - radius * 1.1,
            center.x(),
            center.y() - radius * 0.35,
        )
        path.cubicTo(
            center.x() + radius * 0.5,
            center.y() - radius * 1.1,
            center.x() + radius * 1.4,
            center.y() - radius * 0.2,
            center.x(),
            center.y() + radius * 0.8,
        )
        painter.drawPath(path)
    elif name == "bolt":
        path = QPainterPath()
        path.moveTo(center.x() + radius * 0.3, center.y() - radius)
        path.lineTo(center.x() - radius * 0.55, center.y() + radius * 0.15)
        path.lineTo(center.x() - radius * 0.05, center.y() + radius * 0.15)
        path.lineTo(center.x() - radius * 0.3, center.y() + radius)
        path.lineTo(center.x() + radius * 0.55, center.y() - radius * 0.2)
        path.lineTo(center.x() + radius * 0.05, center.y() - radius * 0.2)
        path.closeSubpath()
        painter.drawPath(path)
    elif name == "globe":
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(color, max(1.0, radius * 0.18)))
        painter.drawEllipse(rect.adjusted(radius * 0.1, radius * 0.1, -radius * 0.1, -radius * 0.1))
        painter.drawLine(
            QPointF(center.x(), center.y() - radius * 0.9),
            QPointF(center.x(), center.y() + radius * 0.9),
        )
        painter.drawArc(
            rect.adjusted(radius * 0.35, -radius * 0.9, -radius * 0.35, radius * 0.9), 0, 360 * 16
        )
    elif name == "code":
        painter.setBrush(Qt.NoBrush)
        pen = QPen(color, max(1.5, radius * 0.22))
        painter.setPen(pen)
        path = QPainterPath()
        path.moveTo(center.x() - radius * 0.2, center.y() - radius * 0.7)
        path.lineTo(center.x() - radius * 0.75, center.y())
        path.lineTo(center.x() - radius * 0.2, center.y() + radius * 0.7)
        painter.drawPath(path)
        path2 = QPainterPath()
        path2.moveTo(center.x() + radius * 0.2, center.y() - radius * 0.7)
        path2.lineTo(center.x() + radius * 0.75, center.y())
        path2.lineTo(center.x() + radius * 0.2, center.y() + radius * 0.7)
        painter.drawPath(path2)
    elif name == "briefcase":
        painter.drawRoundedRect(
            rect.adjusted(radius * 0.2, radius * 0.05, -radius * 0.2, -radius * 0.25),
            radius * 0.15,
            radius * 0.15,
        )
        painter.drawRoundedRect(
            rect.adjusted(radius * 0.3, -radius * 0.65, -radius * 0.3, -radius * 0.1),
            radius * 0.12,
            radius * 0.12,
        )
    elif name == "home":
        path = QPainterPath()
        path.moveTo(center.x(), center.y() - radius * 0.85)
        path.lineTo(center.x() + radius * 0.95, center.y() + radius * 0.1)
        path.lineTo(center.x() + radius * 0.6, center.y() + radius * 0.1)
        path.lineTo(center.x() + radius * 0.6, center.y() + radius * 0.8)
        path.lineTo(center.x() - radius * 0.6, center.y() + radius * 0.8)
        path.lineTo(center.x() - radius * 0.6, center.y() + radius * 0.1)
        path.lineTo(center.x() - radius * 0.95, center.y() + radius * 0.1)
        path.closeSubpath()
        painter.drawPath(path)
    elif name == "book":
        painter.drawRoundedRect(
            rect.adjusted(radius * 0.3, -radius * 0.75, -radius * 0.3, radius * 0.75),
            radius * 0.12,
            radius * 0.12,
        )
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(color, max(1.0, radius * 0.15)))
        painter.drawLine(
            QPointF(center.x(), center.y() - radius * 0.7),
            QPointF(center.x(), center.y() + radius * 0.7),
        )
    elif name == "gear":
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(color, max(1.5, radius * 0.3)))
        painter.drawEllipse(
            rect.adjusted(radius * 0.35, radius * 0.35, -radius * 0.35, -radius * 0.35)
        )
        painter.setPen(QPen(color, max(1.0, radius * 0.22)))
        for index in range(8):
            angle = math.pi * 2 * index / 8
            start = QPointF(
                center.x() + math.cos(angle) * radius * 0.6,
                center.y() + math.sin(angle) * radius * 0.6,
            )
            end = QPointF(
                center.x() + math.cos(angle) * radius * 0.95,
                center.y() + math.sin(angle) * radius * 0.95,
            )
            painter.drawLine(start, end)
    elif name == "leaf":
        path = QPainterPath()
        path.moveTo(center.x() - radius * 0.8, center.y() + radius * 0.8)
        path.cubicTo(
            center.x() - radius * 0.9,
            center.y() - radius * 0.9,
            center.x() + radius * 0.9,
            center.y() - radius * 0.9,
            center.x() + radius * 0.8,
            center.y() - radius * 0.8,
        )
        path.cubicTo(
            center.x() + radius * 0.7,
            center.y() + radius * 0.7,
            center.x() - radius * 0.7,
            center.y() + radius * 0.7,
            center.x() - radius * 0.8,
            center.y() + radius * 0.8,
        )
        painter.drawPath(path)
    elif name == "flame":
        path = QPainterPath()
        path.moveTo(center.x(), center.y() - radius)
        path.cubicTo(
            center.x() + radius * 0.9,
            center.y() - radius * 0.2,
            center.x() + radius * 0.6,
            center.y() + radius * 0.9,
            center.x(),
            center.y() + radius * 0.9,
        )
        path.cubicTo(
            center.x() - radius * 0.6,
            center.y() + radius * 0.9,
            center.x() - radius * 0.9,
            center.y() - radius * 0.2,
            center.x(),
            center.y() - radius,
        )
        painter.drawPath(path)
    elif name == "sun":
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(color, max(1.0, radius * 0.16)))
        painter.drawEllipse(
            rect.adjusted(radius * 0.35, radius * 0.35, -radius * 0.35, -radius * 0.35)
        )
        for index in range(8):
            angle = math.pi * 2 * index / 8
            painter.drawLine(
                QPointF(
                    center.x() + math.cos(angle) * radius * 0.6,
                    center.y() + math.sin(angle) * radius * 0.6,
                ),
                QPointF(
                    center.x() + math.cos(angle) * radius * 0.95,
                    center.y() + math.sin(angle) * radius * 0.95,
                ),
            )
    elif name == "moon":
        path = QPainterPath()
        path.moveTo(center.x() + radius * 0.7, center.y() - radius * 0.7)
        path.arcTo(
            QRectF(center.x() - radius, center.y() - radius, radius * 2, radius * 2), 60, 240
        )
        path.closeSubpath()
        painter.drawPath(path)
    elif name == "user":
        painter.drawEllipse(
            QRectF(
                center.x() - radius * 0.45, center.y() - radius * 0.85, radius * 0.9, radius * 0.9
            )
        )
        painter.drawPath(
            _polygon(QPointF(center.x(), center.y() + radius * 0.95), radius * 0.85, 3, math.pi / 2)
        )
    else:  # folder
        painter.drawRoundedRect(
            rect.adjusted(radius * 0.15, -radius * 0.55, -radius * 0.15, radius * 0.75),
            radius * 0.15,
            radius * 0.15,
        )
        painter.drawRoundedRect(
            rect.adjusted(-radius * 0.85, -radius * 0.9, radius * 0.2, -radius * 0.3),
            radius * 0.12,
            radius * 0.12,
        )
    painter.restore()


def glyph_pixmap(name: str, color: str, size: int) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    draw_glyph(painter, name, QRectF(0, 0, size, size), QColor(color))
    painter.end()
    return pixmap


def draw_action(painter: QPainter, name: str, rect: QRectF, color: QColor) -> None:
    """Draws the small icons of the window actions of a card."""
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(color))
    center = rect.center()
    unit = min(rect.width(), rect.height())

    if name == "activate":
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(color, max(1.0, unit * 0.14)))
        painter.drawRect(rect.adjusted(unit * 0.18, unit * 0.28, -unit * 0.18, -unit * 0.28))
        painter.drawLine(
            QPointF(center.x() + unit * 0.02, center.y() - unit * 0.44),
            QPointF(center.x() + unit * 0.02, center.y() - unit * 0.12),
        )
        painter.drawLine(
            QPointF(center.x() + unit * 0.02, center.y() - unit * 0.44),
            QPointF(center.x() - unit * 0.16, center.y() - unit * 0.24),
        )
        painter.drawLine(
            QPointF(center.x() + unit * 0.02, center.y() - unit * 0.44),
            QPointF(center.x() + unit * 0.2, center.y() - unit * 0.24),
        )
    elif name == "restore":
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(color, max(1.0, unit * 0.12)))
        back = QRectF(rect.x() + unit * 0.34, rect.y() + unit * 0.16, unit * 0.5, unit * 0.5)
        front = QRectF(rect.x() + unit * 0.16, rect.y() + unit * 0.34, unit * 0.5, unit * 0.5)
        painter.drawLine(back.topLeft(), back.topRight())
        painter.drawLine(back.topRight(), back.bottomRight())
        painter.drawLine(back.topLeft(), QPointF(back.left(), front.top()))
        painter.drawLine(QPointF(front.right(), back.bottom()), back.bottomRight())
        painter.drawRect(front)
    elif name == "minimize":
        painter.drawRect(
            QRectF(center.x() - unit * 0.34, center.y() + unit * 0.22, unit * 0.68, unit * 0.12)
        )
    elif name == "maximize":
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(color, max(1.0, unit * 0.14)))
        painter.drawRect(rect.adjusted(unit * 0.2, unit * 0.2, -unit * 0.2, -unit * 0.2))
    elif name == "close":
        painter.setPen(QPen(color, max(1.2, unit * 0.16)))
        painter.drawLine(
            QPointF(center.x() - unit * 0.26, center.y() - unit * 0.26),
            QPointF(center.x() + unit * 0.26, center.y() + unit * 0.26),
        )
        painter.drawLine(
            QPointF(center.x() + unit * 0.26, center.y() - unit * 0.26),
            QPointF(center.x() - unit * 0.26, center.y() + unit * 0.26),
        )
    else:  # more
        radius = unit * 0.09
        for offset in (-0.22, 0.0, 0.22):
            painter.drawEllipse(
                QRectF(
                    center.x() + unit * offset - radius,
                    center.y() - radius,
                    radius * 2,
                    radius * 2,
                )
            )
    painter.restore()


def action_pixmap(name: str, color: str, size: int) -> QPixmap:
    """Small icon of a window action (activate, minimise, maximise, close)."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    draw_action(painter, name, QRectF(0, 0, size, size), QColor(color))
    painter.end()
    return pixmap


def initials(text: str) -> str:
    cleaned = "".join(character for character in text if character.isalnum() or character in " .")
    parts = [part for part in cleaned.split() if part]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[1][0]).upper()


def avatar_pixmap(profile, size: int = 36) -> QPixmap:
    """Avatar of the profile: the image chosen by the user, Brave's own, or initials."""
    for candidate in (
        getattr(profile, "custom_image", ""),
        getattr(profile, "avatar_path", None),
    ):
        if not candidate:
            continue
        pixmap = QPixmap(candidate)
        if pixmap.isNull():
            continue
        scaled = pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        canvas = QPixmap(size, size)
        canvas.fill(Qt.transparent)
        from PySide6.QtGui import QPainter as _Painter

        painter = _Painter(canvas)
        painter.setRenderHint(_Painter.Antialiasing, True)
        clip = QPainterPath()
        clip.addEllipse(0, 0, size, size)
        painter.setClipPath(clip)
        painter.drawPixmap((size - scaled.width()) // 2, (size - scaled.height()) // 2, scaled)
        painter.end()
        return canvas

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    color = QColor(getattr(profile, "color", "#4f8cff"))
    painter.setBrush(QBrush(color))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(0, 0, size, size)
    font = QFont()
    font.setBold(True)
    font.setPixelSize(int(size * 0.42))
    painter.setFont(font)
    painter.setPen(QPen(QColor("#ffffff")))
    painter.drawText(pixmap.rect(), Qt.AlignCenter, initials(getattr(profile, "label", "?")))
    painter.end()
    return pixmap


def app_pixmap(size: int = 64) -> QPixmap:
    """Application icon: a stack of profiles in Brave colours."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(QColor("#fb542b")))
    painter.drawRoundedRect(2, 2, size - 4, size - 4, size * 0.22, size * 0.22)
    painter.setBrush(QBrush(QColor("#ffffff")))
    radius = size * 0.18
    painter.drawEllipse(int(size * 0.22), int(size * 0.22), int(radius), int(radius))
    painter.setBrush(QBrush(QColor("#ffffff")))
    painter.drawEllipse(int(size * 0.52), int(size * 0.22), int(radius), int(radius))
    painter.setBrush(QBrush(QColor("#ffd43b")))
    painter.drawRoundedRect(
        int(size * 0.2), int(size * 0.55), int(size * 0.6), int(size * 0.1), 4, 4
    )
    painter.setBrush(QBrush(QColor("#ffffff")))
    painter.drawRoundedRect(
        int(size * 0.2), int(size * 0.72), int(size * 0.4), int(size * 0.1), 4, 4
    )
    painter.end()
    return pixmap


def icon_size() -> QSize:
    return QSize(20, 20)
