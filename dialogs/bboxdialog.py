from qgis.PyQt.QtWidgets import QDialog, QLabel, QComboBox, QPushButton, QAction, QMessageBox, QCompleter, \
    QPlainTextEdit, QLineEdit
from qgis.PyQt.QtCore import QUrl
from qgis.PyQt import QtCore
from qgis.PyQt.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from qgis.core import QgsVectorLayer, QgsRasterLayer, QgsProject, QgsGeometry, QgsFeature, QgsCoordinateReferenceSystem, \
    QgsCoordinateTransform, QgsWkbTypes, QgsMapLayer, QgsPointXY
from qgis.gui import QgsMapCanvas, QgsMapToolPan, QgsProjectionSelectionWidget
from qgis.PyQt import uic
from ..util.mappingtools import RectangleMapTool
from ..util.mappingtools import CircleMapTool
from ..util.mappingtools import PolygonMapTool
import os.path
import json

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui/bboxdialog.ui'))


class SPARQLCompleter(QCompleter):
    insertText = QtCore.pyqtSignal(str)

    def __init__(self, autocomplete, parent=None):
        QCompleter.__init__(self, autocomplete, parent)
        self.setCompletionMode(QCompleter.PopupCompletion)
        # self.setFilterMode(Qt.MatchContains)
        # self.highlighted.connect(self.setHighlighted)

    def setHighlighted(self, text):
        self.lastSelected = text

    def getSelected(self):
        return self.lastSelected


class NominatimText(QLineEdit):

    def __init__(self, parent, nominatimmap, map_canvas):
        super(self.__class__, self).__init__(parent)
        self.nominatimmap = nominatimmap
        self.map_canvas = map_canvas

    def insertCompletion(self, completion):
        self.map_canvas.zoomWithCenter(self.nominatimmap[completion][0], self.nominatimmap[completion][1], True)

    def setMap(self, nominatimmap):
        self.nominatimmap = nominatimmap


class BBOXDialog(QDialog, FORM_CLASS):

    def __init__(self, inp_sparql, triplestoreconf, endpointIndex):
        super(QDialog, self).__init__()
        self.setupUi(self)
        self.inp_sparql = inp_sparql


        self.triplestoreconf = triplestoreconf
        self.endpointIndex = endpointIndex
        self.vl = QgsVectorLayer("Point", "temporary_points", "memory")
        self.map_canvas = QgsMapCanvas(self)
        self.layerExtentOrBBOX = False
        self.map_canvas.setMinimumSize(500, 475)
        self.map_canvas.move(0, 30)
        self.nominatimmap = {}
        actionPan = QAction("Pan", self)
        actionPan.setCheckable(True)
        actionPan.triggered.connect(self.pan)
        self.toolPan = QgsMapToolPan(self.map_canvas)
        self.toolPan.setAction(actionPan)
        uri = "url=http://a.tile.openstreetmap.org/{z}/{x}/{y}.png&zmin=0&type=xyz"
        self.mts_layer = QgsRasterLayer(uri, 'OSM', 'wms')
        if not self.mts_layer.isValid():
            print("Layer failed to load!")
        self.rect_tool = RectangleMapTool(self.map_canvas)
        self.circ_tool = CircleMapTool(self.map_canvas, 1)
        self.poly_tool = PolygonMapTool(self.map_canvas)
        self.map_canvas.setMapTool(self.rect_tool)
        self.map_canvas.setExtent(self.mts_layer.extent())
        self.map_canvas.setLayers([self.vl, self.mts_layer])
        self.map_canvas.setCurrentLayer(self.mts_layer)
        self.pan()
        self.selectCircle.hide()
        # @Antoine
        self.selectPolygon.hide()
        ###########
        self.geocodeSearch = NominatimText(self, self.nominatimmap, self.map_canvas)
        self.move(120, 0)
        self.crsdialog = QgsProjectionSelectionWidget(self)
        self.crsdialog.move(160, 540)
        self.crsdialog.resize(331, 30)
        self.crsdialog.setCrs(QgsCoordinateReferenceSystem('EPSG:4326'))
        self.crsdialog.show()
        self.nominatimurl = 'https://nominatim.openstreetmap.org/search?format=json&q={address}'
        self.panButton.clicked.connect(self.pan)
        self.selectCircle.clicked.connect(self.selectcircle)
        self.selectPolygon.clicked.connect(self.selectpolygon)
        self.selectButton.clicked.connect(self.selectarea)
        self.zoomIn.clicked.connect(self.map_canvas.zoomIn)
        self.zoomOut.clicked.connect(self.map_canvas.zoomOut)
        self.b2.clicked.connect(self.setBBOXExtentQuery)
        self.searchButton.hide()
        self.searchPlace.hide()
        self.geocodeSearch.hide()
        layers = QgsProject.instance().layerTreeRoot().children()
        for layer in layers:
            self.chooseBBOXLayer.addItem(layer.name())
        self.searchButton.clicked.connect(self.geocode)
        self.b1.clicked.connect(self.setBBOXInQuery)

    def geocode(self):
        try:
            nominatimurl = self.nominatimurl.format(**{'address': self.geocodeSearch.text()})
            self.networkrequest(nominatimurl)
        except Exception as e:
            msgBox = QMessageBox()
            msgBox.setWindowTitle("Mandatory variables missing!")
            msgBox.setText(str(e))
            msgBox.exec()

    def networkrequest(self, nurl):
        global reply
        self.manager = QNetworkAccessManager()
        url = QUrl(nurl)
        request = QNetworkRequest(url)
        self.manager.finished.connect(self.handleResponse)
        self.manager.get(request)

    def handleResponse(self, reply):
        er = reply.error()
        if er == QNetworkReply.NoError:
            bytes_string = reply.readAll()
            print(str(bytes_string, 'utf-8'))
            results = json.loads(str(bytes_string, 'utf-8'))
            self.nominatimmap = {}
            chooselist = []
            for rec in results:
                chooselist.append(rec['display_name'])
                self.nominatimmap[rec['display_name']] = [rec['lon'], rec['lat']]
            completer = SPARQLCompleter(chooselist)
            self.geocodeSearch.setMap(self.nominatimmap)
            self.geocodeSearch.setCompleter(completer)
            # self.geocodeSearch.insertCompletion.connect(self.zoomToCoordinates)
            completer.popup().show()
        else:
            print("Error occured: ", er)

    def zoomToCoordinates(self, completion):
        msgBox = QMessageBox()
        msgBox.setText(completion)
        msgBox.exec()
        self.map_canvas.zoomWithCenter(self.nominatimmap[completion][0], self.nominatimmap[completion][1], True)

    def pan(self):
        self.map_canvas.setMapTool(self.toolPan)

    def selectarea(self):
        self.rectangle = True
        self.circle = False
        self.polygon = False
        self.map_canvas.setMapTool(self.rect_tool)

    def selectcircle(self):
        self.rectangle = False
        self.circle = True
        self.polygon = False
        self.map_canvas.setMapTool(self.circ_tool)

    def selectpolygon(self):
        self.rectangle = False
        self.circle = False
        self.polygon = True
        self.map_canvas.setMapTool(self.poly_tool)

    def setBBOXExtentQuery(self):
        if len(QgsProject.instance().layerTreeRoot().children()) > 0:
            self.mts_layer = QgsProject.instance().layerTreeRoot().children()[
                self.chooseBBOXLayer.currentIndex()].layer()
            self.layerExtentOrBBOX = True
            self.setBBOXInQuery()
            self.close()
        else:
            msgBox = QMessageBox()
            msgBox.setWindowTitle("No layer loaded in QGIS!")
            msgBox.setText("No layer has been loaded in QGIS to get an extent from!")
            msgBox.exec()

    def setBBOXInQuery(self):
        #@Antoine
        global polygon
        #
        #
        sourceCrs = None
        if self.layerExtentOrBBOX:
            xMax = self.mts_layer.extent().xMaximum()
            xMin = self.mts_layer.extent().xMinimum()
            yMin = self.mts_layer.extent().yMinimum()
            yMax = self.mts_layer.extent().yMaximum()
            pointt1 = QgsGeometry.fromPointXY(QgsPointXY(xMax, yMin))
            pointt2 = QgsGeometry.fromPointXY(QgsPointXY(xMin, yMin))
            pointt3 = QgsGeometry.fromPointXY(QgsPointXY(xMin, yMax))
            pointt4 = QgsGeometry.fromPointXY(QgsPointXY(xMax, yMax))
            sourceCrs = QgsCoordinateReferenceSystem(self.mts_layer.crs())
        else:
            sourceCrs = QgsCoordinateReferenceSystem(self.mts_layer.crs())
            destCrs = self.crsdialog.crs()
            if self.polygon:
                polygon = self.poly_tool.rb.asGeometry()
                tr = QgsCoordinateTransform(sourceCrs, destCrs, QgsProject.instance())
                polygon.transform(tr)
            elif self.circle:
                pointt1 = QgsGeometry.fromWkt(self.circ_tool.point1.asWkt())
                pointt2 = QgsGeometry.fromWkt(self.circ_tool.point2.asWkt())
                pointt3 = QgsGeometry.fromWkt(self.circ_tool.point3.asWkt())
                pointt4 = QgsGeometry.fromWkt(self.circ_tool.point4.asWkt())
            else:
                pointt1 = QgsGeometry.fromWkt(self.rect_tool.point1.asWkt())
                pointt2 = QgsGeometry.fromWkt(self.rect_tool.point2.asWkt())
                pointt3 = QgsGeometry.fromWkt(self.rect_tool.point3.asWkt())
                pointt4 = QgsGeometry.fromWkt(self.rect_tool.point4.asWkt())
                print("coucou")
                if sourceCrs != None:
                    print(sourceCrs)
                    tr = QgsCoordinateTransform(sourceCrs, destCrs, QgsProject.instance())
                    pointt1.transform(tr)
                    pointt2.transform(tr)
                    pointt3.transform(tr)
                    pointt4.transform(tr)
                print("coucou3")
                polygon = QgsGeometry.fromPolylineXY(
                    [pointt1.asPoint(), pointt2.asPoint(), pointt3.asPoint(), pointt4.asPoint()])
        center = polygon.centroid()
        # distance = QgsDistanceArea()
        # distance.setSourceCrs(destCrs)
        # distance.setEllipsoidalMode(True)
        # distance.setEllipsoid('WGS84')
        curquery = self.inp_sparql.toPlainText()
        if self.rectangle or self.circle:
            widthm = 100  # distance.measureLine(pointt1, pointt2)
            self.curbbox = []
            self.curbbox.append(pointt1)
            self.curbbox.append(pointt2)
            self.curbbox.append(pointt3)
            self.curbbox.append(pointt4)
            self.close()
            if "bboxquery" in self.triplestoreconf[self.endpointIndex] and \
                    self.triplestoreconf[self.endpointIndex]["bboxquery"]["type"] == "geosparql":
                curquery = curquery[0:curquery.rfind('}')] + self.triplestoreconf[self.endpointIndex]["bboxquery"][
                    "query"].replace("%%x1%%", str(pointt1.asPoint().x())).replace("%%x2%%",
                                                                                    str(pointt3.asPoint().x())).replace(
                    "%%y1%%", str(pointt1.asPoint().y())).replace("%%y2%%",
                                                                    str(pointt3.asPoint().y())) + "}\n" + curquery[
                                                                                                        curquery.rfind(
                                                                                                            '}') + 1:]
            elif "bboxquery" in self.triplestoreconf[self.endpointIndex] and \
                    self.triplestoreconf[self.endpointIndex]["bboxquery"]["type"] == "minmax":
                #Removes useless space inside the point syntaxe
                p2= pointt2.asWkt().replace(" (", "(")
                p4= pointt4.asWkt().replace(" (", "(")
                #Inverse latitude and longitude coordinates for point 2
                # c=pointt2.asWkt().split('(')
                # print(c)
                # c=c[1].split(')')
                # print(c)
                # c=c[0].split(' ')
                # print(c)
                # p2= "Point(" + c[1] + " " + c[0] + ")"
                #Inverse latitude and longitude coordinates for point 4
                #c=pointt4.asWkt().split('(')
                #print(c)
                #c=c[1].split(')')
                # print(c)
                # c=c[0].split(' ')
                # print(c)
                # p4= "Point(" + c[1] + " " + c[0] + ")"

                curquery = curquery[0:curquery.rfind('}')] + self.triplestoreconf[self.endpointIndex]["bboxquery"][
                    "query"].replace("%%minPoint%%", p2).replace("%%maxPoint%%",p4) + curquery[curquery.rfind('}') + 1:]
                curquery=curquery.replace("/geosparql","/ont/geosparql")
            elif "bboxquery" in self.triplestoreconf[self.endpointIndex] and \
                    self.triplestoreconf[self.endpointIndex]["bboxquery"]["type"] == "pointdistance":
                curquery = curquery[0:curquery.rfind('}')] + self.triplestoreconf[self.endpointIndex]["bboxquery"][
                    "query"].replace("%%lat%%", str(center.asPoint().y())).replace("%%lon%%",
                                                                                     str(center.asPoint().x())).replace(
                    "%%distance%%", str(widthm / 1000)) + curquery[curquery.rfind('}') + 1:]
            ##
            # @Antoine modified indentation because it was wrong
        elif polygon:
            widthm = 100
            #
            #
            if "bboxquery" in self.triplestoreconf[self.endpointIndex] and \
                    self.triplestoreconf[self.endpointIndex]["bboxquery"]["type"] == "geosparql":
                curquery = curquery[0:curquery.rfind(
                    '}')] + "FILTER(geof:sfIntersects(?geo,\"" + polygon.asWkt() + "\"^^geo:wktLiteral))"
            elif "bboxquery" in self.triplestoreconf[self.endpointIndex] and \
                    self.triplestoreconf[self.endpointIndex]["bboxquery"]["type"] == "minmax":
                curquery = curquery[0:curquery.rfind('}')] + self.triplestoreconf[self.endpointIndex]["bboxquery"][
                    "query"].replace("%%minPoint%%", "POINT(" + str(polygon.boundingBox().yMinimum()) + " " + str(
                    polygon.boundingBox().xMinimum()) + ")").replace("%%maxPoint%%", "POINT(" + str(
                    polygon.boundingBox().yMaximum()) + " " + str(polygon.boundingBox().xMaximum()) + ")") + curquery[
                                                                                                            curquery.rfind(
                                                                                                                '}') + 1:]
            elif "bboxquery" in self.triplestoreconf[self.endpointIndex] and \
                    self.triplestoreconf[self.endpointIndex]["bboxquery"]["type"] == "pointdistance":
                curquery = curquery[0:curquery.rfind('}')] + self.triplestoreconf[self.endpointIndex]["bboxquery"][
                    "query"].replace("%%lat%%", str(polygon.boundingBox().center().asPoint().y())).replace("%%lon%%",
                                                                                                            str(polygon.boundingBox().center().asPoint().x())).replace(
                                                                                                            "%%distance%%", str(widthm / 1000)) + curquery[curquery.rfind('}') + 1:]

        self.inp_sparql.setPlainText(curquery)
        self.close()
