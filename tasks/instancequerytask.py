from ..util.sparqlutils import SPARQLUtils
from ..util.layerutils import LayerUtils
from qgis.core import Qgis, QgsFeature, QgsVectorLayer, QgsCoordinateReferenceSystem
from qgis.PyQt.QtCore import Qt, QSize
from qgis.PyQt.QtGui import QStandardItem
from qgis.core import QgsProject,QgsTask, QgsMessageLog
import json

MESSAGE_CATEGORY = 'InstanceQueryTask'

class InstanceQueryTask(QgsTask):

    def __init__(self, description, triplestoreurl, searchTerm, triplestoreconf, searchResultModel,mymap=None,features=None,parentwindow=None):
        super().__init__(description, QgsTask.CanCancel)
        self.exception = None
        self.triplestoreurl = triplestoreurl
        self.searchTerm=searchTerm
        self.features=features
        self.searchResultModel=searchResultModel
        self.mymap=mymap
        self.prefixes= SPARQLUtils.invertPrefixes(triplestoreconf["prefixes"])
        self.triplestoreconf=triplestoreconf
        self.parentwindow=parentwindow
        self.queryresult={}

    def run(self):
        QgsMessageLog.logMessage('Started task "{}"'.format(self.description()), MESSAGE_CATEGORY, Qgis.Info)
        QgsMessageLog.logMessage('Started task "{}"'.format("SELECT ?con ?rel ?val WHERE { "+ str(self.searchTerm) + " ?rel ?val . }"), MESSAGE_CATEGORY, Qgis.Info)
        thequery="SELECT ?rel ?val WHERE { <" + str(self.searchTerm) + ">  ?rel ?val .  }"
        if "geotriplepattern" in self.triplestoreconf:
            thequery = "SELECT ?rel ?val ?"+"?".join(self.triplestoreconf["mandatoryvariables"][1:])+" WHERE { <" + str(self.searchTerm) + "> ?rel ?val . OPTIONAL { "+str(self.triplestoreconf["geotriplepattern"][0]).replace("?item ","<"+str(self.searchTerm)+"> ")+" } }"
        results = SPARQLUtils.executeQuery(self.triplestoreurl,thequery,self.triplestoreconf)
        #QgsMessageLog.logMessage("Query results: " + str(results), MESSAGE_CATEGORY, Qgis.Info)
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
            if "geo" in result:
                self.queryresult["geo"]={"value":result["geo"]["value"],"valtype":result["geo"]["datatype"]}
        return True

    def finished(self, result):
        while self.searchResultModel.rowCount()>0:
            self.searchResultModel.removeRow(0)
        counter=0
        for rel in self.queryresult:
            #QgsMessageLog.logMessage("Query results: " + str(rel), MESSAGE_CATEGORY, Qgis.Info)
            if rel!="geo":
                self.searchResultModel.insertRow(counter)
            itemchecked = QStandardItem()
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
            elif rel!="geo" and self.queryresult[rel]["val"].startswith("http"):
                    itemchecked.setIcon(SPARQLUtils.objectpropertyicon)
                    itemchecked.setToolTip("Object Property")
                    itemchecked.setText("OP")
            elif SPARQLUtils.namespaces["rdfs"] in rel \
                        or SPARQLUtils.namespaces["owl"] in rel\
                        or SPARQLUtils.namespaces["dc"] in rel\
                        or SPARQLUtils.namespaces["skos"] in rel:
                    itemchecked.setIcon(SPARQLUtils.annotationpropertyicon)
                    itemchecked.setToolTip("Annotation Property")
                    itemchecked.setText("AP")
            elif rel!="geo":
                itemchecked.setIcon(SPARQLUtils.datatypepropertyicon)
                itemchecked.setToolTip("DataType Property")
                itemchecked.setText("DP")
            if "geometryproperty" in self.triplestoreconf and (rel in self.triplestoreconf["geometryproperty"] or rel=="geo"):
                myGeometryInstanceJSON=None
                encounteredcrs=None
                if isinstance(self.triplestoreconf["geometryproperty"],str) \
                        or (type(self.triplestoreconf["geometryproperty"]) is list and len(self.triplestoreconf["geometryproperty"])==1):
                    if "geo" in self.queryresult:
                        myGeometryInstanceJSON=LayerUtils.processLiteral(self.queryresult["geo"]["value"],
                        (self.queryresult["geo"]["valtype"] if "valtype" in self.queryresult["geo"] else ""),
                        True,self.triplestoreconf)
                    else:
                        myGeometryInstanceJSON=LayerUtils.processLiteral(self.queryresult[rel]["val"],
                        (self.queryresult[rel]["valtype"] if "valtype" in self.queryresult[rel] else ""),
                        True,self.triplestoreconf)
                    if "crs" in myGeometryInstanceJSON and myGeometryInstanceJSON["crs"]!=None:
                        encounteredcrs=int(myGeometryInstanceJSON["crs"])
                        del myGeometryInstanceJSON["crs"]
                elif len(self.triplestoreconf["geometryproperty"])==2 and self.triplestoreconf["geometryproperty"][0] in self.queryresult and self.triplestoreconf["geometryproperty"][1] in self.queryresult:
                    myGeometryInstanceJSON=LayerUtils.processLiteral("POINT(" + str(float(self.queryresult[self.triplestoreconf["geometryproperty"][0]]["val"])) + " " + str(
                        float(self.queryresult[self.triplestoreconf["geometryproperty"][1]]["val"])) + ")", "wkt", True, self.triplestoreconf)
                if myGeometryInstanceJSON!=None:
                    geojson = {'type': 'FeatureCollection', 'features': [
                    {'id': str(self.searchTerm), 'type': 'Feature', 'properties': {},
                        'geometry': myGeometryInstanceJSON}
                    ]}
                    QgsMessageLog.logMessage(str(geojson), MESSAGE_CATEGORY, Qgis.Info)
                    self.features = QgsVectorLayer(json.dumps(geojson), str(self.searchTerm),"ogr")
                    featuress = self.features.getFeatures()
                    geomcentroidpoint=None
                    for feat in featuress:
                        geomcentroidpoint = feat.geometry().centroid().asPoint()
                    if encounteredcrs!=None:
                        crs = self.features.crs()
                        crs.createFromId(encounteredcrs)
                        self.features.setCrs(crs)
                    else:
                        self.features.setCrs(QgsCoordinateReferenceSystem(4326))
                    layerlist=self.mymap.layers()
                    layerlist.insert(0,self.features)
                    self.mymap.setLayers(layerlist)
                    self.mymap.setCurrentLayer(self.features)
                    #if geomcentroidpoint != None:
                    #    self.mymap.zoomWithCenter(geomcentroidpoint.x(), geomcentroidpoint.y(), True)
                    self.mymap.show()
            if rel!="geo":
                self.searchResultModel.setItem(counter, 0, itemchecked)
                item = QStandardItem()
                item.setText(SPARQLUtils.labelFromURI(rel,self.prefixes))
                item.setData(str(rel),256)
                item.setToolTip("<html><b>Property URI</b> " + str(rel) + "<br>Double click to view definition in web browser")
                self.searchResultModel.setItem(counter, 1, item)
                itembutton = QStandardItem()
                itembutton.setText(self.queryresult[rel]["val"])
                itembutton.setData(self.queryresult[rel]["valtype"],256)
                self.searchResultModel.setItem(counter, 2, itembutton)
                counter+=1
        self.searchResultModel.setHeaderData(0, Qt.Horizontal, "Selection")
        self.searchResultModel.setHeaderData(1, Qt.Horizontal, "Attribute")
        self.searchResultModel.setHeaderData(2, Qt.Horizontal, "Value")
