import math

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import (
    QBrush,
    QFont,
    QPainterPath,
    QPainterPathStroker,
    QPen,
    QPolygonF,
)
from PyQt6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsPathItem,
    QGraphicsPolygonItem,
)

from tools import EditableTextItem


class Node(QGraphicsEllipseItem):
    def __init__(self, name, x, y, radius=20):
        super().__init__(-radius, -radius, 2 * radius, 2 * radius)
        self.name = name
        self.edges: list[Edge] = []  # ребра, исходящие из узла

        self.setBrush(QBrush(Qt.GlobalColor.cyan))
        self.setPen(QPen(Qt.GlobalColor.black))
        self.setFlag(QGraphicsEllipseItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsEllipseItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(
            QGraphicsEllipseItem.GraphicsItemFlag.ItemSendsScenePositionChanges
        )
        self.setPos(x, y)

        self.name_text_item = EditableTextItem(self.name, self)
        text_rect = self.name_text_item.boundingRect()
        center = self.rect().center()

        self.name_text_item.setPos(
            center.x() - text_rect.width() / 2,
            center.y() - text_rect.height() / 2
        )

    def itemChange(self, change, value):
        if change == self.GraphicsItemChange.ItemPositionHasChanged:
            for edge in self.edges:
                edge.update_path()
        return super().itemChange(change, value)


class Edge(QGraphicsPathItem):
    def __init__(
        self, input_value: str, output_value: str, source: Node, destination: Node
    ):
        super().__init__()
        self.input_value = input_value
        self.output_value = output_value

        self.source = source
        self.destination = destination
        self.setPen(QPen(Qt.GlobalColor.black, 2))

        self.arrow_size = 10
        self.arrow_head = None
        self.input_text_item = None
        self.output_text_item = None
        self.separator_text_item = None

        self.create_click_area(30)

    def get_text(self):
        return f"{self.input_value} | {self.output_value}"

    def create_click_area(self, width):
        # Создаем новую область с шириной 'width' вокруг исходного пути
        stroker = QPainterPathStroker()
        stroker.setWidth(width)
        self.click_area = stroker.createStroke(self.path())

    def update_path(self):
        # Получаем позиции узлов
        source_point = self.get_boundary_point(self.source, self.destination)
        dest_point = self.get_boundary_point(self.destination, self.source)

        path = QPainterPath()
        path.moveTo(source_point)

        # Создаем кривую с помощью quadTo (квадратичная кривая)
        # Можно выбрать контрольную точку для изгиба
        control_point = (source_point + dest_point) / 2
        control_point.setY(control_point.y() - 80)  # смещение вверх для изгиба

        path.quadTo(control_point, dest_point)
        self.setPath(path)
        self.draw_arrowhead()
        self.create_weight_text()

    @staticmethod
    def get_boundary_point(source: Node, destination: Node):
        # Центры узлов
        source_center = source.scenePos() + source.rect().center()
        dest_center = destination.scenePos() + destination.rect().center()

        # Вектор направления
        line_vec = dest_center - source_center
        angle = math.atan2(line_vec.y(), line_vec.x())

        # Размеры узлов
        rect = source.rect()
        width = rect.width() / 2
        height = rect.height() / 2

        # Для эллипса: найти точку на границе по углу
        # Формула для эллипса:
        # x = width * cos(t), y = height * sin(t)
        # где t - угол
        t = angle
        boundary_x = width * math.cos(t)
        boundary_y = height * math.sin(t)

        boundary_point_local = QPointF(boundary_x, boundary_y)
        boundary_point_scene = source_center + boundary_point_local

        return boundary_point_scene

    def create_weight_text(self):
        mid_point = self.path().pointAtPercent(0.5)
        input_offset, offset = QPointF(0, -15), QPointF(15, 0)

        if self.input_text_item and self.output_text_item and self.separator_text_item:
            self.input_text_item.setPos(mid_point + input_offset)
            self.separator_text_item.setPos(self.input_text_item.pos() + offset)
            self.output_text_item.setPos(self.separator_text_item.pos() + offset)
            return

        # Находим середину линии для отображения веса
        font = QFont("Arial", 14)

        # Текстовый элемент для входа
        input_text_item = EditableTextItem(self.input_value, self)
        input_text_item.setBrush(Qt.GlobalColor.red)
        input_text_item.setFont(font)
        input_text_item.setPos(mid_point + input_offset)

        # Текстовый элемент для разделителя
        separator_text_item = EditableTextItem("|", self)
        separator_text_item.setBrush(Qt.GlobalColor.red)
        separator_text_item.setPos(input_text_item.pos() + offset)
        separator_text_item.setFont(font)

        # Текстовый элемент для выхода
        output_text_item = EditableTextItem(self.output_value, self)
        output_text_item.setBrush(Qt.GlobalColor.red)
        output_text_item.setPos(separator_text_item.pos() + offset)
        output_text_item.setFont(font)

        scene = self.scene()
        if scene:
            scene.addItem(input_text_item)
            scene.addItem(output_text_item)
            scene.addItem(separator_text_item)
            self.input_text_item = input_text_item
            self.output_text_item = output_text_item
            self.separator_text_item = separator_text_item

    def draw_arrowhead(self):
        # Удаляем старый стрелочный элемент, если есть
        if self.arrow_head:
            scene = self.scene()
            if scene:
                scene.removeItem(self.arrow_head)

        path_length = self.path().length()

        if path_length == 0:
            return

        # Получаем точку на конце кривой (конец линии)
        end_point = self.path().pointAtPercent(1.0)

        # Получаем точку чуть перед конца для определения направления стрелки
        # Можно взять чуть назад по линии для определения направления стрелки
        tail_percent = max(0.0, 1.0 - self.arrow_size / path_length)
        start_arrow_point = self.path().pointAtPercent(tail_percent)

        # Вектор направления стрелки (от start к end)
        direction_vector = end_point - start_arrow_point

        # Нормализуем вектор и масштабируем до размера стрелки
        length = math.hypot(direction_vector.x(), direction_vector.y())
        if length == 0:
            return

        unit_vector = QPointF(
            direction_vector.x() / length,
            direction_vector.y() / length,
        )

        # Перпендикуляр к вектору для создания треугольника стрелки
        perp_vector = QPointF(-unit_vector.y(), unit_vector.x())

        # Точки треугольника стрелки относительно конца линии
        point1 = end_point
        point2 = (
            end_point
            - unit_vector * self.arrow_size
            + perp_vector * (self.arrow_size / 2)
        )
        point3 = (
            end_point
            - unit_vector * self.arrow_size
            - perp_vector * (self.arrow_size / 2)
        )

        arrow_polygon = QPolygonF([point1, point2, point3])

        arrow_item = QGraphicsPolygonItem(arrow_polygon)
        arrow_item.setBrush(Qt.GlobalColor.black)
        arrow_item.setPen(QPen(Qt.GlobalColor.black))

        scene = self.scene()
        if scene:
            scene.addItem(arrow_item)

        # Save reference to remove later if needed
        self.arrow_head = arrow_item

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            pass
