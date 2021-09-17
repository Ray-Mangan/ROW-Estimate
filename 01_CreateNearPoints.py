def getMsgs(startMsg):
    msgCnt = arcpy.GetMessageCount()
    msg=arcpy.GetMessage(msgCnt-1)
    arcpy.AddMessage("{} {}".format(startMsg,msg))

in_RCLs = arcpy.GetParameterAsText(0)
in_parcels = arcpy.GetParameterAsText(1)
out_genPnts = arcpy.GetParameterAsText(2)
out_clippedParcels = arcpy.GetParameterAsText(3)
pnt_Dist = arcpy.GetParameterAsText(4)

# only process RCLs greater than pnt_Dist length
where = "Shape_Length > {}".format(pnt_Dist)
result=arcpy.management.MakeFeatureLayer(in_RCLs,"RCLLayer",where)
distanceLayer = result.getOutput(0)
getMsgs("Created feature layer {} from {} {}".format(distanceLayer, in_RCLs, where))

# Generate points along the RCLs at pnt_Dist set to a linear unit
pntDistLU = "{} FEET".format(pnt_Dist)
arcpy.management.GeneratePointsAlongLines(distanceLayer, out_genPnts, "DISTANCE", pntDistLU, None, None)
getMsgs("Generate Points along {} at {} increments".format(in_RCLs, pnt_Dist))

# Run near between the generated points and the parcels - this will create near information in the points
arcpy.analysis.Near(out_genPnts, in_parcels, None, "LOCATION", "NO_ANGLE", "PLANAR", "NEAR_FID NEAR_FID;NEAR_DIST NEAR_DIST;NEAR_X NEAR_X;NEAR_Y NEAR_Y")
getMsgs("Generate Near information in {} from {}".format(out_genPnts,in_parcels))

## Buffer the RCLs by 200' each side
result = arcpy.analysis.Buffer(in_RCLs, "in_memory\\bufferedRCLs", "200 Feet", "FULL", "ROUND", "ALL", None, "PLANAR")
bufferedRCLs = result.getOutput(0)
getMsgs("Buffered {} by 200 feet to create {}".format(in_RCLs,bufferedRCLs))
        
## clip the parcels by bufferedRCLs
result = arcpy.analysis.Clip(in_parcels, bufferedRCLs, out_clippedParcels, None)
getMsgs("Clipped {} using {} to create {}".format(in_parcels, bufferedRCLs, out_clippedParcels))

arcpy.SetParameter(2,out_genPnts)
arcpy.SetParameter(3,out_clippedParcels)
