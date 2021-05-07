in_parcels = arcpy.GetParameterAsText(0)
in_RCLs = arcpy.GetParameterAsText(1)
out_parcels = arcpy.GetParameterAsText(2)

# make a backup of our source parcels
result = arcpy.management.CopyFeatures(in_parcels,out_parcels)
arcpy.AddMessage("Copied {} to {}".format(in_parcels,out_parcels))
processingParcels = result.getOutput(0)
result = arcpy.management.MakeFeatureLayer(processingParcels,"ProcessingParcels")
procParcelLyr=result.getOutput(0)
arcpy.SetParameter(2,procParcelLyr)

# select parcels that are intersected by road centerlines
arcpy.management.SelectLayerByLocation(procParcelLyr, "INTERSECT", in_RCLs, None, "NEW_SELECTION", "NOT_INVERT")
desc = arcpy.Describe(procParcelLyr)
result = arcpy.management.GetCount(processingParcels)
cntAllPar = int(result.getOutput(0))
cnt = len(desc.FIDset.split(";"))
arcpy.AddMessage("{} parcels selected from {} total parcels".format(cnt,cntAllPar))

if cnt > 0 and cntAllPar > cnt:
    # copy out the selected parcels
    result = arcpy.management.CopyFeatures(procParcelLyr,"in_memory\\parcelsWithIntersectingRCLs")
    intersectedParcels = result.getOutput(0)
    arcpy.AddMessage("Copied {} selected parcels to {}".format(cnt,intersectedParcels))  
    arcpy.SetParameter(3,intersectedParcels)

    # verify we have the correct number of features
    result = arcpy.management.GetCount(intersectedParcels)
    intersectedParCnt = int(result.getOutput(0))
    if intersectedParCnt != cnt:
        arcpy.AddError("Number of selected parcels does not equal feature count in {}".format(intersectedParcels))
        sys.exit(0)

    # delete the intersecting parcels
    arcpy.management.DeleteFeatures(procParcelLyr)
    arcpy.AddMessage("Removed selected parcels from {}".format(procParcelLyr))
    



