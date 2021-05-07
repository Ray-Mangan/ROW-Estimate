def getMsgs(startMsg):
    msgCnt = arcpy.GetMessageCount()
    msg=arcpy.GetMessage(msgCnt-1)
    arcpy.AddMessage("{} {}".format(startMsg,msg))

in_RCLs = arcpy.GetParameterAsText(0)
in_parcels = arcpy.GetParameterAsText(1)
namePrefix = arcpy.GetParameterAsText(2)
pnt_Dist = arcpy.GetParameterAsText(3)

# only process RCLs greater than pnt_Dist length
where = "Shape_Length > {}".format(pnt_Dist)
result=arcpy.management.MakeFeatureLayer(in_RCLs,"RCLLayer",where)
distanceLayer = result.getOutput(0)
getMsgs("Created feature layer {} from {} {}".format(distanceLayer, in_RCLs, where))

# Generate points along the RCLs at pnt_Dist set to a linear unit
pntDistLU = "{} FEET".format(pnt_Dist)
out_genPnts = "in_memory\\{}_Near_Points".format(namePrefix)
arcpy.management.GeneratePointsAlongLines(distanceLayer, out_genPnts, "DISTANCE", pntDistLU, None, None)
getMsgs("Generate Points along {} at {} increments".format(in_RCLs, pnt_Dist))

# Run near between the generated points and the parcels - this will create near information in the points
arcpy.analysis.Near(out_genPnts, in_parcels, None, "LOCATION", "NO_ANGLE", "PLANAR", "NEAR_FID NEAR_FID;NEAR_DIST NEAR_DIST;NEAR_X NEAR_X;NEAR_Y NEAR_Y")
getMsgs("Generate Near information in {} from {}".format(out_genPnts,in_parcels))
        
arcpy.SetParameter(4,out_genPnts)

