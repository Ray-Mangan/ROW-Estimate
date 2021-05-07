from time import perf_counter

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
nameSuffix = arcpy.GetParameterAsText(1)
moveDistance = int(arcpy.GetParameterAsText(2))

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
     
### Calculate distance between parcels that have an RCL between them
# 1. Iterate the list of nearParcelPoints 
# 2. Read the angle created by the Near tool
# 3. Calc an opposite angle
# 4. Create another point at the distance from our original near point

# list for output dataset
pointsOppositeNearParcelPoint = []

## operation timing lists
pntAngDist = []

# 1. Iterate the list of nearParcelPoints
t2_start = perf_counter()
for p in nearParcelPoints:
    # Read the angle and calc opposite angle 
    revAngle = p[2] + 180 if p[2] < 0 else p[2] - 180

    try:
        distance = p[7]  + moveDistance
            
        # Create another point at the distance from our original near point
        oppositePointGeom = None
        try:
            # performance test
            t1 = perf_counter()
            oppositePointGeom = p[0].pointFromAngleAndDistance(revAngle, distance, "PLANAR")
            t2 = perf_counter()
            pntAngDist.append(t2-t1)
        except:
            e1=sys.exc_info()[1]
            arcpy.AddWarning("Error creating an oppositePoint from OID {}: {}".format(p[5],e1))
            arcpy.AddWarning("SEGMENTID = {} revAngle = {} distance = {}".format(p[6], revAngle, distance))

        if oppositePointGeom: 
            pointsOppositeNearParcelPoint.append([(oppositePointGeom.firstPoint.X,oppositePointGeom.firstPoint.Y),p[1].firstPoint.X,p[1].firstPoint.Y,p[5],p[6],distance])
                    
    except:
        e=sys.exc_info()[1]
        arcpy.AddWarning("An error occurred while creating an opposite point from a near parcel point: {}".format(e.args[0]))
            
t2_stop = perf_counter()
arcpy.AddMessage("Time to generate list of pointsOppositeNearParcelPoints: {}".format(t2_stop - t2_start))

# performance testing summary
arcpy.AddMessage("Operation,Average,Max,Sum,Total Observations")
performanceReport(pntAngDist, "pointAngleAndDistance")

### End

# Create oppositePoints feature class & add fields
# 1. Create oppositePoints feature class & add fields
result = arcpy.management.CreateFeatureclass("in_memory","{}_Pnt_Opposite_Near_Prcl_Pnts".format(nameSuffix),"POINT",spatial_reference=spaRef)
oppPntFc = result.getOutput(0)
getMsgs("Created {}".format(oppPntFc))

flds = [['NEAR_X','DOUBLE'],['NEAR_Y','DOUBLE'],['NEAR_FID', 'LONG'],['SEGMENTID', 'LONG'],['NEAR_DIST', 'DOUBLE']]
arcpy.management.AddFields(oppPntFc, flds)
getMsgs("Added fields to {}".format(oppPntFc))

# 2. Insert data into oppositePoints
fields=['SHAPE@XY','NEAR_X','NEAR_Y','NEAR_FID','SEGMENTID','NEAR_DIST']
t4_start = perf_counter()
cursor1 = arcpy.da.InsertCursor(oppPntFc,fields)
try:
    for row in pointsOppositeNearParcelPoint:
        cursor1.insertRow(row)
        
except: 
    e = sys.exc_info()[1]
    arcpy.AddError("Error when inserting rows into {}: {}".format(oppPntFc, e.args[0]))
    sys.exit(0)
finally:
    del cursor1
    t4_stop = perf_counter()
    arcpy.AddMessage("Time to insert data into {}: {}".format(oppPntFc, t4_stop - t4_start))

# Derived Parameter 
arcpy.SetParameter(3,oppPntFc)
