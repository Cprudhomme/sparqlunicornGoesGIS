# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SPAQLunicorn
                                 A QGIS plugin
 This plugin adds a GeoJSON layer from a Wikidata SPARQL query.
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2019-10-28
        git sha              : $Format:%H$
        copyright            : (C) 2019 by SPARQL Unicorn
        email                : rse@fthiery.de
        developer(s)         : Florian Thiery,  Timo Homburg
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

from qgis.utils import iface
from qgis.core import Qgis, QgsMessageLog

from qgis.PyQt.QtCore import QSettings, QCoreApplication, QRegExp, QVariant, Qt, QItemSelectionModel, QTranslator
from qgis.PyQt.QtGui import QIcon, QRegExpValidator, QBrush, QColor, QStandardItem
from qgis.PyQt.QtWidgets import QAction, QComboBox, QCompleter, QFileDialog, QTableWidgetItem, QHBoxLayout, QPushButton, \
    QWidget, QMessageBox, QProgressDialog, QListWidgetItem, QStyle
from qgis.core import QgsProject, QgsGeometry, QgsVectorLayer, QgsExpression, QgsFeatureRequest, \
    QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsApplication, QgsWkbTypes, QgsField
from .resources import *
import os.path
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "dependencies")))
from .util.sparqlutils import SPARQLUtils
from .util.layerutils import LayerUtils

import json

from rdflib import *

# Initialize Qt resources from file resources.py
from .tasks.querylayertask import QueryLayerTask
from .tasks.classtreequerytask import ClassTreeQueryTask
from .tasks.geoconceptsquerytask import GeoConceptsQueryTask
from .tasks.geocollectionsquerytask import GeoCollectionsQueryTask
# Import the code for the dialog
from .dialogs.uploadrdfdialog import UploadRDFDialog
from .dialogs.loginwindowdialog import LoginWindowDialog
from .dialogs.sparql_unicorn_dialog import SPARQLunicornDialog

geoconcepts = ""

## The main SPARQL unicorn dialog.
#
class SPARQLunicorn:
    """QGIS Plugin Implementation."""
    loadedfromfile = False

    enrichedExport = False

    exportNameSpace = None

    exportIdCol = None

    exportSetClass = None
    # Triple store configuration map
    triplestoreconf = None

    enrichLayer = None

    qtask = None

    currentgraph = None

    originalRowCount = 0

    enrichLayerCounter = 0

    addVocabConf = None

    savedQueriesJSON = {}

    exportColConfig = {}

    valueconcept = {}

    columnvars = {}

    prefixes = []

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'SPAQLunicorn_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&SPARQL Unicorn Wikidata Plugin')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('SPAQLunicorn', message)

    def add_action(
            self,
            icon_path,
            text,
            callback,
            enabled_flag=True,
            add_to_menu=True,
            add_to_toolbar=True,
            status_tip=None,
            whats_this=None,
            parent=None):
        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToVectorMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        # a = str('numpy' in sys.modules)
        # iface.messageBar().pushMessage("load libs", a, level=Qgis.Success)

        icon_path = ':/icons/resources/icons/sparqlunicorn.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Adds GeoJSON layer from a Wikidata'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True

    ## Removes the plugin menu item and icon from QGIS GUI.
    #  @param self The object pointer.
    def unload(self):
        for action in self.actions:
            self.iface.removePluginVectorMenu(
                self.tr(u'&SPARQL Unicorn Wikidata Plugin'),
                action)
            self.iface.removeToolBarIcon(action)

    ## Creates a layer from the result of the given SPARQL unicorn query.
    #  @param self The object pointer.
    def create_unicorn_layer(self):
        endpointIndex = self.dlg.comboBox.currentIndex()
        # SPARQL query
        # print(self.loadedfromfile)
        # query
        query = self.dlg.inp_sparql2.toPlainText()
        if self.loadedfromfile:
            curindex = self.dlg.proxyModel.mapToSource(self.dlg.geoTreeView.selectionModel().currentIndex())
            if curindex != None and self.dlg.geoTreeViewModel.itemFromIndex(curindex) != None:
                concept = self.dlg.geoTreeViewModel.itemFromIndex(curindex).data(256)
            else:
                concept = "http://www.opengis.net/ont/geosparql#Feature"
            geojson = self.getGeoJSONFromGeoConcept(self.currentgraph, concept)
            vlayer = QgsVectorLayer(json.dumps(geojson, sort_keys=True, indent=4),
                                    "unicorn_" + self.dlg.inp_label.text(), "ogr")
            print(vlayer.isValid())
            QgsProject.instance().addMapLayer(vlayer)
            canvas = iface.mapCanvas()
            canvas.setExtent(vlayer.extent())
            iface.messageBar().pushMessage("Add layer", "OK", level=Qgis.Success)
            # iface.messageBar().pushMessage("Error", "An error occured", level=Qgis.Critical)
            # self.dlg.close()
            return
        else:
            endpoint_url = self.triplestoreconf[endpointIndex]["endpoint"]
        missingmandvars = []
        for mandvar in self.triplestoreconf[endpointIndex]["mandatoryvariables"]:
            if mandvar not in query:
                missingmandvars.append("?" + mandvar)
        if missingmandvars != [] and not self.dlg.allownongeo.isChecked():
            msgBox = QMessageBox()
            msgBox.setWindowTitle("Mandatory variables missing!")
            msgBox.setText("The SPARQL query is missing the following mandatory variables: " + str(missingmandvars))
            msgBox.exec()
            return
        progress = QProgressDialog("Querying layer from " + endpoint_url + "...", "Abort", 0, 0, self.dlg)
        progress.setWindowTitle("Query layer")
        progress.setWindowModality(Qt.WindowModal)
        progress.setCancelButton(None)
        progress.show()
        queryprefixes = []
        prefixestoadd = ""
        for line in query.split("\n"):
            if line.startswith("PREFIX"):
                queryprefixes.append(line[line.find("http"):].replace(">", ""))
                url = line[line.find("http"):].replace(">", "")
        for endpoint in self.triplestoreconf[endpointIndex]["prefixes"]:
            if not self.triplestoreconf[endpointIndex]["prefixes"][endpoint] in queryprefixes:
                prefixestoadd += "PREFIX " + endpoint + ": <" + self.triplestoreconf[endpointIndex]["prefixes"][
                    endpoint] + "> \n"
        self.qtask = QueryLayerTask("Querying QGIS Layer from " + endpoint_url,
                                    endpoint_url,
                                    prefixestoadd + query, self.triplestoreconf[endpointIndex],
                                    self.dlg.allownongeo.isChecked(), self.dlg.inp_label.text(), progress)
        QgsApplication.taskManager().addTask(self.qtask)
        # self.dlg.close()

    ## Gets a set of geometric concepts from the selected triple store.
    #  @param self The object pointer.
    #  @param triplestoreurl the url of the SPARQL endpoint
    #  @param query the query to execute
    #  @param queryvar the queryvariable returning the geoconcepts
    #  @param graph the graph to query if to query from a file
    #  @param getlabels indicates whether to also query labels for the returned geoconcepts
    def getGeoConcepts(self, triplestoreurl, query, queryvar, graph, getlabels, examplequery):
        viewlist = []
        resultlist = []
        if graph != None:
            results = graph.query(query)
            self.dlg.autocomplete["completerClassList"] = {}
            for row in results:
                viewlist.append(str(row[0]))
                self.dlg.autocomplete["completerClassList"][row] = str(row[0])
            self.dlg.conceptViewTabWidget.setTabText(0, "GeoConcepts (" + str(len(viewlist)) + ")")
            return viewlist
        self.qtask = GeoConceptsQueryTask("Querying GeoConcepts from " + triplestoreurl,
                                          triplestoreurl,
                                          query, self.triplestoreconf[self.dlg.comboBox.currentIndex()],
                                          self.dlg.inp_sparql2, queryvar, getlabels, self.dlg.layercount,
                                          self.dlg.geoTreeViewModel, examplequery, self.dlg.geoTreeView,
                                          self.dlg.autocomplete, self.dlg)
        QgsApplication.taskManager().addTask(self.qtask)

    def getClassTree(self):
        self.dlg.classTreeViewModel.clear()
        item2 = QStandardItem()
        item2.setText("Loading...")
        self.dlg.classTreeViewModel.appendRow(item2)
        self.qtaskctree = ClassTreeQueryTask(
            "Getting classtree for " + self.triplestoreconf[self.dlg.comboBox.currentIndex()]["endpoint"],
            self.triplestoreconf[self.dlg.comboBox.currentIndex()]["endpoint"],
            self.dlg, self.dlg.classTreeViewModel.invisibleRootItem(),self.triplestoreconf[self.dlg.comboBox.currentIndex()])
        QgsApplication.taskManager().addTask(self.qtaskctree)

    def getGeoCollectionInstances(self, triplestoreurl, query, queryvar, graph, featureOrGeoCollection, examplequery):
        viewlist = []
        resultlist = []
        if graph != None:
            results = graph.query(query)
            self.dlg.autocomplete["completerClassList"] = {}
            for row in results:
                viewlist.append(str(row[0]))
                self.dlg.autocomplete["completerClassList"][row] = str(row[0])
            return viewlist
        QgsMessageLog.logMessage('Started task "{}"'.format(str(query)), "SPARQL Unicorn", Qgis.Info)
        if featureOrGeoCollection:
            self.qtaskfeature = GeoCollectionsQueryTask("Querying FeatureCollections from " + triplestoreurl,
                                                        triplestoreurl,
                                                        query, self.triplestoreconf[self.dlg.comboBox.currentIndex()],
                                                        self.dlg.inp_sparql2, queryvar, "label", featureOrGeoCollection,
                                                        self.dlg.layercount,
                                                        self.dlg.featureCollectionClassListModel, examplequery,
                                                        self.dlg.featureCollectionClassList,
                                                        self.dlg.autocomplete, self.dlg)
            QgsApplication.taskManager().addTask(self.qtaskfeature)
        else:
            self.qtaskgeos = GeoCollectionsQueryTask("Querying GeometryCollections from " + triplestoreurl,
                                                     triplestoreurl,
                                                     query, self.triplestoreconf[self.dlg.comboBox.currentIndex()],
                                                     self.dlg.inp_sparql2, queryvar, "label", featureOrGeoCollection,
                                                     self.dlg.layercount,
                                                     self.dlg.geometryCollectionClassListModel, examplequery,
                                                     self.dlg.geometryCollectionClassList,
                                                     self.dlg.autocomplete, self.dlg)
            QgsApplication.taskManager().addTask(self.qtaskgeos)

    ## Selects a SPARQL endpoint and changes its configuration accordingly.
    #  @param self The object pointer.
    def endpointselectaction(self):
        endpointIndex = self.dlg.comboBox.currentIndex()
        self.dlg.queryTemplates.clear()
        self.dlg.filterConcepts.setText("")
        print("changing endpoint")
        QgsMessageLog.logMessage('Started task "{}"'.format(self.triplestoreconf[endpointIndex]), "SPARQLUnicorn", Qgis.Info)
        conceptlist = []
        self.dlg.geoTreeViewModel.clear()
        self.dlg.geometryCollectionClassListModel.clear()
        self.dlg.featureCollectionClassListModel.clear()
        self.dlg.conceptViewTabWidget.setTabText(0, "GeoConcepts")
        self.dlg.conceptViewTabWidget.setTabText(1, "FeatureCollections")
        self.dlg.conceptViewTabWidget.setTabText(2, "GeometryCollections")
        self.dlg.conceptViewTabWidget.setTabText(3, "ClassTree")
        self.dlg.savedQueries.clear()
        if "prefixesrev" not in self.triplestoreconf[endpointIndex]:
            self.triplestoreconf[endpointIndex]["prefixesrev"]=SPARQLUtils.invertPrefixes(self.triplestoreconf[endpointIndex]["prefixes"])
        if "endpoint" in self.triplestoreconf[endpointIndex] and self.triplestoreconf[endpointIndex][
            "endpoint"] in self.savedQueriesJSON:
            for item in self.savedQueriesJSON[self.triplestoreconf[endpointIndex]["endpoint"]]:
                self.dlg.savedQueries.addItem(item["label"])
        if "endpoint" in self.triplestoreconf[endpointIndex] and self.triplestoreconf[endpointIndex][
            "endpoint"] != "" and (
                not "staticconcepts" in self.triplestoreconf[endpointIndex] or "staticconcepts" in self.triplestoreconf[
            endpointIndex] and self.triplestoreconf[endpointIndex]["staticconcepts"] == []) and "geoconceptquery" in \
                self.triplestoreconf[endpointIndex] and self.triplestoreconf[endpointIndex]["geoconceptquery"] != "":
            item = QStandardItem()
            item.setText("Loading...")
            self.dlg.geoTreeViewModel.appendRow(item)
            item2 = QStandardItem()
            item2.setText("Loading...")
            self.dlg.classTreeViewModel.appendRow(item)
            if "examplequery" in self.triplestoreconf[endpointIndex]:
                self.getGeoConcepts(self.triplestoreconf[endpointIndex]["endpoint"],
                                    self.triplestoreconf[endpointIndex]["geoconceptquery"], "class", None,
                                    True, self.triplestoreconf[endpointIndex]["examplequery"])
            elif "geoconceptquery" in self.triplestoreconf[endpointIndex]:
                self.getGeoConcepts(self.triplestoreconf[endpointIndex]["endpoint"],
                                    self.triplestoreconf[endpointIndex]["geoconceptquery"], "class", None,
                                    True, None)
        elif "staticconcepts" in self.triplestoreconf[endpointIndex] and self.triplestoreconf[endpointIndex][
            "staticconcepts"] != []:
            conceptlist = self.triplestoreconf[endpointIndex]["staticconcepts"]
            self.dlg.autocomplete["completerClassList"] = {}
            self.dlg.conceptViewTabWidget.setTabText(0, "GeoConcepts (" + str(len(conceptlist)) + ")")
            for concept in conceptlist:
                item = QStandardItem()
                item.setData(concept, 256)
                item.setText(SPARQLUtils.labelFromURI(concept, self.triplestoreconf[endpointIndex]["prefixesrev"]))
                item.setIcon(SPARQLUtils.geoclassicon)
                item.setData(SPARQLUtils.geoclassnode,257)
                self.dlg.autocomplete["completerClassList"][SPARQLUtils.labelFromURI(concept)] = "<" + concept + ">"
                self.dlg.geoTreeViewModel.appendRow(item)
            self.dlg.inp_sparql2.updateNewClassList()
            if len(conceptlist) > 0:
                self.dlg.geoTreeView.selectionModel().setCurrentIndex(self.dlg.geoTreeView.model().index(0, 0),
                                                                      QItemSelectionModel.SelectCurrent)
            if "examplequery" in self.triplestoreconf[endpointIndex]:
                self.dlg.inp_sparql2.setPlainText(self.triplestoreconf[endpointIndex]["examplequery"])
                self.dlg.inp_sparql2.columnvars = {}
        if "File" not in self.triplestoreconf[endpointIndex]["name"] and "wikidata" not in self.triplestoreconf[endpointIndex]["endpoint"]:
            self.getClassTree()
        if "geocollectionquery" in self.triplestoreconf[endpointIndex]:
            query = str(self.triplestoreconf[endpointIndex]["geocollectionquery"])
            QgsMessageLog.logMessage('Started task "{}"'.format(str(query)), "SPARQL Unicorn", Qgis.Info)
            if "featurecollectionclasses" in self.triplestoreconf[endpointIndex] and \
                    self.triplestoreconf[endpointIndex]["featurecollectionclasses"] != None and \
                    self.triplestoreconf[endpointIndex]["featurecollectionclasses"] != "":
                valstatement = "VALUES ?collclass {"
                for featclass in self.triplestoreconf[endpointIndex]["featurecollectionclasses"]:
                    valstatement += "<" + str(featclass) + "> "
                valstatement += "} "
                querymod = query.replace("%%concept%% .", "?collclass . ?collclass " + str(valstatement))
            else:
                rep = "<http://www.opengis.net/ont/geosparql#FeatureCollection>"
                querymod = str(self.triplestoreconf[endpointIndex]["geocollectionquery"]).replace("%%concept%% .", rep)
            QgsMessageLog.logMessage('Started task "{}"'.format(str(query)), "SPARQL Unicorn", Qgis.Info)
            self.getGeoCollectionInstances(self.triplestoreconf[endpointIndex]["endpoint"],
                                           querymod, "colinstance", None,
                                           True, None)
            query = str(self.triplestoreconf[endpointIndex]["geocollectionquery"])
            if "geometrycollectionclasses" in self.triplestoreconf[endpointIndex] and \
                    self.triplestoreconf[endpointIndex]["geometrycollectionclasses"] != None and \
                    self.triplestoreconf[endpointIndex]["geometrycollectionclasses"] != "":
                valstatement = "VALUES ?collclass {"
                for geoclass in self.triplestoreconf[endpointIndex]["geometrycollectionclasses"]:
                    valstatement += "<" + str(geoclass) + "> "
                valstatement += "} "
                querymod = query.replace("%%concept%% .", "?collclass . ?collclass " + str(valstatement))
            else:
                rep = "<http://www.opengis.net/ont/geosparql#GeometryCollection>"
                querymod = str(self.triplestoreconf[endpointIndex]["geocollectionquery"]).replace("%%concept%% .", rep)
            QgsMessageLog.logMessage('Started task "{}"'.format(str(query)), "SPARQL Unicorn", Qgis.Info)
            self.getGeoCollectionInstances(self.triplestoreconf[endpointIndex]["endpoint"],
                                           querymod, "colinstance", None,
                                           False, None)
        """
        if "areaconcepts" in self.triplestoreconf[endpointIndex] and self.triplestoreconf[endpointIndex][
            "areaconcepts"]:
            conceptlist2 = self.triplestoreconf[endpointIndex]["areaconcepts"]
            for concept in conceptlist2:
                self.dlg.areaconcepts.addItem(concept["concept"])
        """
        if "querytemplate" in self.triplestoreconf[endpointIndex]:
            for concept in self.triplestoreconf[endpointIndex]["querytemplate"]:
                self.dlg.queryTemplates.addItem(concept["label"])
        if self.triplestoreconf[endpointIndex]["endpoint"] in self.savedQueriesJSON:
            self.dlg.savedQueries.clear()
            for concept in self.savedQueriesJSON[self.triplestoreconf[endpointIndex]["endpoint"]]:
                self.dlg.savedQueries.addItem(concept["label"])

    ## Gets GeoJSON reperesentations from a graph given by an RDF file or data source.
    #  @param self The object pointer.
    #  @param self The rdf graph
    #  @param self The concept to search for
    def getGeoJSONFromGeoConcept(self, graph, concept):
        print(concept)
        qres = graph.query(
            """SELECT DISTINCT ?a ?rel ?val ?wkt
        WHERE {
          ?a rdf:type <""" + str(concept) + """> .
          ?a ?rel ?val .
          OPTIONAL { ?val <http://www.opengis.net/ont/geosparql#asWKT> ?wkt}
        }""")
        geos = []
        geometries = {
            'type': 'FeatureCollection',
            'features': geos,
        }
        newfeature = False
        lastfeature = ""
        currentgeo = {}
        for row in qres:
            print(lastfeature + " - " + row[0] + " - " + str(len(row)))
            print(row)
            if (lastfeature == "" or lastfeature != row[0]):
                if (lastfeature != ""):
                    geos.append(currentgeo)
                lastfeature = row[0]
                currentgeo = {'id': row[0], 'geometry': {}, 'properties': {}}
            if (row[3] != None):
                print(row[3])
                if ("<" in row[3]):
                    currentgeo['geometry'] = json.loads(QgsGeometry.fromWkt(row[3].split(">")[1].strip()).asJson())
                else:
                    currentgeo['geometry'] = json.loads(QgsGeometry.fromWkt(row[3]).asJson())
            else:
                currentgeo['properties'][str(row[1])] = str(row[2])
        return geometries

    def useDefaultIDPropProcess(self):
        self.dlg.findIDPropertyEdit.setText("http://www.w3.org/2000/01/rdf-schema#label")

    def matchColumnValueFromTripleStore(self, toquery):
        values = "VALUES ?vals { "
        for queryval in toquery:
            values += "\"" + queryval + "\""
        values += "}"
        results=SPARQLUtils.executeQuery("https://query.wikidata.org/sparql","""SELECT DISTINCT ?a
        WHERE {
          ?a wdt:P31 ?class .
          ?a ?label ?vals .
        } """)
        for result in results["results"]["bindings"]:
            self.viewlist.append(str(result["a"]["value"]))
        return self.viewlist

    def exportLayer2(self):
        self.exportLayer(None, None, None, None, None, None, self.dlg.exportTripleStore_2.isChecked())

    ## Creates the export layer dialog for exporting layers as TTL.
    #  @param self The object pointer.
    def exportLayer(self, urilist=None, classurilist=None, includelist=None, proptypelist=None, valuemappings=None,
                    valuequeries=None, exportToTripleStore=False):
        layers = QgsProject.instance().layerTreeRoot().children()
        if self.enrichedExport:
            selectedLayerIndex = self.dlg.chooseLayerInterlink.currentIndex()
        else:
            selectedLayerIndex = self.dlg.loadedLayers.currentIndex()
        layer = layers[selectedLayerIndex].layer()
        if exportToTripleStore:
            ttlstring = LayerUtils.layerToTTLString(layer,"".join(self.prefixes[self.dlg.comboBox.currentIndex()]), urilist, classurilist, includelist, proptypelist, valuemappings,
                                              valuequeries)
            uploaddialog = UploadRDFDialog(ttlstring, self.triplestoreconf, self.dlg.comboBox.currentIndex())
            uploaddialog.setMinimumSize(450, 250)
            uploaddialog.setWindowTitle("Upload interlinked dataset to triple store ")
            uploaddialog.exec_()
        else:
            filename, _filter = QFileDialog.getSaveFileName(
                self.dlg, "Select   output file ", "", "Linked Data (*.ttl *.n3 *.nt *.graphml)", )
            if filename == "":
                return
            if filename.endswith("graphml"):
                ttlstring = LayerUtils.layerToGraphML(layer)
            else:
                ttlstring = LayerUtils.layerToTTLString(layer, "".join(self.prefixes[self.dlg.comboBox.currentIndex()]),
                                                        urilist, classurilist, includelist, proptypelist, valuemappings,
                                                        valuequeries)
            with open(filename, 'w') as output_file:
                output_file.write(ttlstring)
                iface.messageBar().pushMessage("export layer successfully!", "OK", level=Qgis.Success)
            if not filename.endswith("graphml"):
                g = Graph()
                g.parse(data=ttlstring, format="ttl")
                splitted = filename.split(".")
                exportNameSpace = ""
                exportSetClass = ""
                with open(filename, 'w') as output_file:
                    output_file.write(g.serialize(format=splitted[len(splitted) - 1]).decode("utf-8"))
                    iface.messageBar().pushMessage("export layer successfully!", "OK", level=Qgis.Success)

    ## Saves a personal copy of the triplestore configuration file to disk.
    #  @param self The object pointer.
    def saveTripleStoreConfig(self):
        __location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
        with open(os.path.join(__location__, 'conf/triplestoreconf_personal.json'), 'w') as myfile:
            myfile.write(json.dumps(self.triplestoreconf, indent=2))

    ## Restores the triple store configuration file with the version delivered with the SPARQLUnicorn QGIS plugin.
    #  @param self The object pointer.
    def resetTripleStoreConfig(self):
        __location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
        with open(os.path.join(__location__, 'conf/triplestoreconf.json'), 'r') as myfile:
            data = myfile.read()
        self.triplestoreconf = json.loads(data)
        with open(os.path.join(__location__, 'conf/triplestoreconf_personal.json'), 'w') as myfile:
            myfile.write(json.dumps(self.triplestoreconf, indent=2))

    def createLoginWindow(self):
        LoginWindowDialog(self).exec()

    def run(self):
        """Run method that performs all the real work"""
        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        if self.first_start == True:
            __location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
            if os.path.isfile(os.path.join(__location__, 'conf/triplestoreconf_personal.json')):
                with open(os.path.join(__location__, 'conf/triplestoreconf_personal.json'), 'r') as myfile:
                    data = myfile.read()
            else:
                with open(os.path.join(__location__, 'conf/triplestoreconf.json'), 'r') as myfile:
                    data = myfile.read()
            # parse file
            with open(os.path.join(__location__, 'owl/addvocabconf.json'), 'r') as myfile:
                data2 = myfile.read()
            with open(os.path.join(__location__, 'owl/vocabs.json'), 'r') as myfile:
                data3 = myfile.read()
            with open(os.path.join(__location__, 'owl/prefixes.json'), 'r') as myfile:
                data4 = myfile.read()
            if os.path.isfile(os.path.join(__location__, 'conf/savedqueries.json')):
                with open(os.path.join(__location__, 'conf/savedqueries.json'), 'r') as myfile:
                    data5 = myfile.read()
                self.savedQueriesJSON = json.loads(data5)
            self.triplestoreconf = json.loads(data)
            self.addVocabConf = json.loads(data2)
            self.autocomplete = json.loads(data3)
            self.prefixstore = json.loads(data4)

            counter = 0
            for store in self.triplestoreconf:
                self.prefixes.append("")
                for prefix in store["prefixes"]:
                    self.prefixes[counter] += "PREFIX " + prefix + ":<" + store["prefixes"][prefix] + ">\n"
                counter += 1
            self.addVocabConf = json.loads(data2)
            self.saveTripleStoreConfig()
            self.first_start = False
            self.dlg = SPARQLunicornDialog(self.triplestoreconf, self.prefixes, self.addVocabConf, self.autocomplete,
                                           self.prefixstore, self.savedQueriesJSON, self)
            self.dlg.setWindowIcon(QIcon(':/icons/resources/icons/sparqlunicorn.png'))
            self.dlg.inp_sparql.hide()
            self.dlg.comboBox.clear()
            for triplestore in self.triplestoreconf:
                if triplestore["active"]:
                    item = triplestore["name"]
                    if "mandatoryvariables" in triplestore and len(triplestore["mandatoryvariables"]) > 0:
                        item += " --> "
                        for mandvar in triplestore["mandatoryvariables"]:
                            item += "?" + mandvar + " "
                    self.dlg.comboBox.addItem(item)
            self.dlg.comboBox.setCurrentIndex(1)
            self.dlg.viewselectactionClassTree()
            self.dlg.comboBox.currentIndexChanged.connect(self.endpointselectaction)
            self.endpointselectaction()
            # self.dlg.exportTripleStore.hide()
            # self.dlg.exportTripleStore_2.hide()
            # self.dlg.tabWidget.removeTab(2)
            # self.dlg.tabWidget.removeTab(1)
            self.dlg.oauthTestButton.hide()
            self.dlg.oauthTestButton.clicked.connect(self.createLoginWindow)
            self.dlg.loadedLayers.clear()
            self.dlg.pushButton.clicked.connect(self.create_unicorn_layer)
            # self.dlg.geoClassList.doubleClicked.connect(self.create_unicorn_layer)
            self.dlg.exportLayers.clicked.connect(self.exportLayer2)
        else:
            self.dlg.show()
