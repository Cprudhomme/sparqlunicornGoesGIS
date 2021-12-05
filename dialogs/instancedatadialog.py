
from qgis.PyQt.QtWidgets import QDialog, QLabel,QHeaderView, QLineEdit, QPushButton, QTableWidget, QComboBox, QMessageBox, QRadioButton, QTableWidgetItem, QProgressDialog
from qgis.PyQt.QtCore import QRegExp, Qt, QSettings,QUrl
from qgis.PyQt.QtGui import QDesktopServices
from qgis.PyQt import uic
from qgis.core import Qgis
from ..tasks.instancequerytask import InstanceQueryTask
from ..tasks.querylayertask import QueryLayerTask
from ..util.sparqlutils import SPARQLUtils
import os.path
from qgis.core import (
    QgsApplication, QgsTask, QgsMessageLog,
)


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui/instancedatadialog.ui'))

# Class representing a search dialog which may be used to search for concepts or properties.


class InstanceDataDialog(QDialog, FORM_CLASS):

    ##
    #  @brief Initializes the search dialog
    #
    #  @param self The object pointer
    #  @param column The column of the GUI widget which called this dialog, if any
    #  @param row The row of the GUI widget which called this dialog, if any
    #  @param triplestoreconf The triple store configuration of the plugin
    #  @param prefixes A list of prefixes known to the plugin
    #  @param interlinkOrEnrich indicates whether this dialog was called from an enrichment or interlinking dialog
    #  @param table The GUI element ot return the result to
    #  @param propOrClass indicates whether a class or a property can be searched
    #  @param bothOptions indicates whether both a class or property may be searched
    #  @param currentprefixes Description for currentprefixes
    #  @param addVocab Description for addVocab
    #  @return Return description
    #
    #  @details More details
    #
    def __init__(self, concept,label,triplestoreurl,triplestoreconf,prefixes,curindex):
        super(QDialog, self).__init__()
        self.setupUi(self)
        self.concept=concept
        self.label=label
        self.prefixes=prefixes
        self.alreadyloadedSample=[]
        self.triplestoreconf=triplestoreconf
        self.triplestoreurl=triplestoreurl
        self.curindex=curindex
        self.queryInstanceLayerButton.clicked.connect(self.queryInstance)
        self.instanceDataNameLabel.setText(str(label)+" (<a href=\""+str(concept)+"\">"+SPARQLUtils.labelFromURI(str(concept),self.triplestoreconf[self.curindex]["prefixesrev"])+"</a>)")
        header =self.instanceDataTableView.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        self.instanceDataTableView.setHorizontalHeaderLabels(["Attribute", "Value"])
        self.instanceDataTableView.insertRow(0)
        item = QTableWidgetItem()
        item.setText("Loading...")
        self.instanceDataTableView.setItem(0,0,item)
        self.instanceDataTableView.setMouseTracking(True)
        self.instanceDataTableView.cellEntered.connect(self.showURI)
        self.instanceDataTableView.cellDoubleClicked.connect(self.openURL)
        self.okButton.clicked.connect(self.close)
        QgsMessageLog.logMessage('Started task "{}"'.format(self.triplestoreconf[self.curindex]), "InstanceDataDialog", Qgis.Info)
        self.getAttributes(self.concept,triplestoreurl)


    def queryInstance(self):
        querydepth = self.graphQueryDepthBox.value()
        if int(querydepth)>1:
            query=SPARQLUtils.expandRelValToAmount("SELECT ?" + " ?".join(self.triplestoreconf[self.curindex][
                                       "mandatoryvariables"]) + " ?rel ?val\n WHERE\n {\n BIND( <" + str(
                self.concept) + "> AS ?item)\n" +
            self.triplestoreconf[self.curindex]["geotriplepattern"][0] + "\n ?item ?rel ?val . }",querydepth)
            self.qlayerinstance = QueryLayerTask(
            "Instance to Layer: " + str(self.concept),
            self.triplestoreconf[self.curindex]["endpoint"],query,
            self.triplestoreconf[self.curindex], False, SPARQLUtils.labelFromURI(self.concept), None)
        else:
            self.qlayerinstance = QueryLayerTask(
            "Instance to Layer: " + str(self.concept),
            self.triplestoreconf[self.curindex]["endpoint"],
            "SELECT ?" + " ?".join(self.triplestoreconf[self.curindex][
                                       "mandatoryvariables"]) + " ?rel ?val\n WHERE\n {\n BIND( <" + str(
                self.concept) + "> AS ?item)\n ?item ?rel ?val . " +
            self.triplestoreconf[self.curindex]["geotriplepattern"][0] + "\n }",
            self.triplestoreconf[self.curindex], False, SPARQLUtils.labelFromURI(self.concept), None)
        QgsApplication.taskManager().addTask(self.qlayerinstance)

    def openURL(self,row,column):
        if self.instanceDataTableView.item(row,column)!=None:
            concept=str(self.instanceDataTableView.item(row,column).data(256))
            if concept.startswith("http"):
                url = QUrl(concept)
                QDesktopServices.openUrl(url)

    def showURI(self,row,column):
        if self.instanceDataTableView.item(row,column)!=None:
            concept=str(self.instanceDataTableView.item(row,column).data(256))
            if concept.startswith("http"):
                self.statusBarLabel.setText(concept)

    ##
    #  @brief Gives statistics about most commonly occuring properties from a certain class in a given triple store.
    #  
    #  @param [in] self The object pointer
    #  @return A list of properties with their occurance given in percent
    def getAttributes(self, concept="wd:Q3914", endpoint_url="https://query.wikidata.org/sparql"):
        QgsMessageLog.logMessage('Started task "{}"'.format(self.triplestoreconf[self.curindex]), "InstanceDataDialog", Qgis.Info)
        QgsMessageLog.logMessage('Started task "{}"'.format(str(self.curindex)+ " "+str(self.triplestoreconf[self.curindex]["endpoint"])), "DataSchemaDialog",
                                 Qgis.Info)
        QgsMessageLog.logMessage('Started task "{}"'.format(self.triplestoreconf[self.curindex]["whattoenrichquery"]), "DataSchemaDialog",
                                 Qgis.Info)
        if self.concept == "" or self.concept is None or "whattoenrichquery" not in self.triplestoreconf[self.curindex]:
            return
        concept = "<" + self.concept + ">"
        self.qtask = InstanceQueryTask("Querying dataset schema.... (" + self.label + ")",
                                           self.triplestoreurl,
                                           self.concept,
                                           self.triplestoreconf[self.curindex],
                                           self.instanceDataTableView)
        QgsApplication.taskManager().addTask(self.qtask)