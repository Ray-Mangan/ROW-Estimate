from time import perf_counter

### FindRowDistances
# Creates output datasets (points, polylines and a table) that determine conceptual ROW distances between parcels and RCLs
###

### Constants
# Starting distance to move a point when it does not within a parcel
MOVE_DIST_START = 5
### End constants

def performanceReport(times,category):
    try:
        num = len(times)
        avg = sum(times) / num       
        slowest = max(times)
        total = sum(times)
        arcpy.AddMessage("{},{},{},{},{}".format(category, avg, slowest, total, num))
    except:
        e1=sys.exc_info()[1]
        arcpy.AddWarning("An error occurred while creating the performance report for category {}: {}".format(category,e1))
        

def getMsgs(startMsg):
    msgCnt = arcpy.GetMessageCount()
    msg=arcpy.GetMessage(msgCnt-1)
    arcpy.AddMessage("{} {}".format(startMsg,msg))

### Find angles and distances between the points created by NEAR tool 
# 1. Loop through Distance ROW Points
# 2. Create an arcpy.point from the XY created by NEAR, then create a PointGeometry
# 3. Get angle and distance between the ROW point and PointGeometry & store in list

# Get all params
in_distanceRowPnts = arcpy.GetParameterAsText(0)
in_dissolveParcels = arcpy.GetParameterAsText(1)
nameSuffix = arcpy.GetParameterAsText(6)
searchAttempts = int(arcpy.GetParameterAsText(8))

fields=['SHAPE@','NEAR_X','NEAR_Y','NEAR_FID','OID@','SEGMENTID','NEAR_DIST']
nearParcelPoints = []
spaRef = arcpy.SpatialReference()
hawaii3 = "PROJCS['NAD_1983_HARN_StatePlane_Hawaii_3_FIPS_5103_Feet',GEOGCS['GCS_North_American_1983_HARN',DATUM['D_North_American_1983_HARN',SPHEROID['GRS_1980',6378137.0,298.257222101]],PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]],PROJECTION['Transverse_Mercator'],PARAMETER['False_Easting',1640416.666666667],PARAMETER['False_Northing',0.0],PARAMETER['Central_Meridian',-158.0],PARAMETER['Scale_Factor',0.99999],PARAMETER['Latitude_Of_Origin',21.16666666666667],UNIT['Foot_US',0.3048006096012192]];-16807900 -40496900 3048.00609601219;-100000 10000;-100000 10000;3.28083333333333E-03;0.001;0.001;IsHighPrecision"
spaRef.loadFromString(hawaii3)

# 1. Loop through Distance ROW Points
t1_start = perf_counter()
with arcpy.da.SearchCursor(in_distanceRowPnts, fields) as cursor:
    for row in cursor:
        # 2. Create an arcpy.point from the XY created by NEAR, then create a PointGeometry
        nearParcelPoint = arcpy.Point(row[1],row[2])
        nearParcelPointGeom = arcpy.PointGeometry(nearParcelPoint,spaRef)

        # 3. Get angle and distance between the ROW point and PointGeometry & store in list
        angleDist = row[0].angleAndDistanceTo(nearParcelPointGeom,"PLANAR")
        nearParcelPoints.append([row[0],nearParcelPointGeom,angleDist[0],angleDist[1],row[3],row[4],row[5],row[6]])

t1_stop = perf_counter()
arcpy.AddMessage("{} query + fetch time: {}".format(in_distanceRowPnts,t1_stop-t1_start))

### End Find angles and distances between the points gathered above

### Create data to support distance calcs below
# 1. Dissolve the parcels into 1 large geometry to make point in polygon operations faster

# 1. Dissolve the parcels into 1 large geometry to make point in polygon and intersect operations faster
## Performance test - count the number of parcels. If more than 2k, do not dissolve
dissolved = []
allParcels = []
t1a_start = perf_counter()
result = arcpy.management.Dissolve(in_dissolveParcels,"in_memory\\{}_dissolvedPars".format(nameSuffix))
disLyr = result.getOutput(0)
getMsgs("Dissolved {} into {}".format(in_dissolveParcels,disLyr))
errors = []
for row in arcpy.da.SearchCursor(disLyr, ["SHAPE@"]):
    try:
        dissolved.append(row[0])
    except:
        e=sys.exc_info()[1]
        errors.append(e)

arcpy.AddMessage("Number of items in {} = {}".format(disLyr,len(dissolved)))

if len(dissolved) < 1:
    arcpy.AddError("Dissolve created no output parcel features")
    sys.exit(0)

for row in arcpy.da.SearchCursor(in_dissolveParcels,["SHAPE@"]):
    allParcels.append(row[0])
               
t1a_stop = perf_counter()
arcpy.AddMessage("Number of items in {} = {}".format(in_dissolveParcels,len(allParcels)))
arcpy.AddMessage("Time to handle parcel dissolve and cache: {}".format(t1a_stop - t1a_start))

### End create data to support distance calcs below
       
### Calculate distance between parcels that have an RCL between them
# 1. Iterate the list of nearParcelPoints 
# 2. Read the angle created by the Near tool
# 3. Calc an opposite angle
# 4. Create another point at the distance from our original near point
# 5. Test if that point is within a parcel - try up to searchAttempts times
# 6. if point intersect parcel, create a line between point and the original near point
# 7. intersect line w/parcels + get output of intersection as point
# 8. Calc distance between intersection point and nearParcelPointGeom

## this is a list to store generated points that do not fall into a parcel 
pointsNotInParcels = []

## this List will be used to populate a table
distancesPerRCL = []

## Lists to hold computed points and connector lines
intersectPnts = []
connections = []

## operation timing lists
pntAngDist = []
within = []
newPolyLine = []
intersect = []
distanceTo = []
newPolyLine2 = []

# 1. Iterate the list of nearParcelPoints
t2_start = perf_counter()
for p in nearParcelPoints:
    # 2. + 3. Read the angle and calc opposite angle
    if p[2] < 0:
        revAngle = p[2] + 180
    else:
        revAngle = p[2] - 180

    # 5. Test if that point is within a parcel, making up to searchAttempts tries to locate this point w/in a parcel
    pntInPoly = False
    for x in range(searchAttempts):
        try:
            distance = p[7] if x==0 else p[7] + (x * MOVE_DIST_START)        
            ##arcpy.AddMessage("Distance value = {}".format(distance))
            
            # 4. Create another point at the distance from our original near point
            oppositePointGeom = None
            try:
                # performance test
                t1 = perf_counter()
                oppositePointGeom = p[0].pointFromAngleAndDistance(revAngle, distance, "PLANAR")
                t2 = perf_counter()
                pntAngDist.append(t2-t1)
            except:
                e1=sys.exc_info()[1]
                arcpy.AddWarning("Error creating an oppositePoint from OID {}".format(p[5]))
                arcpy.AddWarning("SEGMENTID = {} revAngle = {} distance = {}".format(p[6], revAngle, distance))

            if oppositePointGeom: ## and oppositePointGeom.within(dissolved[0]):
                # performance test
                t1 = perf_counter()
                polyIntersect = None
                    
                if len(allParcels) < 1001:                   
                    for poly in allParcels: 
                        if oppositePointGeom.within(poly):
                            polyIntersect = poly
                            break
                        
                else:
                    for poly in dissolved:
                        if oppositePointGeom.within(poly):
                            polyIntersect = poly
                            break
                                
                t2 = perf_counter()
                within.append(t2-t1)

                if polyIntersect:
                
                    # 6. create a line between oppositePointGeom and p[0] (the original near point)
                    pntArray = arcpy.Array([p[0].firstPoint, oppositePointGeom.firstPoint])

                    # performance test
                    t1 = perf_counter()
                    polylineGeom = arcpy.Polyline(pntArray, spaRef)
                    t2 = perf_counter()
                    newPolyLine.append(t2-t1)
                    
                    if polylineGeom:
                        # 7. intersect line w/parcels + get output of intersection as point

                        # performance test
                        t1 = perf_counter()
                        interSectionPointGeom = polylineGeom.intersect(polyIntersect,1)
                        t2 = perf_counter()
                        intersect.append(t2-t1)
                        
                        if interSectionPointGeom:
                            # 8. Calc distance between intersection point and nearParcelPointGeom

                            # performance test
                            t1 = perf_counter()
                            dist = interSectionPointGeom.distanceTo(p[1])
                            t2 = perf_counter()
                            distanceTo.append(t2-t1)
                            
                            distancesPerRCL.append([p[6],p[5],dist])

                            # cache the intersection points - these will later be inserted into an output fc
                            intersectPnts.append([(interSectionPointGeom.firstPoint.X,interSectionPointGeom.firstPoint.Y),p[5],p[6],distance])

                            # generate another polyline - these will later be inserted into an output fc
                            pntConnectArray = arcpy.Array([p[1].firstPoint, interSectionPointGeom.firstPoint])

                            # performance test
                            t1 = perf_counter()
                            connectionLine = arcpy.Polyline(pntConnectArray, spaRef)
                            t2 = perf_counter()
                            newPolyLine2.append(t2-t1)
                            
                            connections.append([connectionLine,p[5],p[6]])
                            
                            pntInPoly = True
                            break
                else:                
                    if oppositePointGeom and x == (searchAttempts-1):
                        if pntInPoly == False:
                            missing = [(oppositePointGeom.firstPoint.X,oppositePointGeom.firstPoint.Y),p[6],p[5],distance]
                            pointsNotInParcels.append(missing)
                    
        except:
            e=sys.exc_info()[1]
            arcpy.AddError(e.args[0])
            
t2_stop = perf_counter()
arcpy.AddMessage("Time to calc distance between parcels that have an RCL between them: {}".format(t2_stop - t2_start))

### End Calculate distance between parcels that have an RCL between them


### Summarize ROW distances
# 1. Write all distancesPerRCL values into a table
# 2. Summarize by RCL FID to get max, min and avg ROW distance

# 1. Write all distancesPerRCL values into a table
result = arcpy.CreateTable_management("in_memory","{}_ROW_all".format(nameSuffix))
tbl = result.getOutput(0)
getMsgs("Create table {}".format(tbl))

rowDistFlds = [['SEGMENTID', 'LONG'], ['NEAR_PNT_FID', 'LONG'], ['ROW_DISTANCE', 'DOUBLE']]
arcpy.management.AddFields(tbl,rowDistFlds)
getMsgs("Added fields to {}".format(tbl))

rowDistFlds = ['SEGMENTID','NEAR_PNT_FID','ROW_DISTANCE']
t3_start = perf_counter()
cursor = arcpy.da.InsertCursor(tbl,rowDistFlds)
try:
    for row in distancesPerRCL:
        cursor.insertRow(row)
        
except: 
    e = sys.exc_info()[1]
    arcpy.AddError(e.args[0])
    sys.exit(0)
finally:
    del cursor
    t3_stop = perf_counter()
    arcpy.AddMessage("Time to write all distancesPerRCL values into a table: {}".format(t3_stop - t3_start))


arcpy.SetParameter(7,tbl)


# 2. Summarize by RCL FID to get max, min and avg ROW distance
result = arcpy.analysis.Statistics(tbl, "in_memory\\{}_ROWSummary".format(nameSuffix), "ROW_DISTANCE MAX;ROW_DISTANCE MIN;ROW_DISTANCE MEAN", "SEGMENTID")
getMsgs("Summary Stats {} to {}".format(tbl, result.getOutput(0)))

arcpy.SetParameter(2, result.getOutput(0))

### End Summarize ROW distance

### Create Derivative datasets
# 1. Create oppositePoints feature class & add fields
# 2. Insert data into oppositePoints
# 3. Create connector lines feature class & add fields
# 4. Insert data into connector lines
# 5. Create missing points feature class & add fields
# 6. Insert data into missing points

# 1. Create oppositePoints feature class & add fields
result = arcpy.management.CreateFeatureclass("in_memory","{}_PointsCreatedByParcelIntersect".format(nameSuffix),"POINT",spatial_reference=spaRef)
oppPntFc = result.getOutput(0)
getMsgs("Created {}".format(oppPntFc))

flds = [['ORIG_PNT_FID', 'LONG'],['SEGMENTID', 'LONG'],['ROW_DISTANCE', 'DOUBLE']]
arcpy.management.AddFields(oppPntFc, flds)
getMsgs("Added fields to {}".format(oppPntFc))

# 2. Insert data into oppositePoints
t4_start = perf_counter()
cursor1 = arcpy.da.InsertCursor(oppPntFc,['SHAPE@XY','ORIG_PNT_FID','SEGMENTID','ROW_DISTANCE'])
try:
    for row in intersectPnts:
        cursor1.insertRow(row)
        
except: 
    e = sys.exc_info()[1]
    arcpy.AddError("Error when inserting oppositePoints = {}".format(e.args[0]))
    sys.exit(0)
finally:
    del cursor1
    t4_stop = perf_counter()
    arcpy.AddMessage("Time to insert data into oppositePoints: {}".format(t4_stop - t4_start))

# Derived Parameter 1
arcpy.SetParameter(3,oppPntFc)

# 3. Create connector lines feature class & add fields
result = arcpy.management.CreateFeatureclass("in_memory","{}_connectionLines".format(nameSuffix),"POLYLINE",spatial_reference=spaRef)
connectorFc = result.getOutput(0)
getMsgs("Created {}".format(connectorFc))

flds = [['ORIG_PNT_FID', 'LONG'],['SEGMENTID', 'LONG']]
arcpy.management.AddFields(connectorFc, flds)
getMsgs("Added fields to {}".format(connectorFc))

# 4. Insert data into connector lines
t5_start = perf_counter()
cursor = arcpy.da.InsertCursor(connectorFc,['SHAPE@','ORIG_PNT_FID','SEGMENTID'])
try:
    for row in connections:
        cursor.insertRow(row)
        
except: 
    e = sys.exc_info()[1]
    arcpy.AddError(e.args[0])
finally:
    del cursor
    t5_stop = perf_counter()
    arcpy.AddMessage("Time to insert data into connector lines: {}".format(t5_stop - t5_start))

# Derived parameter 2
arcpy.SetParameter(4,connectorFc)

# 5. Create missing points feature class & add fields
if len(pointsNotInParcels) > 0:
    result = arcpy.management.CreateFeatureclass("in_memory","{}_missingPoints".format(nameSuffix),"POINT",spatial_reference=spaRef)
    missingPntsFc = result.getOutput(0)
    getMsgs("Created {}".format(missingPntsFc))

    flds = [["SEGMENTID","LONG"],["NEAR_PNT_FID","LONG"],["FinalSearchDistance","DOUBLE"]]
    arcpy.management.AddFields(missingPntsFc, flds)
    getMsgs("Added fields to {}".format(missingPntsFc))

    # 6. Insert data into missing points
    t6_start = perf_counter()
    cursor = arcpy.da.InsertCursor(missingPntsFc,['SHAPE@XY','SEGMENTID','NEAR_PNT_FID','FinalSearchDistance'])
    try:
        for row in pointsNotInParcels:
            cursor.insertRow(row)
            
    except: 
        e = sys.exc_info()[1]
        arcpy.AddError(e.args[0])
    finally:
        del cursor
        t6_stop = perf_counter()
        arcpy.AddMessage("Time to insert data into missing points: {}".format(t6_stop - t6_start))

    # Derived Parameter 3
    arcpy.SetParameter(5, missingPntsFc)

else: arcpy.AddMessage("There are no missing points to process")

# performance testing summary

arcpy.AddMessage("Operation,Average,Max,Sum,Total Observations")
performanceReport(pntAngDist, "pointAngleAndDistance")
performanceReport(within, "within")
performanceReport(newPolyLine, "new polyline")
performanceReport(intersect, "intersect")
performanceReport(distanceTo, "distanceTo")
performanceReport(newPolyLine2, "new polyline2")
