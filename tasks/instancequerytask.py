from ..util.sparqlutils import SPARQLUtils
from ..util.layerutils import LayerUtils
from qgis.core import Qgis, QgsFeature, QgsVectorLayer, QgsCoordinateReferenceSystem
from qgis.PyQt.QtCore import Qt, QSize
from qgis.core import QgsProject
from qgis.core import (
    QgsTask, QgsMessageLog
)
from qgis.PyQt.QtWidgets import QTableWidgetItem
import json

MESSAGE_CATEGORY = 'InstanceQueryTask'

class InstanceQueryTask(QgsTask):

    def __init__(self, description, triplestoreurl, searchTerm, triplestoreconf, searchResult,mymap=None,features=None,parentwindow=None):
        super().__init__(description, QgsTask.CanCancel)
        self.exception = None
        self.triplestoreurl = triplestoreurl
        self.searchTerm=searchTerm
        self.features=features
        self.mymap=mymap
        self.searchResult = searchResult
        self.prefixes= SPARQLUtils.invertPrefixes(triplestoreconf["prefixes"])
        self.triplestoreconf=triplestoreconf
        self.parentwindow=parentwindow
        self.queryresult={}

    def run(self):
        QgsMessageLog.logMessage('Started task "{}"'.format(self.description()), MESSAGE_CATEGORY, Qgis.Info)
        QgsMessageLog.logMessage('Started task "{}"'.format(
                "SELECT ?con ?rel ?val WHERE { "+ str(
                    self.searchTerm) + " ?rel ?val . }"), MESSAGE_CATEGORY, Qgis.Info)
        thequery="SELECT ?rel ?val WHERE { <" + str(self.searchTerm) + ">  ?rel ?val . }"
        results = SPARQLUtils.executeQuery(self.triplestoreurl,thequery,self.triplestoreconf)
        QgsMessageLog.logMessage("Query results: " + str(results), MESSAGE_CATEGORY, Qgis.Info)
        for result in results["results"]["bindings"]:
            if "rel" in result and "val" in result:
                #QgsMessageLog.logMessage("Query results: " + str(result["rel"]["value"]), MESSAGE_CATEGORY, Qgis.Info)
                self.queryresult[result["rel"]["value"]]={"rel":result["rel"]["value"],"val":result["val"]["value"]}
                if "datatype" in result["val"]:
                    self.queryresult[result["rel"]["value"]]["valtype"]=result["val"]["datatype"]
                elif not result["val"]["value"].startswith("http"):
                    self.queryresult[result["rel"]["value"]]["valtype"] ="http://www.w3.org/2001/XMLSchema#string"
                else:
                    self.queryresult[result["rel"]["value"]]["valtype"] = result["val"]["value"]
        return True

    def finished(self, result):
        while self.searchResult.rowCount()>0:
            self.searchResult.removeRow(0)
        self.searchResult.setHorizontalHeaderLabels(["Selection","Attribute", "Value"])
        counter=0
        for rel in self.queryresult:
            QgsMessageLog.logMessage("Query results: " + str(rel), MESSAGE_CATEGORY, Qgis.Info)
            self.searchResult.insertRow(counter)
            itemchecked = QTableWidgetItem()
            itemchecked.setFlags(Qt.ItemIsUserCheckable |
                                 Qt.ItemIsEnabled)
            itemchecked.setCheckState(Qt.Checked)
            if rel in SPARQLUtils.geoproperties:
                if SPARQLUtils.geoproperties[rel]=="DatatypeProperty":
                    itemchecked.setIcon(SPARQLUtils.geodatatypepropertyicon)
                    itemchecked.setToolTip("Geo Datatype Property")
                    itemchecked.setText("GeoDP")
                elif SPARQLUtils.geoproperties[rel]=="ObjectProperty":
                    itemchecked.setIcon(SPARQLUtils.geoobjectpropertyicon)
                    itemchecked.setToolTip("Geo Object Property")
                    itemchecked.setText("GeoOP")
            elif self.queryresult[rel]["val"].startswith("http"):
                    itemchecked.setIcon(SPARQLUtils.objectpropertyicon)
                    itemchecked.setToolTip("Object Property")
                    itemchecked.setText("OP")
            elif SPARQLUtils.namespaces["rdfs"] in rel \
                        or SPARQLUtils.namespaces["owl"] in rel\
                        or SPARQLUtils.namespaces["dc"] in rel:
                    itemchecked.setIcon(SPARQLUtils.annotationpropertyicon)
                    itemchecked.setToolTip("Annotation Property")
                    itemchecked.setText("AP")
            else:
                itemchecked.setIcon(SPARQLUtils.datatypepropertyicon)
                itemchecked.setToolTip("DataType Property")
                itemchecked.setText("DP")
            if "geometryproperty" in self.triplestoreconf and rel in self.triplestoreconf["geometryproperty"]:
                myGeometryInstanceJSON=LayerUtils.processLiteral(self.queryresult[rel]["val"],
                    (self.queryresult[rel]["valtype"] if "valtype" in self.queryresult[rel] else ""),
                    True,self.triplestoreconf)
                if myGeometryInstanceJSON!=None:
                    geojson = {'type': 'FeatureCollection', 'features': [
                    {'id': str(self.searchTerm), 'type': 'Feature', 'properties': {},
                        'geometry': json.loads(myGeometryInstanceJSON)}
                    ]}
                    QgsMessageLog.logMessage(str(geojson), MESSAGE_CATEGORY, Qgis.Info)
                    self.features = QgsVectorLayer(json.dumps(geojson), str(self.searchTerm),
                                            "ogr")
                    self.features.setCrs(QgsCoordinateReferenceSystem(3857))
                    QgsProject.instance().addMapLayer(self.features)
                    layerlist=self.mymap.layers()
                    layerlist.insert(0,self.features)
                    self.features.invertSelection()
                    self.mymap.setLayers(layerlist)
                    self.mymap.setCurrentLayer(self.features)
                    self.mymap.zoomToSelected(self.features)
                    self.parentwindow.resize(QSize(self.parentwindow.width() + 250, self.parentwindow.height()))
                    self.mymap.show()
            self.searchResult.setItem(counter, 0, itemchecked)
            item = QTableWidgetItem()
            item.setText(SPARQLUtils.labelFromURI(rel,self.prefixes))
            item.setData(256, str(rel))
            item.setToolTip("<html><b>Property URI</b> " + str(rel) + "<br>Double click to view definition in web browser")
            self.searchResult.setItem(counter, 1, item)
            itembutton = QTableWidgetItem()
            itembutton.setText(self.queryresult[rel]["val"])
            itembutton.setData(256, self.queryresult[rel]["valtype"])
            self.searchResult.setItem(counter, 2, itembutton)
            counter+=1
