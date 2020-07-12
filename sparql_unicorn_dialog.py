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

from qgis.PyQt import uic
from qgis.PyQt import QtWidgets
from qgis.core import QgsProject
from qgis.PyQt.QtWidgets import QComboBox
from rdflib.plugins.sparql import prepareQuery
from .whattoenrich import EnrichmentDialog
from .tooltipplaintext import ToolTipPlainText
from .triplestoredialog import TripleStoreDialog
from .searchdialog import SearchDialog
from .sparqlhighlighter import SPARQLHighlighter
from .valuemapping import ValueMappingDialog
from .bboxdialog import BBOXDialog

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'sparql_unicorn_dialog_base.ui'))


class SPAQLunicornDialog(QtWidgets.QDialog, FORM_CLASS):
	
    triplestoreconf=None
	
    prefixes=None
	
    columnvars={}
	
    def __init__(self,triplestoreconf={},prefixes=[],parent=None):
        """Constructor."""
        super(SPAQLunicornDialog, self).__init__(parent)
        # Set up the user interface from Designer through FORM_CLASS.
        # After self.setupUi() you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        self.prefixes=prefixes
        self.triplestoreconf=triplestoreconf
        self.searchTripleStoreDialog=TripleStoreDialog(self.triplestoreconf,self.comboBox)
        self.layerconcepts.clear()
        self.layerconcepts.setEditable(True)
        self.layerconcepts.setInsertPolicy(QComboBox.NoInsert)
        self.inp_sparql2=ToolTipPlainText(self.tab,self.triplestoreconf,self.comboBox,self.columnvars,self.prefixes)
        self.inp_sparql2.move(10,130)
        self.inp_sparql2.setMinimumSize(1071,401)
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

    def buildCustomTripleStoreDialog(self):	
        self.searchTripleStoreDialog = TripleStoreDialog(self.triplestoreconf,self.comboBox)	
        self.searchTripleStoreDialog.setMinimumSize(700, 500)
        self.searchTripleStoreDialog.setWindowTitle("Configure Own Triple Store")	
        self.searchTripleStoreDialog.exec_()
		
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
		
    def createEnrichSearchDialog(self,row=-1,column=-1):
        if column==1:
            self.buildSearchDialog(row,column,False,self.enrichTable,False,False,None,self.addVocabConf)
        if column==6:
            self.buildSearchDialog(row,column,False,self.enrichTable,False,False,None,self.addVocabConf)

    def createEnrichSearchDialogProp(self,row=-1,column=-1):
        self.buildSearchDialog(row,column,False,self.findIDPropertyEdit,True,False,None,self.addVocabConf)

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
    #  @param [in] self The object pointer
    #  
    def showConfigTable(self):
        self.enrichTableResult.hide()
        self.enrichTable.show()
        self.startEnrichment.setText("Start Enrichment")
        self.startEnrichment.clicked.disconnect()
        self.startEnrichment.clicked.connect(self.enrichLayerProcess)


    ## Selects a SPARQL endpoint and changes its configuration accordingly.
    #  @param self The object pointer.
    def endpointselectaction(self):
        endpointIndex = self.comboBox.currentIndex()
        self.queryTemplates.clear()
        print("changing endpoint")
        conceptlist=[]
        self.layerconcepts.clear()
        if "endpoint" in self.triplestoreconf[endpointIndex] and self.triplestoreconf[endpointIndex]["endpoint"]!="" and (not "staticconcepts" in self.triplestoreconf[endpointIndex] or "staticconcepts" in self.triplestoreconf[endpointIndex] and self.triplestoreconf[endpointIndex]["staticconcepts"]==[]) and "geoconceptquery" in self.triplestoreconf[endpointIndex] and self.triplestoreconf[endpointIndex]["geoconceptquery"]!="":
            conceptlist=self.getGeoConcepts(self.triplestoreconf[endpointIndex]["endpoint"],self.triplestoreconf[endpointIndex]["geoconceptquery"],"class",None,True)
        elif "staticconcepts" in self.triplestoreconf[endpointIndex] and self.triplestoreconf[endpointIndex]["staticconcepts"]!=[]:
            conceptlist=self.triplestoreconf[endpointIndex]["staticconcepts"]
        for concept in conceptlist:
            self.layerconcepts.addItem(concept)
        comp=QCompleter(self.layerconcepts)
        comp.setCompletionMode(QCompleter.PopupCompletion)
        comp.setModel(self.layerconcepts.model())
        self.layerconcepts.setCompleter(comp)
        if "areaconcepts" in self.triplestoreconf[endpointIndex] and self.triplestoreconf[endpointIndex]["areaconcepts"]:
            conceptlist2=self.triplestoreconf[endpointIndex]["areaconcepts"]
            for concept in conceptlist2:
                 self.areaconcepts.addItem(concept["concept"])
        if "querytemplate" in self.triplestoreconf[endpointIndex]:
            for concept in self.triplestoreconf[endpointIndex]["querytemplate"]:
                 self.queryTemplates.addItem(concept["label"])
        if "examplequery" in self.triplestoreconf[endpointIndex]:
            self.inp_sparql2.setPlainText(self.triplestoreconf[endpointIndex]["examplequery"]) 
            self.inp_sparql2.columnvars={}

    def viewselectaction(self):
        endpointIndex = self.comboBox.currentIndex()
        if endpointIndex==0:
            self.justloadingfromfile=False
            return
        if self.layerconcepts.currentText()!=None and "(Q" in self.layerconcepts.currentText():
            self.inp_label.setText(self.layerconcepts.currentText().split("(")[0].lower().replace(" ","_"))
            concept=self.layerconcepts.currentText().split("Q")[1].replace(")","")
        else:
            concept=self.layerconcepts.currentText()
        if "querytemplate" in self.triplestoreconf[endpointIndex]:
            self.inp_sparql2.setPlainText(self.triplestoreconf[endpointIndex]["querytemplate"][self.queryTemplates.currentIndex()]["query"].replace("%%concept%%",concept))
            self.inp_sparql2.columnvars={}
            if "wd:Q ." in self.inp_sparql2.toPlainText():
                self.inp_sparql2.setPlainText(self.inp_sparql2.toPlainText().replace("wd:Q .", "wd:Q1248784 ."))
        if "#" in self.layerconcepts.currentText():
            self.inp_label.setText(self.layerconcepts.currentText()[self.layerconcepts.currentText().rfind('#')+1:].lower().replace(" ","_"))
        else:
            self.inp_label.setText(self.layerconcepts.currentText()[self.layerconcepts.currentText().rfind('/')+1:].lower().replace(" ","_"))




    def addnewEnrichRow(self):
        currentRowCount = self.enrichTable.rowCount() 
        self.enrichTable.insertRow(currentRowCount)
        
    def moveRow(self,upOrDown):
        if self.enrichTable.selectionModel().hasSelected():
            currentRowCount = self.enrichTable.selectedRows() 

    def deleteEnrichRow(send):
        w = send.sender().parent()
        row = self.enrichTable.indexAt(w.pos()).row()
        self.enrichTable.removeRow(row);
        self.enrichTable.setCurrentCell(0, 0)
        
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
    #  @param [in] self The object pointer
    #  @param [in] row the row to insert the result
    #  @param [in] column the column to insert the result
    #  @param [in] interlinkOrEnrich indicates if the dialog is meant for interlinking or enrichment
    #  @param [in] table the GUI element to display the result 
    def buildSearchDialog(self,row,column,interlinkOrEnrich,table,propOrClass,bothOptions=False,currentprefixes=None,addVocabConf=None):
        self.currentcol=column
        self.currentrow=row
        self.interlinkdialog = SearchDialog(column,row,self.triplestoreconf,self.prefixes,interlinkOrEnrich,table,propOrClass,bothOptions,currentprefixes,addVocabConf)
        self.interlinkdialog.setMinimumSize(650, 400)
        self.interlinkdialog.setWindowTitle("Search Interlink Concept")
        self.interlinkdialog.exec_()

    def getPointFromCanvas(self):
        self.d=BBOXDialog(self.inp_sparql2,self.triplestoreconf,self.comboBox.currentIndex())
        self.d.setWindowTitle("Choose BoundingBox")
        self.d.exec_()

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
