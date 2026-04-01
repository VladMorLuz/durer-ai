from krita import Krita
from PyQt5.QtGui import QPainter, QColor, QPen
from PyQt5.QtCore import QPoint

app = Krita.instance()
doc = app.activeDocument()
node = doc.activeNode()

# Pega os pixels do layer como QImage
img = node.thumbnail(doc.width(), doc.height())

# Cria um QPainter sobre essa imagem
painter = QPainter(img)
pen = QPen(QColor(0, 0, 0))   # Preto
pen.setWidth(8)
painter.setPen(pen)

# Desenha uma linha diagonal simples
painter.drawLine(QPoint(100, 100), QPoint(400, 400))
painter.end()

# Devolve os pixels pro layer
node.setPixelData(
    img.bits().asstring(img.byteCount()),
    0, 0, doc.width(), doc.height()
)
doc.refreshProjection()