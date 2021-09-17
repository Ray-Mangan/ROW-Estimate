from time import perf_counter

def getMsgs(startMsg):
    msgCnt = arcpy.GetMessageCount()
    msg=arcpy.GetMessage(msgCnt-1)
    arcpy.AddMessage("{} {}".format(startMsg,msg))

def makeFc(fcPathName, fieldsList, fcGeomType,spatialRef):
    result = arcpy.management.CreateFeatureclass("in_memory",fcPathName,fcGeomType,spatial_reference=spatialRef)
    featureCls = result.getOutput(0)
    getMsgs("Created {}".format(featureCls))

    arcpy.management.AddFields(featureCls, fieldsList)
    getMsgs("Added fields to {}".format(featureCls))

    return featureCls

def insertData(fcPathName, fldsList):
    t5_start = perf_counter()
    cursor = arcpy.da.InsertCursor(fcPathName,fldsList)
    try:
        for row in connectionLines:
            cursor.insertRow(row)
            
    except: 
        e = sys.exc_info()[1]
        arcpy.AddError(e.args[0])
        sys.exit(0)
    finally:
        del cursor
        t5_stop = perf_counter()
        arcpy.AddMessage("Time to insert data into {}: {}".format(fcPathName, t5_stop - t5_start))


inPnts = arcpy.GetParameterAsText(0)
inParcels = arcpy.GetParameterAsText(1)
namePrefix = arcpy.GetParameterAsText(2)

##dissolve the parcels 
dissolved = []
result = arcpy.management.Dissolve(inParcels,"in_memory\\{}_dissolvedPars".format(namePrefix))
disLyr = result.getOutput(0)
getMsgs("Dissolved {} into {}".format(inParcels,disLyr))

## connection lines
fields=['SHAPE@','NEAR_X','NEAR_Y','NEAR_FID','OID@','SEGMENTID','NEAR_DIST']
spaRef = arcpy.SpatialReference()
hawaii3 = "PROJCS['NAD_1983_HARN_StatePlane_Hawaii_3_FIPS_5103_Feet',GEOGCS['GCS_North_American_1983_HARN',DATUM['D_North_American_1983_HARN',SPHEROID['GRS_1980',6378137.0,298.257222101]],PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]],PROJECTION['Transverse_Mercator'],PARAMETER['False_Easting',1640416.666666667],PARAMETER['False_Northing',0.0],PARAMETER['Central_Meridian',-158.0],PARAMETER['Scale_Factor',0.99999],PARAMETER['Latitude_Of_Origin',21.16666666666667],UNIT['Foot_US',0.3048006096012192]];-16807900 -40496900 3048.00609601219;-100000 10000;-100000 10000;3.28083333333333E-03;0.001;0.001;IsHighPrecision"
spaRef.loadFromString(hawaii3)

connectionLines = []

# Loop through input points
t1_start = perf_counter()
with arcpy.da.SearchCursor(inPnts, fields) as cursor:
    for row in cursor:

        # Create an arcpy.point from the XY created by NEAR, then create a PointGeometry
        nearParcelPoint = arcpy.Point(row[1],row[2])
        nearParcelPointGeom = arcpy.PointGeometry(nearParcelPoint,spaRef)

        # Create a polyline between the two points
        pntArray = arcpy.Array([row[0].firstPoint, nearParcelPointGeom.firstPoint])
        polylineGeom = arcpy.Polyline(pntArray, spaRef)
        connectionLines.append([polylineGeom,row[4],row[5],row[1],row[2]])

t1_stop = perf_counter()
arcpy.AddMessage("Time to {} query + create polylines: {}".format(inPnts,t1_stop-t1_start))

if len(connectionLines) < 1:
	arcpy.AddWarning("No polylines created from {}".format(inPnts))
	sys.exit(0)

# Create connector lines feature class & add fields
connectorFcName = "{}_firstConnectionLines".format(namePrefix)
flds = [['ORIG_PNT_FID', 'LONG'],['SEGMENTID', 'LONG'],['NEAR_X','DOUBLE'],['NEAR_Y','DOUBLE']]
connectorFc = makeFc(connectorFcName, flds, "POLYLINE",spaRef)

# 4. Insert data into connector lines
insertData(connectorFc, ['SHAPE@','ORIG_PNT_FID','SEGMENTID','NEAR_X','NEAR_Y'])

# intersect with the dissolved parcels 
intersectLyrs = [connectorFc,disLyr] #r"Bin_4_connectionLines #;'Bin 4\bin_4_rcl_SearchAreas' #"
outIntersectPnts = "in_memory\\{}_Connection_Points".format(namePrefix)
result = arcpy.analysis.Intersect(intersectLyrs, outIntersectPnts, "ALL", None, "POINT")
pntsFromIntersect = result.getOutput(0)
getMsgs("Intersection of {} and {} created {}".format(connectorFc,disLyr,pntsFromIntersect))

## create new connection lines from  pntsFromIntersect
connectionLines = []
t1_start = perf_counter()
fields=['SHAPE@','SEGMENTID','OID@']
with arcpy.da.SearchCursor(pntsFromIntersect, fields) as cursor:
    for row in cursor:
        try:
            if row[0].type.lower()=="multipoint" and row[0].pointCount > 1:
                pnt1 = row[0].firstPoint
                pnt2 = row[0].lastPoint
                pntArray = arcpy.Array([pnt1, pnt2])
                polylineGeom = arcpy.Polyline(pntArray, spaRef)
                connectionLines.append([polylineGeom,row[1],0 if row[0].pointCount == 2 else 1])
            else:
                arcpy.AddWarning("Point {}: type is {} ; has {} geometries".format(row[2],row[0].type,row[0].pointCount))

        except: 
            e = sys.exc_info()[1]
            arcpy.AddError(e.args[0])
            sys.exit(0)

t1_stop = perf_counter()
arcpy.AddMessage("Time to query {}  + create polylines list: {}".format(pntsFromIntersect,t1_stop-t1_start))

if len(connectionLines) < 1:
	arcpy.AddWarning("No polylines created from {}".format(pntsFromIntersect))
	sys.exit(0)

# Create the final connector Featureclass
connectorFcName = "{}_Final_Connection_Lines".format(namePrefix)
flds = [['SEGMENTID', 'LONG'],['REVIEW','SHORT']]
connectorFc = makeFc(connectorFcName, flds, "POLYLINE",spaRef)

# re-insert into connectorFc
insertData(connectorFc,['SHAPE@','SEGMENTID','REVIEW'])

arcpy.SetParameter(3, connectorFc)
arcpy.SetParameter(4, pntsFromIntersect)
