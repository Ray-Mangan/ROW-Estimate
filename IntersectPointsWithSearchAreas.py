def getMsgs(startMsg):
    msgCnt = arcpy.GetMessageCount()
    msg=arcpy.GetMessage(msgCnt-1)
    arcpy.AddMessage("{} {}".format(startMsg,msg))

inPnts = arcpy.GetParameterAsText(0)
inParcels = arcpy.GetParameterAsText(1)
namePrefix = arcpy.GetParameterAsText(2)

desc = arcpy.Describe(inPnts)
if len(desc.FIDset) > 0:
	arcpy.AddError("{} has a selection set. Please clear selections".format(inPnts))
	sys.exit(0)

# select points in polygons
arcpy.management.SelectLayerByLocation(inPnts, "INTERSECT", inParcels, None, "NEW_SELECTION", "NOT_INVERT")
getMsgs("Selected {} in {}".format(inPnts, inParcels))
desc = arcpy.Describe(inPnts)
outSelectedPnts = None
if len(desc.FIDset) > 0:	
	result = arcpy.CopyFeatures_management(inPnts,"in_memory\\{}_PointsInParcels".format(namePrefix))
	outSelectedPnts = result.getOutput(0)
	getMsgs("Copied selected features from {} to {}".format(inPnts, outSelectedPnts))	

# select points not in polygons
outSelectedNotPnts = None
arcpy.management.SelectLayerByLocation(inPnts, "INTERSECT", inParcels, None, "NEW_SELECTION", "INVERT")
desc = arcpy.Describe(inPnts)
if len(desc.FIDset) > 0:	
	result = arcpy.CopyFeatures_management(inPnts,"in_memory\\{}_Points_Not_In_Parcels".format(namePrefix))
	outSelectedNotPnts = result.getOutput(0)
	getMsgs("Copied selected features from {} to {}".format(inPnts, outSelectedPnts))	

if outSelectedPnts != None:
	arcpy.SetParameter(3, outSelectedPnts)

if outSelectedNotPnts != None:
	arcpy.SetParameter(4, outSelectedNotPnts)