import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import (
    QPainter,
)
from PyQt6.QtWidgets import (
    QApplication,
    QGraphicsScene,
    QGraphicsView,
    QMainWindow,
)

from graphics import Edge, Node
from tools import MultipleInputDialog


class GraphView(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.setScene(QGraphicsScene(self))
        self.setSceneRect(0, 0, 800, 600)
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.TextAntialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
        )
        # self.automata = Automata()

        self.nodes: dict[str, Node] = {}  # словарь узел-имя
        self.selected_nodes = []  # выделенные узлы для соединения

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return
        scene_pos = self.mapToScene(event.position().toPoint())
        items = self.scene().items(scene_pos)
        node_clicked, edge_clicked = None, None
        for item in items:
            if isinstance(item, Node):
                node_clicked = item
            if isinstance(item, Edge):
                edge_clicked = item

        if node_clicked:
            # Обработка выделения узла
            if node_clicked in self.selected_nodes:
                node_clicked.setSelected(False)
                self.selected_nodes.remove(node_clicked)
            else:
                if len(self.selected_nodes) < 2:
                    node_clicked.setSelected(True)
                    self.selected_nodes.append(node_clicked)
                # Если выбрали два узла - создаём связь
                if len(self.selected_nodes) == 2:
                    self.create_edge(self.selected_nodes[0], self.selected_nodes[1])
                    # Снимаем выделение
                if len(self.selected_nodes) >= 2:
                    for n in self.selected_nodes:
                        n.setSelected(False)
                    self.selected_nodes.clear()

        if edge_clicked:
            # Обработка выделения ребра - пердаем управление обработчику клика ребра
            super().mousePressEvent(event)

        if not edge_clicked and not node_clicked:
            # Клик по пустому месту — добавляем новый узел в место клика
            pos = event.position().toPoint()
            name = f"s{len(self.nodes)}"
            new_node = Node(name, pos.x(), pos.y())
            self.scene().addItem(new_node)
            self.nodes[name] = new_node

    def create_edge(self, node1, node2):
        in_, out_ = self.enter_weight()
        edge = Edge(in_, out_, node1, node2)
        # Добавляем линию на сцену и в списки связных узлов
        node1.edges.append(edge)
        node2.edges.append(edge)
        self.scene().addItem(edge)
        edge.update_path()

    @staticmethod
    def enter_weight():
        input_field = MultipleInputDialog("Вход", "Выход:")
        return input_field.getValues()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Граф с перемещаемыми узлами (PyQt6)")
        self.view = GraphView()
        self.setCentralWidget(self.view)
        # self.resize(800, 600)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
