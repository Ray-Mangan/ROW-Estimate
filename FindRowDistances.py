from time import perf_counter

### FindRowDistances
# Creates output datasets (points, polylines and a table) that determine conceptual ROW distances between parcels and RCLs
###

### Constants
# Starting distance to move a point when it does not within a parcel
MOVE_DIST_START = 5
# Number of times to try to move the point
MOVE_ATTEMPTS = 6
### End constants

def performanceReport(times,category):
    num = len(times)
    avg = sum(times) / num
    slowest = max(times)
    total = sum(times)
    arcpy.AddMessage("{},{},{},{},{}".format(category, avg, slowest, total, num))

def getMsgs(startMsg):
    msgCnt = arcpy.GetMessageCount()
    msg=arcpy.GetMessage(msgCnt-1)
    arcpy.AddMessage("{} {}".format(startMsg,msg))

### Find angles and distances between the points created by 2 NEAR tool executions
# 1. Loop through Distance ROW Points
# 2. Create an arcpy.point from the XY created by the 2nd run of NEAR, then create a PointGeometry
# 3. Get angle and distance between the ROW point and PointGeometry & store in list

# Get all params
in_distanceRowPnts = arcpy.GetParameterAsText(0)
in_dissolveParcels = arcpy.GetParameterAsText(1)

# NEAR_X_PARCEL AND NEAR_Y_PARCEL are the locations of the points on the parcels that are nearest to the distance row points
# NEAR_FID is the fid of the RCL feature
#fields=['SHAPE@','NEAR_X_PARCEL','NEAR_Y_PARCEL','NEAR_FID','OID@']
fields=['SHAPE@','NEAR_X_PARCEL','NEAR_Y_PARCEL','NEAR_FID','OID@','SEGMENTID']
nearParcelPoints = []
spaRef = arcpy.SpatialReference()
hawaii3 = "PROJCS['NAD_1983_HARN_StatePlane_Hawaii_3_FIPS_5103_Feet',GEOGCS['GCS_North_American_1983_HARN',DATUM['D_North_American_1983_HARN',SPHEROID['GRS_1980',6378137.0,298.257222101]],PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]],PROJECTION['Transverse_Mercator'],PARAMETER['False_Easting',1640416.666666667],PARAMETER['False_Northing',0.0],PARAMETER['Central_Meridian',-158.0],PARAMETER['Scale_Factor',0.99999],PARAMETER['Latitude_Of_Origin',21.16666666666667],UNIT['Foot_US',0.3048006096012192]];-16807900 -40496900 3048.00609601219;-100000 10000;-100000 10000;3.28083333333333E-03;0.001;0.001;IsHighPrecision"
spaRef.loadFromString(hawaii3)

# 1. Loop through Distance ROW Points
t1_start = perf_counter()
with arcpy.da.SearchCursor(in_distanceRowPnts, fields) as cursor:
    for row in cursor:
        # 2. Create an arcpy.point from the XY created by the 2nd run of NEAR, then create a PointGeometry
        nearParcelPoint = arcpy.Point(row[1],row[2])
        nearParcelPointGeom = arcpy.PointGeometry(nearParcelPoint,spaRef)

        # 3. Get angle and distance between the ROW point and PointGeometry & store in list
        angleDist = row[0].angleAndDistanceTo(nearParcelPointGeom,"PLANAR")
        nearParcelPoints.append([row[0],nearParcelPointGeom,angleDist[0],angleDist[1],row[3],row[4],row[5]])

t1_stop = perf_counter()
arcpy.AddMessage("{} query + fetch time: {}".format(in_distanceRowPnts,t1_stop-t1_start))

### End Find angles and distances between the points created by 2 NEAR tool executions

### Create data to support distance calcs below
# 1. Dissolve the parcels into 1 large geometry to make point in polygon and intersect operations faster
# 2. Read the summary table to get near a distance per rcl segment to the parcels (This will be 1 side of the street and it won't be the max distance)
# 3. Add the distance value to the points in nearParcelPoints so we know, at a minimun, how far out to generate a point

# 1. Dissolve the parcels into 1 large geometry to make point in polygon and intersect operations faster
result = arcpy.management.Dissolve(in_dissolveParcels,"in_memory\\dissolvedPars")
disLyr = result.getOutput(0)
getMsgs("Dissolved {} into {}".format(in_dissolveParcels,disLyr))
dissolved = []
for row in arcpy.da.SearchCursor(disLyr, ["SHAPE@"]):
    dissolved.append(row[0])
    
if len(dissolved) != 1:
    arcpy.AddError("Dissolve produced empty output or created too many features")
    sys.exit(0)

# 2. Read the summary table to get near a distance per rcl segment to the parcels (This will be 1 side of the street and it won't be the max distance)
maxDistancesRCLtoParcel = []
# Create a summary table from the input parcels layer
result = arcpy.analysis.Statistics(in_dissolveParcels, "in_memory\\Near_Parcel_Stats", "NEAR_DIST MAX", "NEAR_FID")
nearParcelStats = result.getOutput(0)
getMsgs("Summary Stats {} to {}".format(in_dissolveParcels,nearParcelStats))
                 
# cache the near fid values into a list
for row in arcpy.da.SearchCursor(nearParcelStats,["NEAR_FID","MAX_NEAR_DIST"]):
    maxDistancesRCLtoParcel.append([row[0],row[1]])
    
if len(maxDistancesRCLtoParcel) < 1:
    arcpy.AddError("No maximum distances found in the summary table")
    sys.exit(0)

# 3. Add the distance value to the points in nearParcelPoints so we know, at a minimun, how far out to generate a point
t1a_start = perf_counter()
for p in nearParcelPoints:
    rclOid = p[4]
    for d in maxDistancesRCLtoParcel:
        if rclOid == d[0]:
            p.append(d[1])
            break

t1a_stop = perf_counter()
arcpy.AddMessage("Time to match nearParcelPoints to distance from RCL (double loop): {}".format(t1a_stop - t1a_stop))

### End create data to support distance calcs below
       
### Calculate distance between parcels that have an RCL between them
# 1. Iterate the list of nearParcelPoints 
# 2. Read the angle created by the Near tool
# 3. Calc an opposite angle
# 4. Create another point at the distance from our original near point
# 5. Test if that point is within a parcel - try up to MOVE_ATTEMPTS times
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

    # 5. Test if that point is within a parcel, making up to MOVE_ATTEMPS tries to locate this point w/in a parcel
    pntInPoly = False
    for x in range(MOVE_ATTEMPTS):
        try:
            distance = p[7] if x==0 else p[7] + (x * MOVE_DIST_START)        
            
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
                #arcpy.AddWarning("NEAR_FID = {} revAngle = {} distance = {}".format(p[4], revAngle, distance))
                arcpy.AddWarning("SEGMENTID = {} revAngle = {} distance = {}".format(p[6], revAngle, distance))

            # performance test
            t1 = perf_counter()
            if oppositePointGeom and oppositePointGeom.within(dissolved[0]):
                t2 = perf_counter()
                within.append(t2-t1)
                
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
                    interSectionPointGeom = polylineGeom.intersect(dissolved[0],1)
                    t2 = perf_counter()
                    intersect.append(t2-t1)
                    
                    if interSectionPointGeom:
                        # 8. Calc distance between intersection point and nearParcelPointGeom

                        # performance test
                        t1 = perf_counter()
                        dist = interSectionPointGeom.distanceTo(p[1])
                        t2 = perf_counter()
                        distanceTo.append(t2-t1)
                        
                        #distancesPerRCL.append([p[4],p[5],dist])
                        distancesPerRCL.append([p[6],p[5],dist])

                        # cache the intersection points - these will later be inserted into an output fc
                        intersectPnts.append([(interSectionPointGeom.firstPoint.X,interSectionPointGeom.firstPoint.Y),p[3],p[4],distance])

                        # generate another polyline - these will later be inserted into an output fc
                        pntConnectArray = arcpy.Array([p[1].firstPoint, interSectionPointGeom.firstPoint])

                        # performance test
                        t1 = perf_counter()
                        connectionLine = arcpy.Polyline(pntConnectArray, spaRef)
                        t2 = perf_counter()
                        newPolyLine2.append(t2-t1)
                        
                        connections.append([connectionLine,p[3],p[4]])
                        
                        pntInPoly = True
                        break
            else:                
                if oppositePointGeom and x == (MOVE_ATTEMPTS-1):
                    if pntInPoly == False:
                        missing = [(oppositePointGeom.firstPoint.X,oppositePointGeom.firstPoint.Y),p[4],p[5],distance]
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
result = arcpy.CreateTable_management("in_memory","ROW_all")
tbl = result.getOutput(0)
getMsgs("Create table {}".format(tbl))

rowDistFlds = [['SEGMENTID', 'LONG'], ['NEAR_PNT_FID', 'LONG'], ['ROW_DISTANCE', 'DOUBLE']]
arcpy.management.AddFields(tbl,rowDistFlds)
getMsgs("Added fields to {}".format(tbl))

#rowDistFlds = ['RCL_FID','NEAR_PNT_FID','ROW_DISTANCE']
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


# 2. Summarize by RCL FID to get max, min and avg ROW distance
result = arcpy.analysis.Statistics(tbl, "in_memory\\ROWSummary", "ROW_DISTANCE MAX;ROW_DISTANCE MIN;ROW_DISTANCE MEAN", "SEGMENTID")
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
result = arcpy.management.CreateFeatureclass("in_memory","oppositePoints","POINT",spatial_reference=spaRef)
oppPntFc = result.getOutput(0)
getMsgs("Created {}".format(oppPntFc))

#flds = [['NEAR_PNT_FID', 'LONG'],['RCL_FID', 'LONG'],['ROW_DISTANCE', 'DOUBLE']]
flds = [['NEAR_PNT_FID', 'LONG'],['SEGMENTID', 'LONG'],['ROW_DISTANCE', 'DOUBLE']]
arcpy.management.AddFields(oppPntFc, flds)
getMsgs("Added fields to {}".format(oppPntFc))

# 2. Insert data into oppositePoints
t4_start = perf_counter()
cursor1 = arcpy.da.InsertCursor(oppPntFc,['SHAPE@XY','NEAR_PNT_FID','SEGMENTID','ROW_DISTANCE'])
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
result = arcpy.management.CreateFeatureclass("in_memory","connectionLines","POLYLINE",spatial_reference=spaRef)
connectorFc = result.getOutput(0)
getMsgs("Created {}".format(connectorFc))

#flds = [['NEAR_PNT_FID', 'LONG'],['RCL_FID', 'LONG']]
flds = [['NEAR_PNT_FID', 'LONG'],['SEGMENTID', 'LONG']]
arcpy.management.AddFields(connectorFc, flds)
getMsgs("Added fields to {}".format(connectorFc))

# 4. Insert data into connector lines
t5_start = perf_counter()
#cursor = arcpy.da.InsertCursor(connectorFc,['SHAPE@','NEAR_PNT_FID','RCL_FID'])
cursor = arcpy.da.InsertCursor(connectorFc,['SHAPE@','NEAR_PNT_FID','SEGMENTID'])
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
    result = arcpy.management.CreateFeatureclass("in_memory","missingPoints","POINT",spatial_reference=spaRef)
    missingPntsFc = result.getOutput(0)
    getMsgs("Created {}".format(missingPntsFc))

    #flds = [["RCL_FID","LONG"],["NEAR_PNT_FID","LONG"],["FinalSearchDistance","DOUBLE"]]
    flds = [["SEGMENTID","LONG"],["NEAR_PNT_FID","LONG"],["FinalSearchDistance","DOUBLE"]]
    arcpy.management.AddFields(missingPntsFc, flds)
    getMsgs("Added fields to {}".format(missingPntsFc))

    # 6. Insert data into missing points
    t6_start = perf_counter()
    #cursor = arcpy.da.InsertCursor(missingPntsFc,['SHAPE@XY','RCL_FID','NEAR_PNT_FID','FinalSearchDistance'])
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

# performance testing summary

arcpy.AddMessage("Operation,Average,Max,Sum,Total Observations")
performanceReport(pntAngDist, "pointAngleAndDistance")
performanceReport(within, "within")
performanceReport(newPolyLine, "new polyline")
performanceReport(intersect, "intersect")
performanceReport(distanceTo, "distanceTo")
performanceReport(newPolyLine2, "new polyline2")
