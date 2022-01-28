from qgis.PyQt.QtWidgets import QApplication, QMenu, QAction, QFileDialog
from qgis.PyQt.QtGui import QDesktopServices
from qgis.core import (
    QgsApplication, QgsMessageLog
)
from qgis.PyQt.QtCore import QUrl

from ...tasks.querylayertask import QueryLayerTask
from ...tasks.findrelatedgeoconcept import FindRelatedGeoConceptQueryTask
from ..instancedatadialog import InstanceDataDialog
from ...tasks.subclassquerytask import SubClassQueryTask
from ...tasks.instanceamountquerytask import InstanceAmountQueryTask
from ...tasks.instancelistquerytask import InstanceListQueryTask
from ..dataschemadialog import DataSchemaDialog
from ..querylimitedinstancesdialog import QueryLimitedInstancesDialog
from ...util.sparqlutils import SPARQLUtils

MESSAGE_CATEGORY = 'ContextMenu'

class ConceptContextMenu(QMenu):

    def __init__(self,dlg,triplestoreconf,prefixes,position,context,item,preferredlang=None,menu=None):
        super(ConceptContextMenu, self).__init__()
        self.triplestoreconf=triplestoreconf
        self.dlg=dlg
        self.preferredlang=preferredlang
        self.item=item
        self.prefixes=prefixes
        if menu==None:
            menu = QMenu("Menu", context)
        actionclip = QAction("Copy IRI to clipboard")
        if item.data(257) == SPARQLUtils.instancenode or item.data(257) == SPARQLUtils.geoinstancenode:
            actionclip.setIcon(SPARQLUtils.instancelinkicon)
        elif item.data(257) == SPARQLUtils.classnode or item.data(257) == SPARQLUtils.geoclassnode:
            actionclip.setIcon(SPARQLUtils.classlinkicon)
        elif item.data(257) == SPARQLUtils.linkedgeoclassnode:
            actionclip.setIcon(SPARQLUtils.linkedgeoclassicon)
        menu.addAction(actionclip)
        actionclip.triggered.connect(lambda: ConceptContextMenu.copyClipBoard(item))
        action = QAction("Open in Webbrowser")
        action.setIcon(SPARQLUtils.geoclassicon)
        menu.addAction(action)
        action.triggered.connect(lambda: QDesktopServices.openUrl(QUrl(item.data(256))))
        if item.data(257) != SPARQLUtils.instancenode and item.data(257) != SPARQLUtils.geoinstancenode:
            actioninstancecount = QAction("Check instance count")
            actioninstancecount.setIcon(SPARQLUtils.countinstancesicon)
            menu.addAction(actioninstancecount)
            actioninstancecount.triggered.connect(self.instanceCount)
            actiondataschema = QAction("Query data schema")
            if item.data(257) == SPARQLUtils.classnode:
                actiondataschema.setIcon(SPARQLUtils.classschemaicon)
                actionrelgeo = QAction("Check related geo concepts")
                actionrelgeo.setIcon(SPARQLUtils.countinstancesicon)
                menu.addAction(actionrelgeo)
                actionrelgeo.triggered.connect(self.relatedGeoConcepts)
            else:
                actiondataschema.setIcon(SPARQLUtils.geoclassschemaicon)
            menu.addAction(actiondataschema)
            actiondataschema.triggered.connect(lambda: DataSchemaDialog(
                item.data(256),
                item.data(257),
                item.text(),
                triplestoreconf["endpoint"],
                triplestoreconf, self.prefixes,
                "Data Schema View for " + SPARQLUtils.labelFromURI(str(item.data(256)),
                                                                   triplestoreconf[
                                                                       "prefixesrev"])
            ).exec_())
            actionqueryinstances = QAction("Query all instances")
            menu.addAction(actionqueryinstances)
            actionqueryinstances.triggered.connect(self.instanceList)
            if "subclassquery" in triplestoreconf:
                action2 = QAction("Load subclasses")
                menu.addAction(action2)
                action2.triggered.connect(self.loadSubClasses)
            actionsubclassquery = QAction("Create subclass query")
            actionsubclassquery.setIcon(SPARQLUtils.subclassicon)
            menu.addAction(actionsubclassquery)
            actionsubclassquery.triggered.connect(self.dlg.subclassQuerySelectAction)
            actionquerysomeinstances = QAction("Add some instances as new layer")
            actionquerysomeinstances.setIcon(SPARQLUtils.addfeaturecollectionicon)
            menu.addAction(actionquerysomeinstances)
            actionquerysomeinstances.triggered.connect(lambda: QueryLimitedInstancesDialog(
                triplestoreconf,
                item.data(256),
                item.data(257)
            ).exec_())
            actionaddallInstancesAsLayer = QAction("Add all instances as new layer")
            actionaddallInstancesAsLayer.setIcon(SPARQLUtils.addfeaturecollectionicon)
            menu.addAction(actionaddallInstancesAsLayer)
            actionaddallInstancesAsLayer.triggered.connect(self.dlg.dataAllInstancesAsLayer)
        else:
            actiondataschema = QAction("Query data")
            if item.data(257) == SPARQLUtils.instancenode:
                actiondataschema.setIcon(SPARQLUtils.instanceicon)
            elif item.data(257) == SPARQLUtils.geoinstancenode:
                actiondataschema.setIcon(SPARQLUtils.geoinstanceicon)
            menu.addAction(actiondataschema)
            actiondataschema.triggered.connect(self.dataInstanceView)
            actionaddInstanceAsLayer = QAction("Add instance as new layer")
            if item.data(257) == SPARQLUtils.instancenode:
                actionaddInstanceAsLayer.setIcon(SPARQLUtils.addinstanceicon)
            elif item.data(257) == SPARQLUtils.geoinstancenode:
                actionaddInstanceAsLayer.setIcon(SPARQLUtils.addgeoinstanceicon)
            menu.addAction(actionaddInstanceAsLayer)
            actionaddInstanceAsLayer.triggered.connect(self.dlg.dataInstanceAsLayer)
        if item.data(257) == SPARQLUtils.linkedgeoclassnode:
            actionquerylinkedgeoconcept = QAction("Query joined layer with linked geoconcept")
            actionquerylinkedgeoconcept.setIcon(SPARQLUtils.linkedgeoclassicon)
            menu.addAction(actionquerylinkedgeoconcept)
            actionquerylinkedgeoconcept.triggered.connect(self.queryLinkedGeoConcept)
        #actionapplicablestyles = QAction("Find applicable styles")
        #menu.addAction(actionapplicablestyles)
        #actionapplicablestyles.triggered.connect(self.appStyles)
        menu.exec_(context.viewport().mapToGlobal(position))

    @staticmethod
    def createListContextMenu(item,menu=None):
        if menu==None:
            menu = QMenu("Menu")
        actionclip = QAction("Copy IRI to clipboard")
        menu.addAction(actionclip)
        actionclip.triggered.connect(lambda: ConceptContextMenu.copyClipBoard(item))
        action = QAction("Open in Webbrowser")
        menu.addAction(action)
        action.triggered.connect(lambda: QDesktopServices.openUrl(QUrl(item.data(256))))
        return menu

    def appStyles(self):
        curindex = self.currentProxyModel.mapToSource(self.currentContext.selectionModel().currentIndex())
        concept = self.currentContextModel.itemFromIndex(curindex).data(256)
        label = self.currentContextModel.itemFromIndex(curindex).text()
        # self.dataschemaDialog = DataSchemaDialog(concept,label,self.triplestoreconf["endpoint"],self.triplestoreconf,self.prefixes,self.comboBox.currentIndex())
        # self.dataschemaDialog.setWindowTitle("Data Schema View for "+str(concept))
        # self.dataschemaDialog.exec_()

    def dataInstanceView(self):
        concept = self.item.data(256)
        nodetype = self.item.data(257)
        label = self.item.text()
        self.instancedataDialog = InstanceDataDialog(concept,nodetype,label,self.triplestoreconf["endpoint"],self.triplestoreconf,self.prefixes)
        self.instancedataDialog.setWindowTitle("Data Instance View for "+SPARQLUtils.labelFromURI(str(concept),self.triplestoreconf["prefixesrev"]))
        self.instancedataDialog.exec_()

    def queryLinkedGeoConcept(self):
        concept = self.item.data(256)
        nodetype = self.item.data(257)
        linkedproperty=self.data(260)
        label = self.item.text()
        self.qlayerinstance = QueryLayerTask(
            "Linked GeoClass to Layer: " + str(concept),
            concept,
            self.triplestoreconf[self.comboBox.currentIndex()]["endpoint"],
            "SELECT ?item ?item2 ?rel ?val ?rel2 ?val2 \n WHERE\n {\n BIND( <" + str(concept) + "> AS ?item)\n ?item ?rel ?val . ?item <"+str(linkedproperty)+"> ?item2 . ?item2 ?rel2 ?val2 . \n }",
            self.triplestoreconf[self.comboBox.currentIndex()], True, SPARQLUtils.labelFromURI(concept), None)


    def relatedGeoConcepts(self):
        concept = self.item.data(256)
        label = self.item.text()
        if not label.endswith("]"):
            self.qtaskinstance = FindRelatedGeoConceptQueryTask(
                "Getting related geo concepts for " + str(concept),
                self.triplestoreconf["endpoint"], self, concept,self.triplestoreconf)
            QgsApplication.taskManager().addTask(self.qtaskinstance)

    def instanceCount(self):
        concept = self.item.data(256)
        nodetype = self.item.data(257)
        label = self.item.text()
        if not label.endswith("]"):
            self.qtaskinstance = InstanceAmountQueryTask(
                "Getting instance count for " + str(concept),
                self.triplestoreconf["endpoint"], self, self.item,self.triplestoreconf,nodetype)
            QgsApplication.taskManager().addTask(self.qtaskinstance)

    def instanceList(self):
        concept = self.item.data(256)
        alreadyloadedindicator = self.item.data(259)
        if alreadyloadedindicator!=SPARQLUtils.instancesloadedindicator:
            self.qtaskinstanceList = InstanceListQueryTask(
                "Getting instance count for " + str(concept),
                self.triplestoreconf["endpoint"], self, self.item,self.triplestoreconf)
            QgsApplication.taskManager().addTask(self.qtaskinstanceList)

    def loadSubClasses(self):
        concept = self.item.data(256)
        if "subclassquery" in self.triplestoreconf:
            if "wikidata" in self.triplestoreconf["endpoint"]:
                query=self.triplestoreconf["subclassquery"].replace("%%concept%%",str("wd:" + concept[concept.find('(')+1:-1]))
            else:
                query=self.triplestoreconf["subclassquery"].replace("%%concept%%","<"+str(concept)+">")
            prefixestoadd=""
            for endpoint in self.triplestoreconf["prefixes"]:
                    prefixestoadd += "PREFIX " + endpoint + ": <" + self.triplestoreconf["prefixes"][endpoint] + "> \n"
            self.qtasksub = SubClassQueryTask("Querying subclasses of " + self.triplestoreconf["endpoint"],
                                    self.triplestoreconf["endpoint"],
                                    prefixestoadd + query,None,self,
                                    self.item,concept,self.triplestoreconf)
            QgsApplication.taskManager().addTask(self.qtasksub)

    @staticmethod
    def copyClipBoard(item):
        concept = item.data(256)
        cb = QApplication.clipboard()
        cb.clear(mode=cb.Clipboard)
        cb.setText(concept, mode=cb.Clipboard)