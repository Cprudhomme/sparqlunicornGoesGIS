# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SpaLOD
                                 A QGIS plugin
 Fork of SPARQLunicorn
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                             -------------------
        begin                : 2022-02-02
        copyright            : (C) 2022 by HAFSAOUI A, PONCIANO C , PONCIANO JJ
        email                : antoinehafsaoui@gmail.com
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load SpaLOD class from file SpaLOD.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .spalod import SpaLOD
    return SpaLOD(iface)
