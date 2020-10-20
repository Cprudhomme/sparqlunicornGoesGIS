# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SPAQLunicornDialog
                                 A QGIS plugin
 This plugin adds a GeoJSON layer from a Wikidata SPARQL query.
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                             -------------------
        begin                : 2019-10-28
        git sha              : $Format:%H$
        copyright            : (C) 2019 by SPARQL Unicorn
        email                : rse@fthiery.de
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

import os
import re
from qgis.PyQt import uic
from qgis.PyQt import QtWidgets
from qgis.PyQt import QtCore
from qgis.core import QgsProject
from qgis.PyQt.QtCore import QRegExp, QSortFilterProxyModel,Qt
from qgis.PyQt.QtGui import QRegExpValidator,QStandardItemModel
from qgis.PyQt.QtWidgets import QComboBox,QCompleter,QTableWidgetItem,QHBoxLayout,QPushButton,QWidget,QAbstractItemView,QListView,QMessageBox
from rdflib.plugins.sparql import prepareQuery
from .whattoenrich import EnrichmentDialog
from .tooltipplaintext import ToolTipPlainText
from .enrichmenttab import EnrichmentTab
from .interlinkingtab import InterlinkingTab
from .triplestoredialog import TripleStoreDialog
from .searchdialog import SearchDialog
from .sparqlhighlighter import SPARQLHighlighter
from .valuemapping import ValueMappingDialog
from .bboxdialog import BBOXDialog
from .loadgraphdialog import LoadGraphDialog

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'sparql_unicorn_dialog_base.ui'))

## 
#  @brief The main dialog window of the SPARQLUnicorn QGIS Plugin.
class SPAQLunicornDialog(QtWidgets.QDialog, FORM_CLASS):
	## The triple store configuration file
    triplestoreconf=None
	## Prefix map
    prefixes=None
	
    enrichtab=None
	
    interlinktab=None
	
    conceptList=None
	
    columnvars={}
	
    def __init__(self,triplestoreconf={},prefixes=[],addVocabConf={},maindlg=None,parent=None):
        """Constructor."""
        super(SPAQLunicornDialog, self).__init__(parent)
        # Set up the user interface from Designer through FORM_CLASS.
        # After self.setupUi() you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        self.prefixes=prefixes
        self.maindlg=maindlg
        self.enrichtab=EnrichmentTab(self)
        self.interlinktab=InterlinkingTab(self)
        self.addVocabConf=addVocabConf
        self.triplestoreconf=triplestoreconf
        self.searchTripleStoreDialog=TripleStoreDialog(self.triplestoreconf,self.comboBox)
        self.geoClassList.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.geoClassList.setAlternatingRowColors(True)
        self.geoClassList.setViewMode(QListView.ListMode)
        self.geoClassListModel=QStandardItemModel()
        self.proxyModel = QSortFilterProxyModel(self)
        self.proxyModel.sort(0)
        self.proxyModel.setSourceModel(self.geoClassListModel)	
        self.geoClassList.setModel(self.proxyModel)
        self.geoClassListModel.clear()  
        self.filterConcepts.textChanged.connect(self.setFilterFromText)
        self.inp_sparql2=ToolTipPlainText(self.tab,self.triplestoreconf,self.comboBox,self.columnvars,self.prefixes)
        self.inp_sparql2.move(10,130)
        self.inp_sparql2.setMinimumSize(811,401)
        self.inp_sparql2.document().defaultFont().setPointSize(16)
        self.inp_sparql2.setPlainText("SELECT ?item ?lat ?lon WHERE {\n ?item ?b ?c .\n ?item <http://www.wikidata.org/prop:P123> ?def .\n}")
        self.inp_sparql2.columnvars={}
        self.inp_sparql2.textChanged.connect(self.validateSPARQL)
        self.sparqlhighlight = SPARQLHighlighter(self.inp_sparql2)
        self.areaconcepts.hide()
        self.areas.hide()
        self.label_8.hide()
        self.label_9.hide()
        self.enrichTableResult.hide()
        self.queryTemplates.currentIndexChanged.connect(self.viewselectaction)
        self.bboxButton.clicked.connect(self.getPointFromCanvas)
        self.interlinkTable.cellClicked.connect(self.createInterlinkSearchDialog)
        self.enrichTable.cellClicked.connect(self.createEnrichSearchDialog)
        self.chooseLayerInterlink.clear()
        self.searchClass.clicked.connect(self.createInterlinkSearchDialog)
        urlregex = QRegExp("http[s]?://(?:[a-zA-Z#]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+")
        urlvalidator = QRegExpValidator(urlregex, self)
        self.interlinkNameSpace.setValidator(urlvalidator)
        self.interlinkNameSpace.textChanged.connect(self.check_state3)
        self.interlinkNameSpace.textChanged.emit(self.interlinkNameSpace.text())
        self.addEnrichedLayerButton.clicked.connect(self.enrichtab.addEnrichedLayer)
        self.startEnrichment.clicked.connect(self.enrichtab.enrichLayerProcess)
        self.exportInterlink.clicked.connect(self.enrichtab.exportEnrichedLayer)
        self.exportMappingButton.clicked.connect(self.interlinktab.exportMapping)
        self.importMappingButton.clicked.connect(self.interlinktab.loadMapping)
        self.loadLayerInterlink.clicked.connect(self.loadLayerForInterlink)
        self.loadLayerEnrich.clicked.connect(self.loadLayerForEnrichment)
        self.addEnrichedLayerRowButton.clicked.connect(self.addEnrichRow)
        self.geoClassList.selectionModel().selectionChanged.connect(self.viewselectaction)
        self.loadFileButton.clicked.connect(self.buildLoadGraphDialog)
        self.refreshLayersInterlink.clicked.connect(self.loadUnicornLayers)
        self.whattoenrich.clicked.connect(self.createWhatToEnrich)
        self.loadTripleStoreButton.clicked.connect(self.buildCustomTripleStoreDialog)
        self.loadUnicornLayers()

    def setFilterFromText(self):
        self.proxyModel.setFilterRegExp(self.filterConcepts.text())

    ## 
    #  @brief Creates a What To Enrich dialog with parameters given.
    #  
    #  @param self The object pointer
    def buildLoadGraphDialog(self):	
        self.searchTripleStoreDialog = LoadGraphDialog(self.triplestoreconf,self.maindlg,self)	
        self.searchTripleStoreDialog.setWindowTitle("Load Graph")	
        self.searchTripleStoreDialog.exec_()

    ## 
    #  @brief Creates a What To Enrich dialog with parameters given.
    #  
    #  @param self The object pointer
    def buildCustomTripleStoreDialog(self):	
        self.searchTripleStoreDialog = TripleStoreDialog(self.triplestoreconf,self.comboBox)	
        self.searchTripleStoreDialog.setMinimumSize(700, 500)
        self.searchTripleStoreDialog.setWindowTitle("Configure Own Triple Store")	
        self.searchTripleStoreDialog.exec_()

    ## 
    #  @brief Creates a What To Enrich dialog with parameters given.
    #  
    #  @param self The object pointer
    def createWhatToEnrich(self):
        if self.enrichTable.rowCount()==0:
            return
        layers = QgsProject.instance().layerTreeRoot().children()
        selectedLayerIndex = self.chooseLayerEnrich.currentIndex()
        layer = layers[selectedLayerIndex].layer()
        self.searchTripleStoreDialog = EnrichmentDialog(self.triplestoreconf,self.prefixes,self.enrichTable,layer,None,None)	
        self.searchTripleStoreDialog.setMinimumSize(700, 500)
        self.searchTripleStoreDialog.setWindowTitle("Enrichment Search")	
        self.searchTripleStoreDialog.exec_()

    def check_state3(self):
        self.searchTripleStoreDialog.check_state(self.interlinkNameSpace)

    def createEnrichSearchDialog(self,row=-1,column=-1):
        if column==1:
            self.buildSearchDialog(row,column,False,self.enrichTable,False,False,None,self.addVocabConf)
        if column==6:
            self.buildSearchDialog(row,column,False,self.enrichTable,False,False,None,self.addVocabConf)

    def createEnrichSearchDialogProp(self,row=-1,column=-1):
        self.buildSearchDialog(row,column,False,self.findIDPropertyEdit,True,False,None,self.addVocabConf)

    ## 
    #  @brief Creates a search dialog with parameters for interlinking.
    #  
    #  @param self The object pointer
    #  @param row The row of the table for which to map the search result
    #  @param column The column of the table for which to map the search result
    def createInterlinkSearchDialog(self, row=-1, column=-1):
        if column>3 and column<7:
            self.buildSearchDialog(row,column,True,self.interlinkTable,True,False,None,self.addVocabConf)
        elif column>=7:
            layers = QgsProject.instance().layerTreeRoot().children()
            selectedLayerIndex = self.chooseLayerInterlink.currentIndex()
            layer = layers[selectedLayerIndex].layer()
            self.buildValueMappingDialog(row,column,True,self.interlinkTable,layer)
        elif column==-1:
            self.buildSearchDialog(row,column,-1,self.interlinkOwlClassInput,False,False,None,self.addVocabConf)
    
    ## 
    #  @brief Shows the configuration table after creating an enrichment result.
    #  
    #  @param  self The object pointer
    #  
    def showConfigTable(self):
        self.enrichTableResult.hide()
        self.enrichTable.show()
        self.startEnrichment.setText("Start Enrichment")
        self.startEnrichment.clicked.disconnect()
        self.startEnrichment.clicked.connect(self.enrichtab.enrichLayerProcess)
        
    ## 
    #  @brief Executes a GUI event when a new SPARQL endpoint is selected. 
    #  Usually loads the list of concepts related to the SPARQL endpoint
    #  @param  send The sender of the request
    # 
    def viewselectaction(self):
        endpointIndex = self.comboBox.currentIndex()
        if endpointIndex==0:
            self.justloadingfromfile=False
            return
        concept=""
        curindex=self.proxyModel.mapToSource(self.geoClassList.selectionModel().currentIndex())
        if self.geoClassList.selectionModel().currentIndex()!=None and self.geoClassListModel.itemFromIndex(curindex)!=None and re.match(r'.*Q[0-9]+.*',self.geoClassListModel.itemFromIndex(curindex).text()) and not self.geoClassListModel.itemFromIndex(curindex).text().startswith("http"):
            self.inp_label.setText(self.geoClassListModel.itemFromIndex(curindex).text().split("(")[0].lower().replace(" ","_"))
            concept="Q"+self.geoClassListModel.itemFromIndex(curindex).text().split("Q")[1].replace(")","")
        elif self.geoClassListModel.itemFromIndex(curindex)!=None:
            concept=self.geoClassListModel.itemFromIndex(curindex).data(1)
        if "querytemplate" in self.triplestoreconf[endpointIndex]:
            if "wd:Q%%concept%% ." in self.triplestoreconf[endpointIndex]["querytemplate"][self.queryTemplates.currentIndex()]["query"]:
                querytext=""
                if concept!=None and concept.startswith("http"):
                    querytext=self.triplestoreconf[endpointIndex]["querytemplate"][self.queryTemplates.currentIndex()]["query"].replace("wd:Q%%concept%% .", "wd:"+concept[concept.rfind('/')+1:]+" .")
                elif concept!=None:
                    querytext=self.triplestoreconf[endpointIndex]["querytemplate"][self.queryTemplates.currentIndex()]["query"].replace("wd:Q%%concept%% .", "wd:"+concept+" .")
            else:
                querytext=self.triplestoreconf[endpointIndex]["querytemplate"][self.queryTemplates.currentIndex()]["query"].replace("%%concept%%",concept)
            if self.queryLimit.text().isnumeric() and querytext.rfind("LIMIT")!=-1:
               querytext=querytext[0:querytext.rfind("LIMIT")]+"LIMIT "+self.queryLimit.text()
            self.inp_sparql2.setPlainText(querytext)
            self.inp_sparql2.columnvars={}
        if self.geoClassList.selectionModel().currentIndex()!=None and self.geoClassListModel.itemFromIndex(curindex)!=None and "#" in self.geoClassListModel.itemFromIndex(curindex).text():
            self.inp_label.setText(self.geoClassListModel.itemFromIndex(curindex).text()[self.geoClassListModel.itemFromIndex(curindex).text().rfind('#')+1:].lower().replace(" ","_"))
        elif self.geoClassList.selectionModel().currentIndex()!=None and self.geoClassListModel.itemFromIndex(curindex)!=None:
            self.inp_label.setText(self.geoClassListModel.itemFromIndex(curindex).text()[self.geoClassListModel.itemFromIndex(curindex).text().rfind('/')+1:].lower().replace(" ","_"))

    ## 
    #  @brief Deletes a row from the table in the enrichment dialog.
    #  
    #  @param  send The sender of the request
    # 
    def deleteEnrichRow(send):
        w = send.sender().parent()
        row = self.enrichTable.indexAt(w.pos()).row()
        self.enrichTable.removeRow(row);
        self.enrichTable.setCurrentCell(0, 0)
  
    ## 
    #  @brief Adds a new row to the table in the enrichment dialog.
    #  
    #  @param  self The object pointer
    # 
    def addEnrichRow(self):
        layers = QgsProject.instance().layerTreeRoot().children()
        selectedLayerIndex = self.chooseLayerEnrich.currentIndex()
        layer = layers[selectedLayerIndex].layer()
        self.enrichTableResult.hide()
        fieldnames = [field.name() for field in layer.fields()]
        item=QTableWidgetItem("new_column")
        #item.setFlags(QtCore.Qt.ItemIsEnabled)
        row = self.enrichTable.rowCount() 
        self.enrichTable.insertRow(row)
        self.enrichTable.setItem(row,0,item)
        cbox=QComboBox()
        cbox.addItem("Get Remote")
        cbox.addItem("No Enrichment")
        cbox.addItem("Exclude")
        self.enrichTable.setCellWidget(row,3,cbox)
        cbox=QComboBox()	
        cbox.addItem("Enrich Value")	
        cbox.addItem("Enrich URI")	
        cbox.addItem("Enrich Both")	
        self.enrichTable.setCellWidget(row,4,cbox)
        cbox=QComboBox()
        for fieldd in fieldnames:
            cbox.addItem(fieldd)	
        self.enrichTable.setCellWidget(row,5,cbox)
        itemm=QTableWidgetItem("http://www.w3.org/2000/01/rdf-schema#label")
        self.enrichTable.setItem(row,6,itemm) 
        itemm=QTableWidgetItem("")
        self.enrichTable.setItem(row,7,itemm)
        itemm=QTableWidgetItem("")
        self.enrichTable.setItem(row,8,itemm)

    ## Validates the SPARQL query in the input field and outputs errors in a label.
    #  @param self The object pointer.
    def validateSPARQL(self):
        try:
            prepareQuery("".join(self.prefixes[self.comboBox.currentIndex()])+"\n"+self.inp_sparql2.toPlainText())
            self.errorLabel.setText("Valid Query")
            self.errorline=-1
            self.sparqlhighlight.errorhighlightline=self.errorline
            self.sparqlhighlight.currentline=0
        except Exception as e:
            self.errorLabel.setText(str(e))
            if "line" in str(e):
                ex=str(e)
                start = ex.find('line:') + 5
                end = ex.find(',', start)
                start2 = ex.find('col:') + 4
                end2 = ex.find(')', start2)
                self.errorline=ex[start:end]
                self.sparqlhighlight.errorhighlightcol=ex[start2:end2]
                self.sparqlhighlight.errorhighlightline=self.errorline
                self.sparqlhighlight.currentline=0
                #msgBox=QMessageBox()
                #msgBox.setText(str(self.errorline)+" "+str(self.sparqlhighlight.errorhighlightline)+" "+str(self.sparqlhighlight.errorhighlightcol))
                #msgBox.exec()

    ## 
    #  @brief Builds the search dialog to search for a concept or class.
    #  @param  self The object pointer
    #  @param  row the row to insert the result
    #  @param  column the column to insert the result
    #  @param  interlinkOrEnrich indicates if the dialog is meant for interlinking or enrichment
    #  @param  table the GUI element to display the result 
    def buildSearchDialog(self,row,column,interlinkOrEnrich,table,propOrClass,bothOptions=False,currentprefixes=None,addVocabConf=None):
        self.currentcol=column
        self.currentrow=row
        self.interlinkdialog = SearchDialog(column,row,self.triplestoreconf,self.prefixes,interlinkOrEnrich,table,propOrClass,bothOptions,currentprefixes,addVocabConf)
        self.interlinkdialog.setMinimumSize(650, 400)
        self.interlinkdialog.setWindowTitle("Search Interlink Concept")
        self.interlinkdialog.exec_()

    ## 
    #  @brief Builds a boundingbox dialog allows to pick a bounding box for a SPARQL query.
    #  
    #  @param self The object pointer
    def getPointFromCanvas(self):
        self.d=BBOXDialog(self.inp_sparql2,self.triplestoreconf,self.comboBox.currentIndex())
        self.d.setWindowTitle("Choose BoundingBox")
        self.d.exec_()

    ## 
    #  @brief Builds a value mapping dialog window for ther interlinking dialog.
    #  
    #  @param self The object pointer
    #  @param row The row of the table for which to map the value
    #  @param column The column of the table for which to map the value
    #  @param table The table in which to save the value mapping result
    #  @param layer The layer which is concerned by the enrichment oder interlinking
    def buildValueMappingDialog(self,row,column,interlinkOrEnrich,table,layer):
        self.currentcol=column
        self.currentrow=row
        valuemap=None
        if table.item(row, column)!=None and table.item(row, column).text()!="":
           valuemap=table.item(row, column).data(1)
        self.interlinkdialog =ValueMappingDialog(column,row,self.triplestoreconf,interlinkOrEnrich,table,table.item(row, 3).text(),layer,valuemap)
        self.interlinkdialog.setMinimumSize(650, 400)
        self.interlinkdialog.setWindowTitle("Get Value Mappings for column "+table.item(row, 3).text())
        self.interlinkdialog.exec_()

    ## 
    #  @brief Loads a QGIS layer for interlinking into the interlinking dialog.
    #  
    #  @param self The object pointer
    def loadLayerForInterlink(self):
        layers = QgsProject.instance().layerTreeRoot().children()
        selectedLayerIndex = self.chooseLayerInterlink.currentIndex()
        if len(layers)==0:
           return
        layer = layers[selectedLayerIndex].layer()
        fieldnames = [field.name() for field in layer.fields()]
        while self.interlinkTable.rowCount() > 0:
            self.interlinkTable.removeRow(0);
        row=0
        self.interlinkTable.setHorizontalHeaderLabels(["Export?","IDColumn?","GeoColumn?","Column","ColumnProperty","PropertyType","ColumnConcept","ValueConcepts"])
        self.interlinkTable.setColumnCount(8)
        for field in fieldnames:
            item=QTableWidgetItem(field)
            item.setFlags(QtCore.Qt.ItemIsEnabled)
            item2=QTableWidgetItem()
            item2.setCheckState(True)
            item3=QTableWidgetItem()
            item3.setCheckState(False)
            item4=QTableWidgetItem()
            item4.setCheckState(False)
            self.interlinkTable.insertRow(row)
            self.interlinkTable.setItem(row,3,item)
            self.interlinkTable.setItem(row,0,item2)
            self.interlinkTable.setItem(row,1,item3)
            self.interlinkTable.setItem(row,2,item4)
            cbox=QComboBox()
            cbox.addItem("Automatic")
            cbox.addItem("AnnotationProperty")
            cbox.addItem("DataProperty")
            cbox.addItem("ObjectProperty")
            cbox.addItem("SubClass")
            self.interlinkTable.setCellWidget(row,5,cbox)
            currentRowCount = self.interlinkTable.rowCount() 
            row+=1

    ## 
    #  @brief Loads a QGIS layer for enrichment into the enrichment dialog.
    #  
    #  @param self The object pointer
    def loadLayerForEnrichment(self):
        layers = QgsProject.instance().layerTreeRoot().children()
        selectedLayerIndex = self.chooseLayerEnrich.currentIndex()
        if len(layers)==0:
           return
        layer = layers[selectedLayerIndex].layer()
        self.enrichTableResult.hide()
        while self.enrichTableResult.rowCount() > 0:
            self.enrichTableResult.removeRow(0);
        self.enrichTable.show()
        self.addEnrichedLayerRowButton.setEnabled(True)
        fieldnames = [field.name() for field in layer.fields()]
        while self.enrichTable.rowCount() > 0:
            self.enrichTable.removeRow(0);
        row=0
        self.enrichTable.setColumnCount(9)
        self.enrichTable.setHorizontalHeaderLabels(["Column","EnrichmentConcept","TripleStore","Strategy","content","ID Column","ID Property","ID Domain","Language"])
        for field in fieldnames:
            item=QTableWidgetItem(field)
            item.setFlags(QtCore.Qt.ItemIsEnabled)
            currentRowCount = self.enrichTable.rowCount() 
            self.enrichTable.insertRow(row)
            self.enrichTable.setItem(row,0,item)
            cbox=QComboBox()
            cbox.addItem("No Enrichment")
            cbox.addItem("Keep Local")
            cbox.addItem("Keep Remote")
            cbox.addItem("Replace Local")
            cbox.addItem("Merge")
            cbox.addItem("Ask User")
            cbox.addItem("Exclude")
            self.enrichTable.setCellWidget(row,3,cbox)
            cbox=QComboBox()	
            cbox.addItem("Enrich Value")	
            cbox.addItem("Enrich URI")	
            cbox.addItem("Enrich Both")	
            self.enrichTable.setCellWidget(row,4,cbox)
            cbox=QComboBox()
            for fieldd in fieldnames:
                cbox.addItem(fieldd)	
            self.enrichTable.setCellWidget(row,5,cbox)
            itemm=QTableWidgetItem("http://www.w3.org/2000/01/rdf-schema#label")
            self.enrichTable.setItem(row,6,itemm)
            itemm=QTableWidgetItem("")
            self.enrichTable.setItem(row,7,itemm)
            itemm=QTableWidgetItem("")
            self.enrichTable.setItem(row,8,itemm)
            celllayout= QHBoxLayout()
            upbutton=QPushButton("Up")
            removebutton=QPushButton("Remove",self)
            removebutton.clicked.connect(self.deleteEnrichRow)
            downbutton=QPushButton("Down")
            celllayout.addWidget(upbutton)
            celllayout.addWidget(downbutton)
            celllayout.addWidget(removebutton)
            w = QWidget()
            w.setLayout(celllayout)
            optitem=QTableWidgetItem()
            #self.enrichTable.setCellWidget(row,4,w)
            #self.enrichTable.setItem(row,3,cbox)
            row+=1
        self.originalRowCount=row

    ## Fetch the currently loaded layers.
    #  @param self The object pointer.
    def loadUnicornLayers(self):
        layers = QgsProject.instance().layerTreeRoot().children()
        # Populate the comboBox with names of all the loaded unicorn layers
        self.loadedLayers.clear()
        self.chooseLayerInterlink.clear()
        self.chooseLayerEnrich.clear()
        for layer in layers:
            ucl = layer.name()
            #if type(layer) == QgsMapLayer.VectorLayer:
            self.loadedLayers.addItem(layer.name())
            self.chooseLayerInterlink.addItem(layer.name())
            self.chooseLayerEnrich.addItem(layer.name())    
